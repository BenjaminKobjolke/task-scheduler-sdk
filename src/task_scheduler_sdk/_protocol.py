"""Low-level JSON protocol for communicating with the task scheduler."""

from __future__ import annotations

import json
import sys
import uuid
from typing import Any


class InteractionError(Exception):
    """Raised when the scheduler returns an error response."""

    def __init__(self, message: str, prompt_id: str) -> None:
        super().__init__(message)
        self.prompt_id = prompt_id


def _generate_id() -> str:
    """Generate a unique prompt ID."""
    return str(uuid.uuid4())


def _send_prompt(
    prompt_type: str,
    message: str,
    *,
    prompt_id: str | None = None,
    default: Any = None,
    options: list[str] | None = None,
) -> Any:
    """Send a prompt to the scheduler via stdout and read the response from stdin.

    Args:
        prompt_type: One of "confirm", "input", "choice"
        message: The question text
        prompt_id: Optional custom ID (auto-generated if not provided)
        default: Default value used on timeout
        options: List of options (for choice prompts)

    Returns:
        The value from the scheduler's response

    Raises:
        InteractionError: If the response contains an error field
    """
    if prompt_id is None:
        prompt_id = _generate_id()

    payload: dict[str, Any] = {
        "_interactive": True,
        "type": prompt_type,
        "id": prompt_id,
        "message": message,
    }
    if default is not None:
        payload["default"] = default
    if options is not None:
        payload["options"] = options

    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()

    response_line = sys.stdin.readline()
    response = json.loads(response_line)

    if "error" in response and response["error"]:
        raise InteractionError(response["error"], prompt_id)

    return response["value"]
