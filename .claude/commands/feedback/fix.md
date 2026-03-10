---
description: Fix issues from AI feedback reports in the feedback/ directory
---

Read and fix issues documented by the AI in feedback reports.

Steps:

1. List all `.md` files in the `feedback/` directory at the project root. If the directory does not exist or is empty, tell the user there are no feedback reports to process.

2. If $ARGUMENTS is provided, find the matching feedback file (partial match on filename, case-insensitive). If multiple match, list them and ask the user to pick one. If none match, show available files. If no $ARGUMENTS, list all feedback files with their titles and timestamps, and ask the user which one to work on.

3. Read the selected feedback file completely. Present a summary to the user:
   - The title and timestamp
   - The user who triggered it
   - The core issue described

4. **Investigate**: Search the codebase for the relevant code mentioned in the feedback. Understand the root cause of the issue described.

5. **Propose fix**: Present your proposed changes and wait for user approval before implementing.

6. **Implement the fix**: Make the code changes.

7. **Verify**: Run the project tests and code analysis as described in CLAUDE.md to ensure the fix does not break anything.

8. If verification passes, move the feedback file to `feedback/done/` (create the subdirectory if it does not exist) and tell the user they can commit with /git:commit.

9. If verification fails, report the failures and ask the user how to proceed.
