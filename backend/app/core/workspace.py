import os
import re
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger("uvicorn")

# Base directory for all workspaces
WORKSPACES_ROOT = Path("d:/logpose-ai/workspaces")


def get_workspace_path(session_id: str) -> Path:
    """Returns the workspace directory for a given session, creating it if needed."""
    workspace = WORKSPACES_ROOT / session_id
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def create_file(session_id: str, filepath: str, content: str) -> str:
    """Creates a file inside the session workspace. Creates subdirectories as needed."""
    workspace = get_workspace_path(session_id)
    full_path = workspace / filepath
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    logger.info(f"[Workspace] Created file: {full_path}")
    return str(full_path)


def read_file(session_id: str, filepath: str) -> Optional[str]:
    """Reads a file from the session workspace."""
    workspace = get_workspace_path(session_id)
    full_path = workspace / filepath
    if full_path.exists():
        return full_path.read_text(encoding="utf-8")
    return None


def list_files(session_id: str) -> List[Dict[str, str]]:
    """Lists all files in the session workspace recursively."""
    workspace = get_workspace_path(session_id)
    files = []
    if workspace.exists():
        for path in sorted(workspace.rglob("*")):
            if path.is_file():
                relative = path.relative_to(workspace)
                files.append({
                    "path": str(relative).replace("\\", "/"),
                    "size": f"{path.stat().st_size} bytes"
                })
    return files


def execute_command(session_id: str, command: str, timeout: int = 30) -> Dict[str, str]:
    """Executes a shell command inside the session workspace."""
    workspace = get_workspace_path(session_id)
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": str(result.returncode)
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s",
            "returncode": "-1"
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "returncode": "-1"
        }


def parse_and_create_files(session_id: str, coder_output: str) -> List[str]:
    """
    Parses the Coder agent's markdown output for code blocks with filenames.
    Looks for patterns like:
        #### `filename.py`
        ```python
        code here
        ```
    OR:
        **`filename.py`**
        ```python
        code here
        ```
    Creates each file in the workspace and returns a list of created file paths.
    """
    created_files = []

    # Pattern: Match a filename header strictly followed by a code block
    # Supports: #### `file.py`, **`file.py`**, File: `file.py`
    pattern = re.compile(
        r'(?:#{1,6}\s+|\*\*|File:\s*)`?([a-zA-Z0-9_/\\.\-]+\.\w+)`?(?:\*\*)?\s*\n'  # strict filename header
        r'[^`]*?'                                                                 # optional intermediate text (no backticks allowed)
        r'```\w*\n'                                                               # opening fence
        r'(.*?)'                                                                  # code content
        r'\n```',                                                                 # closing fence
        re.DOTALL
    )

    matches = pattern.findall(coder_output)

    for filename, code in matches:
        filename = filename.strip().replace("\\", "/")
        # Skip obviously invalid filenames
        if "/" in filename and not any(filename.endswith(ext) for ext in [".py", ".ts", ".js", ".html", ".css", ".json", ".txt", ".md", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".sh", ".bat"]):
            continue
        try:
            create_file(session_id, filename, code.strip())
            created_files.append(filename)
        except Exception as e:
            logger.error(f"[Workspace] Failed to create {filename}: {e}")

    return created_files