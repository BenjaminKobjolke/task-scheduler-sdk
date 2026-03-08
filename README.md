# Interactions SDK

Lightweight Python SDK for adding interactive prompts to scripts run by the task scheduler. Scripts can ask questions, request confirmations, and present choices to users — whether they're running via CLI or chat bot.

## Installation

Install as a package from the repository:

```bash
pip install path/to/interactions-sdk
```

Or with uv:

```bash
uv add --path path/to/interactions-sdk
```

## Quick Start

```python
from interactions_sdk import confirm, ask, choose, output

# output() works everywhere — protocol under scheduler, print() standalone
output("Starting deployment process...")

if confirm("Deploy to production?", default=True):
    env = choose("Select environment:", ["staging", "production"], default=0)
    version = ask("Enter version:", default="1.0.0")
    output(f"Deploying version {version} to env index {env}")
else:
    output("Deployment cancelled")
```

## API Reference

### `confirm(message, *, default=None, id=None) -> bool`

Ask the user for yes/no confirmation.

| Parameter | Type | Description |
|-----------|------|-------------|
| `message` | `str` | Question text shown to user |
| `default` | `bool \| None` | Default value used on timeout |
| `id` | `str \| None` | Custom prompt ID (auto-generated if omitted) |

**Returns:** `True` if confirmed, `False` otherwise.

```python
if confirm("Continue with deployment?"):
    print("Deploying...")
```

### `ask(message, *, default=None, id=None) -> str`

Ask the user for text input.

| Parameter | Type | Description |
|-----------|------|-------------|
| `message` | `str` | Question text shown to user |
| `default` | `str \| None` | Default value used on timeout |
| `id` | `str \| None` | Custom prompt ID (auto-generated if omitted) |

**Returns:** The user's text response.

```python
name = ask("Enter release name:", default="v1.0.0")
```

### `choose(message, options, *, default=None, id=None, hidden_options=None) -> int`

Ask the user to pick from a list of options.

| Parameter | Type | Description |
|-----------|------|-------------|
| `message` | `str` | Question text shown to user |
| `options` | `list[str]` | List of options to choose from |
| `default` | `int \| None` | Default option index (0-based) used on timeout |
| `id` | `str \| None` | Custom prompt ID (auto-generated if omitted) |
| `hidden_options` | `dict[str, str] \| None` | Shortcut keys mapped to labels; accepted as input but not displayed. Indices continue after visible options. |

**Returns:** 0-based index of the selected option.

```python
idx = choose("Select environment:", ["dev", "staging", "production"], default=0)
env = ["dev", "staging", "production"][idx]
print(f"Selected: {env}")
```

**Hidden options** let you define shortcut commands that the scheduler accepts but does not show in the list:

```python
result = choose(
    "Pick action:",
    ["Continue", "Retry"],
    hidden_options={"a": "Abort", "x": "Exit"},
)
# Visible options: "Continue" (0), "Retry" (1)
# Hidden shortcuts: "a" returns 2, "x" returns 3
if result == 2:
    print("Aborted!")
```

### `output(text) -> None`

Display text to the user. When running under the task scheduler, sends through the JSON protocol so the scheduler can display it properly. When running standalone, falls back to `print()`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | `str` | Text to display to the user |

This is a **fire-and-forget** call — no response is expected. Use `output()` as a drop-in replacement for `print()` to ensure your script's display text works correctly both under the scheduler and standalone.

```python
from interactions_sdk import output

output("Processing item 5 of 10...")
output("Done!")
```

### `is_interactive() -> bool`

Check if the current script is running under the task-scheduler. The scheduler sets `INTERACTIVE=1` in the environment of every child process it launches.

**Returns:** `True` if the `INTERACTIVE` environment variable is `"1"`, `False` otherwise.

```python
from interactions_sdk import is_interactive

if is_interactive():
    # Safe to use SDK prompts (confirm, ask, choose)
    answer = confirm("Continue?", default=True)
else:
    # Running standalone — fall back to regular input or defaults
    answer = input("Continue? [y/n] ").lower() == "y"
```

### `ENV_MARKER`

The name of the environment variable used for scheduler detection (`"INTERACTIVE"`). Exposed for advanced use cases (e.g., custom detection logic).

## Error Handling

If a prompt times out and has no default value, an `InteractionError` is raised:

```python
from interactions_sdk import confirm, InteractionError

try:
    result = confirm("Proceed?")
except InteractionError as e:
    print(f"Prompt failed: {e}")
    # Handle gracefully - e.g., abort operation
```

## Timeout Behavior

The scheduler has a configurable timeout (default: 300 seconds) for interactive prompts:

- **With default value:** If timeout expires, the default is used automatically. Your script continues normally.
- **Without default value:** If timeout expires, an `InteractionError` is raised. Your script should handle this gracefully.

Set defaults whenever possible to ensure scripts can run unattended if needed:

```python
# Good: script can complete even without user response
if confirm("Run cleanup?", default=True):
    cleanup()

# Careful: script will raise InteractionError on timeout
if confirm("Run cleanup?"):
    cleanup()
```

## How It Works

The SDK communicates with the task scheduler using a JSON protocol over stdout/stdin:

**Interactive prompts** (`confirm`, `ask`, `choose`):
1. Your script writes a JSON prompt to **stdout**
2. The scheduler reads it, shows it to the user (CLI terminal or chat bot)
3. The user responds
4. The scheduler writes the response as JSON to your script's **stdin**
5. The SDK parses the response and returns the value

**Display-only output** (`output`):
1. Your script writes a JSON message to **stdout** with `type: "output"`
2. The scheduler reads it and displays the text to the user
3. No response is sent back — the script continues immediately

Only lines with the special `_interactive` marker are intercepted by the scheduler. Regular `print()` output still works but bypasses the protocol — prefer `output()` for reliable display under the scheduler.

## Running Your Script

### Via CLI

```bash
python main.py --run_id <task_id>
```

Prompts appear in your terminal. You respond by typing directly.

### Via Bot (Telegram/XMPP)

```
/run <task_id>
```

Prompts are sent as chat messages. You respond by sending a message back.

### Scheduled (automatic) runs

Scheduled runs do **not** support interactive prompts. Only manual runs via CLI or bot trigger the interactive protocol. Make sure your scripts handle the case where no interaction is available by using default values.

## Requirements

- Python >= 3.11
- No external dependencies
