from typing import TypedDict, List, Dict, Any, Optional

class GraphState(TypedDict):
    """
    Defines the shared memory state of LogPose AI's multi-agent graph.
    """
    user_prompt: str
    messages: List[Dict[str, str]]
    planner_output: str
    architect_output: str
    coder_output: str
    review_status: str  # "pass" or "fail"
    review_feedback: str
    loop_count: int
    active_agent: str