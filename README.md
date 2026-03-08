# Interactions SDK

Lightweight Python SDK for adding interactive prompts to scripts run by the task scheduler. Scripts can ask questions, request confirmations, and present choices to users — whether they're running via CLI or chat bot.

## Dual-Mode Operation

The SDK automatically detects how it's running:

- **Interactive mode** (`INTERACTIVE=1` env var): Uses the JSON protocol over stdin/stdout to communicate with the task scheduler.
- **CLI mode** (no env var): Falls back to console `input()` prompts so scripts work stand-alone without any wrapper code.

This means `from interactions_sdk import confirm, ask, choose, output` gives you both modes for free — no wrapper code needed.

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
| `default` | `bool \| None` | Default value used on timeout (interactive) or empty input (CLI) |
| `id` | `str \| None` | Custom prompt ID (auto-generated if omitted) |

**Returns:** `True` if confirmed, `False` otherwise.

**CLI behavior:** Shows `[Y/n]` or `[y/N]` hint based on default. Empty input returns the default (or `False` when no default).

**Interactive behavior:** Raises `AbortError` if the scheduler returns `None`.

```python
if confirm("Continue with deployment?"):
    print("Deploying...")
```

### `ask(message, *, default=None, id=None) -> str`

Ask the user for text input.

| Parameter | Type | Description |
|-----------|------|-------------|
| `message` | `str` | Question text shown to user |
| `default` | `str \| None` | Default value used on timeout (interactive) or empty input (CLI) |
| `id` | `str \| None` | Custom prompt ID (auto-generated if omitted) |

**Returns:** The user's text response.

**CLI behavior:** Shows `[default]` in prompt. Empty input returns the default (or `""` when no default).

**Interactive behavior:** Raises `AbortError` if the scheduler returns `None`.

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

**CLI behavior:** Shows a numbered menu. Default option is marked with `*`. Hidden options show a hint line like `(a=Abort)`. Invalid input re-prompts.

**Interactive behavior:** Raises `AbortError` if the scheduler returns `None`.

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

Display text to the user. When running under the task scheduler, sends through the JSON protocol so the scheduler can display it properly. When running standalone, falls back to `print()` with unicode safety.

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | `str` | Text to display to the user |

This is a **fire-and-forget** call — no response is expected. Use `output()` as a drop-in replacement for `print()` to ensure your script's display text works correctly both under the scheduler and standalone.

If output capture is active, the text is also appended to the capture buffer.

```python
from interactions_sdk import output

output("Processing item 5 of 10...")
output("Done!")
```

### `ask_or_accept(label, *, default) -> str`

Show an accept/edit choice. If the user picks "Accept", returns the default. If they pick "Edit", prompts for text input.

| Parameter | Type | Description |
|-----------|------|-------------|
| `label` | `str` | The label for the value |
| `default` | `str` | The current/default value |

**Returns:** The accepted or edited value.

```python
title = ask_or_accept("Title:", default="My Todo")
```

### `InteractionChoice`

Higher-level class that maps display labels to action keys.

```python
from interactions_sdk import InteractionChoice

ic = InteractionChoice(
    "What next?",
    [("Continue processing", "continue"), ("Skip this item", "skip")],
    default=0,
    abort=True,  # adds a hidden "a" shortcut that returns "abort"
)
action = ic.choose()
if action == "abort":
    print("Aborted!")
elif action == "continue":
    print("Continuing...")
```

### Output Capture

Capture `output()` calls into a buffer for later retrieval.

```python
from interactions_sdk import start_output_capture, stop_output_capture, output

start_output_capture(silent=True)  # silent=True suppresses display
output("line 1")
output("line 2")
text = stop_output_capture()  # "line 1\nline 2"
```

### `is_interactive() -> bool`

Check if the current script is running under the task-scheduler. The scheduler sets `INTERACTIVE=1` in the environment of every child process it launches.

**Returns:** `True` if the `INTERACTIVE` environment variable is `"1"`, `False` otherwise.

```python
from interactions_sdk import is_interactive

if is_interactive():
    print("Running under scheduler")
else:
    print("Running standalone — CLI prompts will be used automatically")
```

### `ENV_MARKER`

The name of the environment variable used for scheduler detection (`"INTERACTIVE"`). Exposed for advanced use cases (e.g., custom detection logic).

## Error Handling

### `AbortError`

Raised when a prompt function (`confirm`, `ask`, `choose`) receives `None` from the scheduler in interactive mode. This typically means the user did not respond.

```python
from interactions_sdk import confirm, AbortError

try:
    result = confirm("Proceed?")
except AbortError:
    print("User did not respond — aborting")
```

### `InteractionError`

Raised when the scheduler returns an explicit error response (e.g., timeout with no default).

```python
from interactions_sdk import confirm, InteractionError

try:
    result = confirm("Proceed?")
except InteractionError as e:
    print(f"Prompt failed: {e}")
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

**CLI fallback** (no scheduler):
1. `confirm`/`ask`/`choose` use `input()` to prompt in the console
2. `output` uses `print()` with unicode safety

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
