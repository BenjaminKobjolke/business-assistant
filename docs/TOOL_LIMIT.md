# OpenAI Tool Limit

## The Problem

OpenAI limits function tools to **128 per API call**. Each plugin registers tools as OpenAI functions. With all plugins active, the bot was reaching ~130 tools, exceeding this limit.

## Current Tool Budget

| Component | Tools |
|-----------|------:|
| Core (memory + feedback) | 7 |
| IMAP plugin | 23 |
| PM plugin | 26 |
| RTM plugin | 10 |
| Obsidian plugin | 10 |
| Filesystem plugin | 8 |
| Workingtimes plugin | 8 |
| Calendar plugin | 8 |
| Transcribe plugin | 1 |
| TTS plugin | 0 |
| **Total** | **~101** |

Headroom: ~27 tools before hitting the limit.

## Solution: Tool Consolidation

Related CRUD operations are merged into single tools with an `action` parameter. This preserves full AI access while reducing the tool count.

### Why Not Command Handlers?

Command handlers bypass the AI entirely — the AI cannot call them during multi-step reasoning. Most tools are called by the AI in chains (e.g., list calendars → create event, search emails → reply). Converting them to command handlers would break these workflows.

### Consolidation Pattern

```python
# Before: 3 separate tools (3 OpenAI function slots)
def add_item(ctx, name: str) -> str: ...
def remove_item(ctx, name: str) -> str: ...
def list_items(ctx) -> str: ...

# After: 1 consolidated tool (1 OpenAI function slot)
def manage_items(ctx, action: str, name: str = "") -> str:
    """Manage items. action: add, remove, list."""
    if action == "add":
        return service.add(name)
    if action == "remove":
        return service.remove(name)
    if action == "list":
        return service.list_all()
    return f"ERROR: Unknown action '{action}'. Valid: add, remove, list."
```

### What Was Consolidated

**PM plugin (37 → 26, saved 11):**
- 7 workflow CRUD tools → `pm_manage_workflow` + `pm_run_workflow` (2)
- 3 match info tools → `pm_manage_match_info` (1)
- 2 project synonym tools → folded into `pm_update_project`
- 2 settings tools → `pm_settings` (1)
- 2 contact tools → `pm_contacts` (1)
- 2 tracking tools → `pm_tracking` (1)

**IMAP plugin (29 → 23, saved 6):**
- `draft_reply` + `send_reply` → `reply_email` with `action` param
- `draft_forward` + `forward_email` → `forward_email` with `action` param
- `draft_compose` + `compose_email` → `compose_email` with `action` param
- 3 tag tools → `email_tags` with `action` param
- Removed redundant `list_inbox` (use `list_messages(folder="INBOX")`)

**RTM plugin (14 → 10, saved 4):**
- `complete_task` + `uncomplete_task` → `rtm_complete_task(undo=False)`
- `add_tags` + `remove_tags` → `rtm_manage_tags(action)`
- `set_due_date` + `set_priority` + `set_task_name` → `rtm_update_task`

**Filesystem plugin (10 → 8, saved 2):**
- `copy_file` + `move_file` + `delete_file` → `fs_file_operation(action)`

**Workingtimes plugin (10 → 8, saved 2):**
- `get_time_entry` + `update_time_entry` + `delete_time_entry` → `wt_manage_time_entry(action)`

**Calendar plugin (9 → 8, saved 1):**
- `create_event` + `create_all_day_event` → `create_event(all_day=False)`

## Automated Guard

`tests/test_tool_count.py` loads all plugins and asserts the total tool count stays under 128. This test runs as part of the standard test suite.

## Guidelines for New Plugins

- Aim for ~10 tools maximum per plugin
- Merge CRUD groups (add/remove/list) into single tools with an `action` parameter
- See `docs/plugins/plugin-development-guide.md` for the consolidation pattern
