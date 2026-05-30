import logging
from typing import Dict, Any

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.agents.state import GraphState
from app.core.workspace import parse_and_create_files

logger = logging.getLogger("uvicorn")


# Dynamic LLM Factory
def get_llm(preferred_provider: str, config: RunnableConfig):
    api_keys = config.get("configurable", {}).get("api_keys", {})

    # Auto-Routing Logic (Check preferred first)
    if preferred_provider == "anthropic" and "anthropic" in api_keys:
        return ChatAnthropic(model="claude-3-5-sonnet-20240620", api_key=api_keys["anthropic"])
    elif preferred_provider == "openai" and "openai" in api_keys:
        return ChatOpenAI(model="gpt-4o", api_key=api_keys["openai"])
    elif preferred_provider == "groq" and "groq" in api_keys:
        return ChatGroq(model="llama3-70b-8192", api_key=api_keys["groq"])
    elif preferred_provider == "gemini" and "gemini" in api_keys:
        return ChatGoogleGenerativeAI(model="gemini-1.5-flash", api_key=api_keys["gemini"])

    # Fallback to ANY available key if preferred is missing
    if "gemini" in api_keys:
        return ChatGoogleGenerativeAI(model="gemini-1.5-flash", api_key=api_keys["gemini"])
    elif "openai" in api_keys:
        return ChatOpenAI(model="gpt-4o", api_key=api_keys["openai"])
    elif "anthropic" in api_keys:
        return ChatAnthropic(model="claude-3-5-sonnet-20240620", api_key=api_keys["anthropic"])
    elif "groq" in api_keys:
        return ChatGroq(model="llama3-70b-8192", api_key=api_keys["groq"])

    # Ultimate fallback to local Ollama if NO keys are provided
    return ChatOllama(
        model="qwen2.5-coder",
        base_url=settings.OLLAMA_BASE_URL
    )


async def send_state_event(
    config: RunnableConfig,
    event_type: str,
    node: str,
    content: str = ""
):
    """Helper to dispatch updates to the WS client during Graph node execution."""
    callback = config.get("configurable", {}).get("websocket_callback")
    if callback:
        await callback(event_type=event_type, node=node, content=content)


async def stream_llm_to_ws(llm, prompt: str, node_name: str, config: RunnableConfig) -> str:
    """
    Shared streaming helper for all agent nodes.
    Handles the deepseek-r1 quirk where thinking tokens arrive as empty strings.
    Extracts reasoning_content from additional_kwargs when available.
    Skips empty chunks to prevent WebSocket flooding.
    """
    await send_state_event(config, "node_start", node_name)
    import asyncio
    await asyncio.sleep(0.1) # Force event loop to flush the websocket

    content = ""
    thinking_sent = False
    has_streamed_content = False

    async for chunk in llm.astream(prompt):
        # Try to get the actual text content
        text = chunk.content or ""

        # DeepSeek-R1 puts reasoning in additional_kwargs during thinking phase
        reasoning = ""
        if hasattr(chunk, "additional_kwargs") and chunk.additional_kwargs:
            reasoning = chunk.additional_kwargs.get("reasoning_content", "")

        # If we have reasoning content, stream that as thinking tokens
        if reasoning:
            if not thinking_sent:
                await send_state_event(config, "thinking", node_name, "🧠 Reasoning...")
                thinking_sent = True
            await send_state_event(config, "token", node_name, reasoning)
            continue

        # Skip empty chunks entirely — this prevents the WebSocket flood
        if not text:
            # Send ONE thinking indicator if we haven't yet
            if not thinking_sent and not has_streamed_content:
                await send_state_event(config, "thinking", node_name, "🧠 Model is reasoning...")
                thinking_sent = True
            continue

        # We have real content — stream it!
        has_streamed_content = True
        content += text
        await send_state_event(config, "token", node_name, text)

    await send_state_event(config, "node_end", node_name, content)
    logger.info(f"[{node_name}] Completed. Output length: {len(content)} chars")
    return content


# Define Nodes
async def planner_node(
    state: GraphState,
    config: RunnableConfig
) -> Dict[str, Any]:
    logger.info("Executing planner_node...")
    llm = get_llm("openai", config)

    prompt = (
        f"You are the Lead Planner for LogPose AI. Create a solid implementation plan for:\n"
        f"'{state['user_prompt']}'\n"
        f"Outline steps, modules, data models, and edge cases."
    )

    content = await stream_llm_to_ws(llm, prompt, "Planner Agent", config)

    return {
        "planner_output": content,
        "active_agent": "Architect Agent"
    }


