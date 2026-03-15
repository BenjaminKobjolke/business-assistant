# Tool Call Gating Pattern

## Problem

AI agents sometimes skip prerequisite steps in multi-step workflows, even when the system prompt explicitly instructs them to follow a specific order. Relying solely on prompt instructions is unreliable — the agent can shortcut or forget steps.

## Solution

Enforce prerequisites at the **code level** by requiring a token, ID, or confirmation flag that can only be obtained by completing the prerequisite step first. Without the valid gate value, the tool call is rejected with an error message that tells the agent what to do.

## Variants

### Token/Receipt Pattern (e.g., greeting_id)

Use when: the agent must call Tool A before Tool B, and Tool A produces a value Tool B needs.

1. Tool A generates a result, stores it in a registry with a unique ID, returns the ID
2. Tool B requires the ID parameter — looks it up in the registry
3. Invalid/missing ID → reject with error explaining the prerequisite
4. IDs are single-use (consumed on use) to prevent stale reuse

**Example:** `build_greeting` returns `{"greeting_id": "uuid", "greeting": "Hallo"}`. `reply_email` and `compose_email` require a valid `greeting_id` — without it, the call fails.

```python
# Registry
_greeting_registry: dict[str, str] = {}

# Tool A: produces token
def _build_greeting(ctx, salutation="", formal=False):
    greeting_text = build_greeting(salutation, formal=formal)
    greeting_id = str(uuid.uuid4())
    _greeting_registry[greeting_id] = greeting_text
    return json.dumps({"greeting_id": greeting_id, "greeting": greeting_text})

# Tool B: requires token
def _reply_email(ctx, email_id, reply_body, greeting_id="", ...):
    greeting = _resolve_greeting(greeting_id)  # pop from registry
    if greeting is None:
        return "Error: greeting_id is missing. Call build_greeting first."
    # ... proceed with greeting
```

### Confirmation Gate Pattern (e.g., confirm=True)

Use when: the agent must verify something with the user before a destructive or irreversible action.

1. Tool has a `confirm: bool = False` parameter
2. On first call without `confirm=True`, returns a descriptive message asking for confirmation
3. Agent shows the message to the user, gets approval, calls again with `confirm=True`
4. Only applies to the "new/dangerous" path — safe paths (e.g., known mappings) skip the gate

**Example:** `mark_email_as_done` requires `confirm=True` when creating a new sender→folder mapping (to prevent the agent from guessing the wrong folder).

```python
def mark_as_done(self, email_id, database, target_folder="",
                 mapping_type="", folder="INBOX", confirm=False):
    mapping = database.get_folder_mapping(sender)

    # Known mapping → auto-move (no confirm needed)
    if not target_folder and mapping:
        return self._do_move(...)

    # New mapping → require confirmation
    if not mapping and not confirm:
        return (
            f"No existing rule for {sender}. "
            f"Confirm: create '{mapping_type}' rule "
            f"'{identifier}' -> '{target_folder}'? "
            "Call again with confirm=True."
        )

    # Confirmed → create mapping and move
    database.set_folder_mapping(identifier, target_folder, mapping_type)
    return self._do_move(...)
```

## When to Use

- Agent frequently skips a prerequisite step despite prompt instructions
- The prerequisite produces information the agent needs (token pattern)
- An action is irreversible and the agent should verify with the user first (confirm pattern)
- The cost of getting it wrong is high (wrong folder, missing greeting, wrong recipient)

## When NOT to Use

- The workflow is simple enough that prompt instructions reliably work
- Adding gating would break existing integrations or make the tool unusable
- The action is easily reversible (e.g., can be undone with another tool call)
