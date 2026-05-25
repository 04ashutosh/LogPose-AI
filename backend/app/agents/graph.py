from typing import Dict, Any
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.agents.state import GraphState

# Create LLM Instances with the local Ollama backend
planner_llm = ChatOllama(base_url=settings.OLLAMA_BASE_URL, model=settings.MODEL_PLANNER, temperature=0.2)
coder_llm = ChatOllama(base_url=settings.OLLAMA_BASE_URL, model=settings.MODEL_CODER, temperature=0.1)
router_llm = ChatOllama(base_url=settings.OLLAMA_BASE_URL, model=settings.MODEL_ROUTER, temperature=0.1)

async def send_state_event(config: Dict[str, Any], event_type: str, node: str, content: str = ""):
    """Helper to dispatch updates to the WS client during Graph node execution."""
    callback = config.get("configurable", {}).get("websocket_callback")
    if callback:
        await callback(event_type=event_type, node=node, content=content)

# Define Nodes
async def planner_node(state: GraphState, config: Dict[str, Any]) -> Dict[str, Any]:
    await send_state_event(config, "node_start", "Planner Agent")
    
    prompt = (
        f"You are the Lead Planner for LogPose AI. Create a solid implementation plan for:\n"
        f"'{state['user_prompt']}'\n"
        f"Outline steps, modules, data models, and edge cases."
    )
    
    content = ""
    async for chunk in planner_llm.astream(prompt):
        text = chunk.content
        content += text
        await send_state_event(config, "token", "Planner Agent", text)
        
    await send_state_event(config, "node_end", "Planner Agent", content)
    return {"planner_output": content, "active_agent": "Architect Agent"}

async def architect_node(state: GraphState, config: Dict[str, Any]) -> Dict[str, Any]:
    await send_state_event(config, "node_start", "Architect Agent")
    
    prompt = (
        f"You are the Systems Architect for LogPose AI. Review this Plan:\n\n{state['planner_output']}\n\n"
        f"Provide the core software design, folder tree, and interface details."
    )
    
    content = ""
    async for chunk in router_llm.astream(prompt):
        text = chunk.content
        content += text
        await send_state_event(config, "token", "Architect Agent", text)
        
    await send_state_event(config, "node_end", "Architect Agent", content)
    return {"architect_output": content, "active_agent": "Coder Agent"}

async def coder_node(state: GraphState, config: Dict[str, Any]) -> Dict[str, Any]:
    await send_state_event(config, "node_start", "Coder Agent")
    
    feedback = f"\nTake this review feedback into account to refine code:\n{state['review_feedback']}" if state.get("review_feedback") else ""
    prompt = (
        f"You are the Coder Agent for LogPose AI. Build the complete production-grade files based on:\n"
        f"Plan: {state['planner_output']}\n"
        f"Architecture: {state['architect_output']}{feedback}\n\n"
        f"Output executable code blocks with brief setup explanations."
    )
    
    content = ""
    async for chunk in coder_llm.astream(prompt):
        text = chunk.content
        content += text
        await send_state_event(config, "token", "Coder Agent", text)
        
    await send_state_event(config, "node_end", "Coder Agent", content)
    return {"coder_output": content, "active_agent": "Reviewer Agent"}

async def reviewer_node(state: GraphState, config: Dict[str, Any]) -> Dict[str, Any]:
    await send_state_event(config, "node_start", "Reviewer Agent")
    
    prompt = (
        f"You are the Quality Reviewer Agent for LogPose AI. Evaluate the Coder's work:\n\n{state['coder_output']}\n\n"
        f"Evaluate bugs, performance, security risks. You must decide whether it passes review.\n"
        f"Format your output exactly as:\n"
        f"STATUS: [PASS or FAIL]\n"
        f"FEEDBACK: [Detailed review observations]"
    )
    
    content = ""
    async for chunk in router_llm.astream(prompt):
        text = chunk.content
        content += text
        await send_state_event(config, "token", "Reviewer Agent", text)
        
    # Simple parse status
    status = "PASS"
    feedback_text = content
    if "STATUS: FAIL" in content or "STATUS: failed" in content or "FAIL" in content[:40]:
        status = "FAIL"
        
    await send_state_event(config, "node_end", "Reviewer Agent", content)
    return {
        "review_status": status,
        "review_feedback": feedback_text,
        "loop_count": state.get("loop_count", 0) + 1,
        "active_agent": "Finished" if status == "PASS" else "Coder Agent"
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