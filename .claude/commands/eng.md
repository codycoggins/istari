---
description: "Autonomous Istari engineering: pick backlog item → plan → implement → PR → CI → feedback"
allowed-tools: Bash, Read, Write, Edit, Agent, Skill
---

# /eng — Autonomous Engineering Workflow

Follow these phases in order. Stop and report if any unrecoverable error occurs.

---

## Phase 0: Select Backlog Item

Read `ROADMAP.md` at the project root.

Extract items from the **"Active Phase"** section first, then **"Backlog"** sections.

Present a numbered list, e.g.:
```
Active:
  1. Phase 8d — Deadlines + Recurrence

Backlog:
  2. Edit projects panel
  3. Bug: Mail tool hyperlinks display inconsistently
  ...
```

Ask: **"Which item should I work on? (enter a number)"**

Wait for the user's selection before proceeding.

---

## Phase 1: Research

Spawn an Explore agent for the selected item. Provide it with:
- The backlog item description
- Instructions to find all relevant files, patterns, and existing utilities
- Instructions to identify what new files or changes are needed

Read the key files it identifies before moving to Phase 2.

---

## Phase 2: Plan

Based on the research, enter plan mode:
- Ask the user up to 3 targeted clarifying questions as needed (use AskUserQuestion)
- Write a concise implementation plan covering: context, file changes, approach, and verification
- Call ExitPlanMode to request user approval

**Do not begin implementation until the user approves the plan.**

---

## Phase 3: Create Worktree Branch

Derive a short slug from the item name (lowercase, hyphens, max 5 words).

Create a git worktree with a new branch — this isolates the work from `main` and allows
multiple Claude sessions to develop features in parallel without conflicts:

```bash
git worktree add ../istari-eng-<slug> -b claude/eng-<slug>
```

Example: worktree at `../istari-eng-deadlines-recurrence`, branch `claude/eng-deadlines-recurrence`.

All subsequent phases operate from within the worktree directory (`../istari-eng-<slug>`).

---

## Phase 4: Implement

From within the worktree directory, implement the approved plan:
- Follow all patterns in CLAUDE.md
- Write tests for new functionality
- Keep changes focused — no scope creep beyond the plan
- If scope turns out significantly larger than planned, pause and check in with the user

---

## Phase 5: Finish

Update the ROADMAP.md and move the task item to the Completed Phases section with a summary

From within the worktree directory, run the full finish workflow (test → update CLAUDE.md → commit):

@.claude/commands/finish.md

If tests fail, propose a targeted fix and ask the user for permission before applying it.

---

## Phase 6: Push and Create PR

From within the worktree directory:

```bash
git push -u origin claude/eng-<slug>
gh pr create --title "<concise title under 70 chars>" --body "$(cat <<'EOF'
## Summary
<2-4 bullet points describing what was implemented>

## Test plan
- [ ] All CI checks pass
- [ ] <specific manual test steps if applicable>

https://claude.ai/code/session_01N8c66hZuGKkzRLJVPctZsk
EOF
)"
```

Report the PR URL to the user.

---

## Phase 7: CI Watch and Auto-Fix (up to 3 attempts)

Wait for the GitHub Actions run triggered by the push. There may be a short delay before
the run appears — retry up to 5 times with 10s sleep if needed:

```bash
RUN_ID=""
for i in 1 2 3 4 5; do
  RUN_ID=$(gh run list --branch claude/eng-<slug> --limit 1 --json databaseId -q '.[0].databaseId' 2>/dev/null)
  [ -n "$RUN_ID" ] && break
  sleep 10
done

gh run watch "$RUN_ID" --exit-status
```

**If CI passes:** proceed to Phase 8.

**If CI fails** (attempt this loop up to 3 times total):
1. Fetch the failure: `gh run view "$RUN_ID" --log-failed`
2. Diagnose and apply a targeted fix from within the worktree directory
3. Commit: `git commit -m "fix: address CI failure (<failing step>)"`
4. Push: `git push`
5. Get the new run ID (retry loop above) and watch again

If CI still fails after 3 fix attempts, stop and present the failure log summary to the
user. Ask how to proceed.

---

## Phase 8: User Feedback

Report:
- PR URL
- CI result (pass or fail, with run URL)
- Brief summary of what was implemented

Ask: **"Does this look good? Any changes before we merge?"**

If the user requests changes, implement them from the worktree directory, commit, push.
CI will re-run automatically. Repeat until the user is satisfied.

Once the user is done, offer to clean up the worktree:
```bash
git worktree remove ../istari-eng-<slug>
```
(The branch and PR are preserved on the remote.)

---

## Notes

- Branch names **must** start with `claude/` — the push policy enforces this
- Always `source backend/.venv/bin/activate` before any backend commands
- In the worktree, `node_modules` is not shared — run `cd frontend && npm install` before
  any frontend commands
- `git worktree list` shows all active worktrees across concurrent sessions
- Multiple Claude CLI sessions can each run `/eng` on different features simultaneously —
  each gets its own worktree directory and branch with no conflicts
