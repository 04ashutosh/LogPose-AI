from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.api.chat import get_current_user
from app.models.models import User
from app.core.workspace import list_files, read_file, execute_command

router = APIRouter(prefix="/workspace", tags=["Workspace"])


class CommandRequest(BaseModel):
    session_id: str
    command: str
    timeout: Optional[int] = 30


@router.get("/files/{session_id}")
async def get_workspace_files(
    session_id: str,
    user: User = Depends(get_current_user)
):
    """Lists all files in a session's workspace."""
    files = list_files(session_id)
    return {"files": files}


@router.get("/files/{session_id}/{filepath:path}")
async def get_file_content(
    session_id: str,
    filepath: str,
    user: User = Depends(get_current_user)
):
    """Reads the content of a specific file."""
    content = read_file(session_id, filepath)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found")
    return {"path": filepath, "content": content}


@router.post("/execute")
async def run_command(
    req: CommandRequest,
    user: User = Depends(get_current_user)
):
    """Executes a command in the session workspace."""
    result = execute_command(req.session_id, req.command, req.timeout)
    return result