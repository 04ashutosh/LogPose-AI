import json
import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_token
from app.models.models import User, ChatSession, ChatMessage
from app.schemas.chat import SessionCreate, SessionResponse, MessageResponse
from app.agents.graph import agent_graph

router = APIRouter(prefix="/chat", tags=["Chat & Agents"])
logger = logging.getLogger("uvicorn")

async def get_user_from_token_ws(websocket: WebSocket, db: AsyncSession) -> User:
    """Authenticates JWT inside WebSocket query string handshake parameters."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketDisconnect()
    
    user_id = decode_token(token)
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketDisconnect()
        
    result = await db.execute(select(User).filter(User.id == UUID(user_id)))
    user = result.scalars().first()
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketDisconnect()
    return user

# REST Endpoints
@router.post("/sessions", response_model=SessionResponse)
async def create_session(session_in: SessionCreate, db: AsyncSession = Depends(get_db)):
    # Simulating standard user for REST simplicity in first phase
    # In a full configuration, a Dependency validates and supplies the current active user ID
    user_result = await db.execute(select(User))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=400, detail="Initialize a registered user first.")
        
    session = ChatSession(user_id=user.id, title=session_in.title)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session

@router.get("/sessions", response_model=list[SessionResponse])
async def get_sessions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ChatSession).order_by(ChatSession.updated_at.desc()))
    return result.scalars().all()

@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def get_session_messages(session_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()))
    return result.scalars().all()

# WebSocket Handler Endpoint
@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: UUID, db: AsyncSession = Depends(get_db)):
    await websocket.accept()
    try:
        user = await get_user_from_token_ws(websocket, db)
    except WebSocketDisconnect:
        return
        
    # Verify the user owns this session ID
    session_result = await db.execute(
        select(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
    )
    chat_session = session_result.scalars().first()
    if not chat_session:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    logger.info(f"WebSocket Client authorized: User {user.email} for Session {session_id}")

    try:
        while True:
            # Await user messages
            data = await websocket.receive_text()
            payload = json.loads(data)
            action = payload.get("action")
            
            if action == "send_prompt":
                prompt_text = payload.get("data", {}).get("prompt")
                if not prompt_text:
                    continue

                # 1. Save client message
                user_msg = ChatMessage(session_id=session_id, role="user", content=prompt_text)
                db.add(user_msg)
                await db.commit()

                # Websocket Callback function to feed events down the pipe dynamically
                async def ws_callback(event_type: str, node: str, content: str = ""):
                    try:
                        await websocket.send_json({
                            "event": event_type,
                            "data": {
                                "node": node,
                                "content": content
                            }
                        })
                    except Exception as e:
                        logger.error(f"Failed to stream websocket event: {e}")

                # 2. Invoke LangGraph Execution Pipeline
                graph_state = {
                    "user_prompt": prompt_text,
                    "messages": [{"role": "user", "content": prompt_text}],
                    "planner_output": "",
                    "architect_output": "",
                    "coder_output": "",
                    "review_status": "",
                    "review_feedback": "",
                    "loop_count": 0,
                    "active_agent": "Planner Agent"
                }

                # Executed asynchronously, yielding events in real-time
                result_state = await agent_graph.ainvoke(
                    graph_state,
                    config={"configurable": {"websocket_callback": ws_callback}}
                )

                # 3. Assemble and save assistant output summary
                final_content = (
                    f"### Planner Output\n{result_state.get('planner_output')}\n\n"
                    f"### Architect Output\n{result_state.get('architect_output')}\n\n"
                    f"### Coder Output\n{result_state.get('coder_output')}\n\n"
                    f"### Reviewer Feedback\n{result_state.get('review_feedback')}"
                )
                assistant_msg = ChatMessage(
                    session_id=session_id,
                    role="assistant",
                    content=final_content,
                    agent_name="LogPose Orchestrator",
                    step_name="Complete"
                )
                db.add(assistant_msg)
                await db.commit()

                # Dispatch execution wrap up
                await websocket.send_json({
                    "event": "graph_complete",
                    "data": {
                        "content": final_content
                    }
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected gracefully.")
    except Exception as e:
        logger.error(f"WebSocket server runtime exception encountered: {e}")