async def architect_node(
    state: GraphState,
    config: RunnableConfig
) -> Dict[str, Any]:
    llm = get_llm("anthropic", config)

    prompt = (
        f"You are the Systems Architect for LogPose AI. Review this Plan:\n\n"
        f"{state['planner_output']}\n\n"
        f"Provide the core software design, folder tree, and interface details."
    )

    content = await stream_llm_to_ws(llm, prompt, "Architect Agent", config)

    return {
        "architect_output": content,
        "active_agent": "Coder Agent"
    }


async def coder_node(
    state: GraphState,
    config: RunnableConfig
) -> Dict[str, Any]:
    llm = get_llm("groq", config)

    feedback = (
        f"\nTake this review feedback into account to refine code:\n"
        f"{state['review_feedback']}"
        if state.get("review_feedback")
        else ""
    )

    prompt = (
        f"You are the Coder Agent for LogPose AI. Build the complete production-grade files based on:\n"
        f"Plan: {state['planner_output']}\n"
        f"Architecture: {state['architect_output']}{feedback}\n\n"
        f"IMPORTANT: For each file, format your output exactly like this:\n"
        f"#### `filename.py`\n"
        f"```python\n"
        f"code here\n"
        f"```\n\n"
        f"CRITICAL RULES FOR OUTPUT:\n"
        f"1. DO NOT generate ASCII directory trees or structural diagrams.\n"
        f"2. ONLY output files containing valid, executable source code.\n"
        f"3. NO placeholder text inside the code block."
    )

    content = await stream_llm_to_ws(llm, prompt, "Coder Agent", config)

    # AUTO-CREATE FILES: Parse the coder output and create real files in workspace
    session_id = config.get("configurable", {}).get("session_id", "")
    created_files = []
    if session_id and content:
        created_files = parse_and_create_files(session_id, content)
        if created_files:
            # Notify the frontend about created files
            file_list = "\n".join(f"  ✅ {f}" for f in created_files)
            await send_state_event(
                config, "files_created", "Coder Agent",
                f"Created {len(created_files)} files:\n{file_list}"
            )
            logger.info(f"[Coder] Created {len(created_files)} files in workspace {session_id}")

    return {
        "coder_output": content,
        "active_agent": "Reviewer Agent"
    }


async def reviewer_node(
    state: GraphState,
    config: RunnableConfig
) -> Dict[str, Any]:
    llm = get_llm("openai", config)

    prompt = (
        f"You are the Quality Reviewer Agent for LogPose AI. Evaluate the Coder's work:\n\n"
        f"{state['coder_output']}\n\n"
        f"Evaluate bugs, performance, security risks. You must decide whether it passes review.\n"
        f"Format your output exactly as:\n"
        f"STATUS: [PASS or FAIL]\n"
        f"FEEDBACK: [Detailed review observations]"
    )

    content = await stream_llm_to_ws(llm, prompt, "Reviewer Agent", config)

    # Simple parse status
    status = "PASS"
    feedback_text = content

    if (
        "STATUS: FAIL" in content
        or "STATUS: failed" in content
        or "FAIL" in content[:40]
    ):
        status = "FAIL"

    return {
        "review_status": status,
        "review_feedback": feedback_text,
        "loop_count": state.get("loop_count", 0) + 1,
        "active_agent": (
            "Finished"
            if status == "PASS"
            else "Coder Agent"
        )
    }


def route_decision(state: GraphState) -> str:
    """Decides if graph loops back to the Coder or finishes."""
    if state["review_status"] == "PASS":
        return "finish"

    if state.get("loop_count", 0) >= 2:
        # Loop breaker safety limit
        return "finish"

    return "coder"


# Construct State Graph
builder = StateGraph(GraphState)

# Register Nodes
builder.add_node("planner", planner_node)
builder.add_node("architect", architect_node)
builder.add_node("coder", coder_node)
builder.add_node("reviewer", reviewer_node)

# Design Flow Connections
builder.set_entry_point("planner")

builder.add_edge("planner", "architect")
builder.add_edge("architect", "coder")
builder.add_edge("coder", "reviewer")

builder.add_conditional_edges(
    "reviewer",
    route_decision,
    {
        "finish": END,
        "coder": "coder"
    }
)

agent_graph = builder.compile()