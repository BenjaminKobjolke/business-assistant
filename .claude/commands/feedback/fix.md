---
description: Fix issues from AI feedback reports in the feedback/ directory
---

Read and fix issues documented by the AI in feedback reports.

Steps:

1. List all `.md` files in the `feedback/` directory at the project root. If the directory does not exist or is empty, tell the user there are no feedback reports to process.

2. If $ARGUMENTS is provided, find the matching feedback file (partial match on filename, case-insensitive). If multiple match, list them and ask the user to pick one. If none match, show available files. If no $ARGUMENTS, process **all** feedback files sequentially (oldest first). Do NOT ask the user which one to work on.

3. Read each feedback file completely. Present a summary to the user:
   - The title and timestamp
   - The user who triggered it
   - The core issue described

4. **For each feedback file**, repeat steps 5-9 before moving to the next file:

5. **Investigate**: Search the codebase for the relevant code mentioned in the feedback. Understand the root cause of the issue described.

6. **Implement the fix**: Present a brief summary of what you're changing, then make the code changes immediately. Do NOT wait for user approval.

8. **Verify**: Run the project tests and code analysis as described in CLAUDE.md to ensure the fix does not break anything.

9. If verification passes, move the feedback file to `feedback/done/` (create the subdirectory if it does not exist).

10. If verification fails, report the failures and ask the user how to proceed.

11. After all feedback files are processed, tell the user they can commit with /git:commit.
