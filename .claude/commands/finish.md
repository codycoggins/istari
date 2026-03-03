---
description: "Run full finish workflow: test, update CLAUDE.md, then commit"
allowed-tools: Bash, Read, Write
---

Run the complete finish workflow in this exact order. Stop and report if any step fails.
## Step 0: Run Database migrations
If there are any new alembic migrations not run, run them
in CLAUDE.md, note the most recent migration run 

## Step 1: Run Tests
@.claude/commands/test.md

If there are any test failures, propose a fix and ask user for permission to proceed.

## Step 2: Update CLAUDE.md
Update the "Current Status" section in CLAUDE.md with progress from session.  
If there are new development commands, "Development Commands"

## Step 3: Commit
If previous steps were successful, commit the changes