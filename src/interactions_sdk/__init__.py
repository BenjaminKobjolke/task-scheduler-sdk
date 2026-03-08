"""Interactions SDK — interactive prompts for scheduled scripts.

Usage:
    from interactions_sdk import confirm, ask, choose

    if confirm("Deploy to production?", default=True):
        env = choose("Select environment:", ["staging", "production"], default=0)
        version = ask("Enter version:", default="1.0.0")
        print(f"Deploying version {version} to environment {env}")
"""

from __future__ import annotations

import os

from ._protocol import InteractionError, _send_output, _send_prompt

__all__ = [
    "ENV_MARKER",
    "InteractionError",
    "_send_output",
    "ask",
    "choose",
    "confirm",
    "is_interactive",
    "output",
]

ENV_MARKER = "INTERACTIVE"


def is_interactive() -> bool:
    """Check if this script is running under the interactive scheduler."""
    return os.getenv(ENV_MARKER) == "1"


def output(text: str) -> None:
    """Display text to the user.

    When running under the task scheduler, sends through the protocol.
    Otherwise, prints directly to stdout.

    Args:
        text: The text to display.
    """
    if is_interactive():
        if text:
            _send_output(text)
    else:
        print(text)


def confirm(
    message: str, *, default: bool | None = None, id: str | None = None
) -> bool:
    """Ask user for yes/no confirmation.

    Args:
        message: Question text shown to user
        default: Default value used on timeout
        id: Optional custom prompt ID

    Returns:
        True if user confirmed, False otherwise
    """
    return _send_prompt("confirm", message, prompt_id=id, default=default)


def ask(
    message: str, *, default: str | None = None, id: str | None = None
) -> str:
    """Ask user for text input.

    Args:
        message: Question text shown to user
        default: Default value used on timeout
        id: Optional custom prompt ID

    Returns:
        The user's text response
    """
    return _send_prompt("input", message, prompt_id=id, default=default)


def choose(
    message: str,
    options: list[str],
    *,
    default: int | None = None,
    id: str | None = None,
    hidden_options: dict[str, str] | None = None,
) -> int:
    """Ask user to pick from a list of options.

    Args:
        message: Question text shown to user
        options: List of string options to choose from
        default: Default option index (0-based) used on timeout
        id: Optional custom prompt ID
        hidden_options: Shortcut keys mapped to labels; accepted as input
            but not displayed to the user. Indices continue after visible
            options (e.g. with 2 visible options, first hidden option = index 2).

    Returns:
        0-based index of the selected option
    """
    return _send_prompt(
        "choice", message, prompt_id=id, default=default, options=options,
        hidden_options=hidden_options,
    )
