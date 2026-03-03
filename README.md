# Task Scheduler SDK

Lightweight Python SDK for adding interactive prompts to scripts run by the task scheduler. Scripts can ask questions, request confirmations, and present choices to users — whether they're running via CLI or chat bot.

## Installation

Install as a package from the repository:

```bash
pip install path/to/task-scheduler-sdk
```

Or with uv:

```bash
uv add --path path/to/task-scheduler-sdk
```

## Quick Start

```python
from task_scheduler_sdk import confirm, ask, choose, is_run_by_task_scheduler

# Detect if running under the scheduler
if is_run_by_task_scheduler():
    # Use SDK prompts — the scheduler handles I/O
    if confirm("Deploy to production?", default=True):
        env = choose("Select environment:", ["staging", "production"], default=0)
        version = ask("Enter version:", default="1.0.0")
        print(f"Deploying version {version} to env index {env}")
    else:
        print("Deployment cancelled")
else:
    # Running standalone — use regular input() or skip prompts
    version = input("Enter version: ")
    print(f"Deploying version {version}")
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

### `choose(message, options, *, default=None, id=None) -> int`

Ask the user to pick from a list of options.

| Parameter | Type | Description |
|-----------|------|-------------|
| `message` | `str` | Question text shown to user |
| `options` | `list[str]` | List of options to choose from |
| `default` | `int \| None` | Default option index (0-based) used on timeout |
| `id` | `str \| None` | Custom prompt ID (auto-generated if omitted) |

**Returns:** 0-based index of the selected option.

```python
idx = choose("Select environment:", ["dev", "staging", "production"], default=0)
env = ["dev", "staging", "production"][idx]
print(f"Selected: {env}")
```

### `is_run_by_task_scheduler() -> bool`

Check if the current script is running under the task-scheduler. The scheduler sets `TASK_SCHEDULER=1` in the environment of every child process it launches.

**Returns:** `True` if the `TASK_SCHEDULER` environment variable is `"1"`, `False` otherwise.

```python
from task_scheduler_sdk import is_run_by_task_scheduler

if is_run_by_task_scheduler():
    # Safe to use SDK prompts (confirm, ask, choose)
    answer = confirm("Continue?", default=True)
else:
    # Running standalone — fall back to regular input or defaults
    answer = input("Continue? [y/n] ").lower() == "y"
```

### `ENV_MARKER`

The name of the environment variable used for scheduler detection (`"TASK_SCHEDULER"`). Exposed for advanced use cases (e.g., custom detection logic).

## Error Handling

If a prompt times out and has no default value, an `InteractionError` is raised:

```python
from task_scheduler_sdk import confirm, InteractionError

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

1. Your script writes a JSON prompt to **stdout**
2. The scheduler reads it, shows it to the user (CLI terminal or chat bot)
3. The user responds
4. The scheduler writes the response as JSON to your script's **stdin**
5. The SDK parses the response and returns the value

This means your script's regular `print()` output still works normally — only lines with the special `_interactive` marker are intercepted as prompts.

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
