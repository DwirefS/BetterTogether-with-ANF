# Agent Rules — MANDATORY for ALL Sessions

> This file defines non-negotiable rules for any AI agent (Claude, Copilot, or otherwise)
> operating on this repository or any repository owned by DwirefS. These rules apply
> regardless of context, urgency, or perceived benefit. Copy this file to any new repo.

---

## Rule 1: NEVER Run Destructive Commands Without Explicit Permission

The following commands are **BANNED** unless the user types the exact command and says "run this":

### Git — History & Working Tree Destruction

```
git filter-repo          # Rewrites history, DESTROYS untracked files
git filter-branch        # Rewrites history, DESTROYS untracked files
git clean -f             # Deletes untracked files
git clean -fd            # Deletes untracked files AND directories
git clean -fdx           # Deletes untracked AND gitignored files (WORST)
git reset --hard         # Discards all uncommitted changes
git checkout -- .        # Discards all unstaged changes
git restore .            # Discards all unstaged changes
git push --force         # Overwrites remote history
git push --force-with-lease  # Overwrites remote history (safer but still destructive)
git rebase               # Rewrites commit history
git stash drop           # Permanently deletes stashed changes
git branch -D            # Force-deletes a branch without merge check
```

### File System — Deletion

```
rm -rf                   # Recursive force delete
rm -f                    # Force delete without confirmation
shred                    # Permanently destroys file content
```

### Docker / Kubernetes — Destructive

```
docker system prune      # Removes all unused containers, images, networks
kubectl delete namespace # Destroys entire namespace and all resources
helm uninstall           # Removes deployed release
```

**If the agent believes a destructive command is necessary, it MUST:**

1. Explain what the command does in plain language
2. Explain exactly what will be deleted, lost, or changed
3. Explain what CANNOT be recovered afterward
4. Suggest a safer alternative if one exists
5. Wait for explicit user approval before proceeding

---

## Rule 2: ALWAYS Backup Before Destructive Operations

If the user explicitly approves a destructive command, the agent MUST:

1. **Copy any untracked/gitignored files** to a safe location outside the repo FIRST
2. **List what will be affected** and confirm the backup is complete
3. Only THEN execute the approved command

Example of what went wrong: `git filter-repo` rewrites history and resets the working
directory. Gitignored files like `keptLocal/` are not in any commit, so they get wiped.
The agent should have copied `keptLocal/` to `/tmp/` before running the command.

---

## Rule 3: Gitignored Files Are LOCAL — Respect Them

- `.gitignore` means "git should not track this" — it does NOT mean "this is disposable"
- Gitignored files often contain the most important local data: credentials, private docs,
  deployment journals, configuration with real values
- NEVER delete, move, or modify gitignored files without asking
- NEVER run any command that has a side effect of removing gitignored files

---

## Rule 4: Credential & Secret Safety

- NEVER hardcode passwords, API keys, tokens, or secrets in any tracked file
- NEVER commit `.env` files, kubeconfig files, or SSH keys
- Always use environment variables, Key Vault references, or placeholder values
- Before every push to a public repo, grep for: passwords, API keys, subscription IDs,
  tenant IDs, client secrets, private IP addresses, email addresses, and PII
- If a secret is accidentally committed, inform the user and let THEM decide how to fix it

---

## Rule 5: Always Explain Before Acting

For any operation that:

- Modifies git history
- Deletes files (tracked or untracked)
- Changes branch structure
- Pushes to a remote
- Modifies system files or configurations

The agent MUST explain what it's about to do and wait for confirmation.
"I'm going to run X which does Y" is not enough.
"I'm going to run X. This will permanently delete Y and Z. This cannot be undone. Should I proceed?" is the minimum.

---

## Rule 6: Git Workflow Standards

- Create NEW commits, never amend unless explicitly asked
- Never skip hooks (--no-verify)
- Never force-push to main/master
- Stage specific files, not `git add -A` or `git add .`
- Use descriptive commit messages with conventional commit prefixes (feat, fix, docs, etc.)
- Always check `git status` before and after commits

---

## Rule 7: When In Doubt, ASK

If there is ANY ambiguity about whether an action is safe, the agent should ask.
It is always better to ask a "dumb" question than to destroy the user's work.
The user's local files, private documents, and git history are irreplaceable.

---

## Summary of Banned Commands (Quick Reference)

| Command | Risk | What It Destroys |
|---------|------|-----------------|
| `git filter-repo` | CRITICAL | Rewrites all history, deletes untracked + gitignored files |
| `git filter-branch` | CRITICAL | Same as filter-repo |
| `git clean -fdx` | CRITICAL | All untracked AND gitignored files gone forever |
| `git clean -fd` | HIGH | All untracked files and directories gone |
| `git reset --hard` | HIGH | All uncommitted changes gone |
| `git push --force` | HIGH | Remote history overwritten, others lose work |
| `rm -rf` | CRITICAL | Recursive delete, no recovery |
| `git rebase` | MEDIUM | Rewrites commit history, can lose changes |
| `git stash drop` | MEDIUM | Stashed work gone forever |
| `git branch -D` | MEDIUM | Branch force-deleted even if unmerged |

# Agent Operating Contract

This repository is worked on by multiple humans and agents across many sessions.
Treat this file as a standing working agreement, not a suggestion.

## Primary Goals

- Maintain delivery speed without losing traceability.
- Preserve durable project memory across sessions and collaborators.
- Prevent secrets, credentials, PII, internal-only material, and protected information from entering commits or public remotes.
- Keep code readable, reversible, and explainable.

## Standing Authority

- The agent may inspect files, edit code, run tests, run linters, and update project memory files without asking again.
- The agent may create local commits after passing the required audit and verification steps in this file.
- The agent must not push, merge, force-push, delete branches, rewrite history, or run destructive cleanup commands unless this file or the user explicitly allows it.
- If the user says "do not change files", the agent must only audit, inspect, and report.
- If the agent finds a likely secret, protected data, or PII exposure, the agent must stop and report it before any commit or push.

## Persistent Project Memory

The agent must maintain these files as the durable memory of the project:

- `TODO.md` for the canonical task list.
- `WORKLOG.md` for an append-only session log.
- `DECISIONS.md` for important technical and product decisions.
- `AUDIT_LOG.md` for security/privacy/release audit results.

If any file does not exist, create it before substantial work begins.

At the start of every session, the agent must read:

- `AGENTS.md`
- `TODO.md`
- `WORKLOG.md`
- `DECISIONS.md`
- `AUDIT_LOG.md`

## TODO Rules

- `TODO.md` is the single source of truth for open work across sessions.
- Every task must include: ID, title, status, priority, owner, date, dependencies, and notes.
- Allowed statuses: `todo`, `in_progress`, `blocked`, `review`, `done`, `deferred`.
- Before starting work, move the task to `in_progress`.
- Before ending the session, update task state and notes.
- If the agent discovers new work, add it immediately instead of keeping it only in chat memory.

## WORKLOG Rules

- `WORKLOG.md` is append-only and chronological.
- Every meaningful work session must add a short entry with:
- Date/time
- Agent or collaborator name
- Task worked on
- Files touched
- Commands run
- Tests run
- Audit result
- Risks, blockers, and follow-ups
- The log should be concise but durable enough that another collaborator can resume work without chat history.

## DECISIONS Rules

- Use `DECISIONS.md` for durable rationale.
- Record architecture, API, schema, deployment, security, or workflow decisions.
- Every decision entry must include:
- Date
- Decision
- Reason
- Alternatives considered
- Consequences
- If a change reverses a prior decision, note the superseded entry.

## Change Management Rules

- Prefer small, coherent changes over large mixed refactors.
- Never silently change behavior.
- If behavior changes, document it in `WORKLOG.md` and, if important, `DECISIONS.md`.
- Preserve unrelated user changes.
- Do not revert or overwrite another collaborator's work unless explicitly instructed.
- Keep comments focused on intent and rationale, not obvious mechanics.

## Deletion and Deprecation Rules

- Do not make "delete immediately" the default for important shared logic during active collaboration.
- If code is risky to remove, likely to be revisited, or useful for collaborator context, comment it out first and explain why.
- When commenting out a block, include:
- Date
- Author
- Reason
- Replacement or follow-up plan
- Condition for final removal
- For trivial dead code, generated code, duplicated code, or formatting-only leftovers, delete cleanly instead of commenting it out.
- For secrets, credentials, or dangerous logic, remove immediately and document the reason in `WORKLOG.md`. Never preserve secret values in comments.
- If the file format does not support comments, move the removed block and rationale to `WORKLOG.md` or `DECISIONS.md`.

Use this tombstone style when disabling code:

```text
DISABLED 2026-03-07 by <agent-or-name>
Reason: <why this was disabled>
Replacement: <new path/function/feature or "none yet">
Remove after: <condition or date>
Reference: TODO-### / decision entry / issue link
Security and Privacy Rules
Assume this repository may become public unless explicitly stated otherwise.
Never commit real secrets, keys, tokens, passwords, certificates, connection strings, kubeconfigs, .env files, or cloud credentials.
Never commit tenant IDs, subscription IDs, client IDs, object IDs, app IDs, private IPs, internal URLs, internal screenshots, access request documents, customer data, or support exports unless explicitly approved as publishable.
Azure secrets belong in Azure Key Vault, not in source control.
If an example value is needed, use an obvious placeholder.
Never print secret values into logs, chat, commit messages, or code comments.
Redact sensitive values in all reports.
Mandatory Pre-Commit Audit
Before any local commit, the agent must perform a security and privacy audit.

Minimum required checks:

Review git status and git diff --staged.
Review all changed files manually for secrets, PII, internal-only content, and accidental exports.
Check that ignored local-only files are not staged.
Run tests or verification relevant to the change.
Update WORKLOG.md, TODO.md, and AUDIT_LOG.md.
If gitleaks is installed, run it on both the working tree and reachable history.

If gitleaks is not installed, run fallback checks like these:

git status --short
git diff --staged --stat
git diff --staged

rg -n --hidden --glob '!.git' '(?i)(password|secret|token|api[_-]?key|client[_-]?secret|connection[_-]?string|tenant[_-]?id|subscription[_-]?id|app[_-]?id|private[_-]?key|access[_-]?key)'

git grep -nI -E '(AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]+|sk-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z\-_]{35}|-----BEGIN (RSA|EC|OPENSSH|PGP|PRIVATE) KEY-----|-----BEGIN CERTIFICATE-----)' $(git rev-list --all)

git log --all --name-only --pretty=format: | rg '(^|/)(\.env(\..*)?$|.*\.(pem|key|p12|pfx|crt|cer|jks|kubeconfig|tfstate|tfvars)$|id_rsa.*|id_ed25519.*|ngc-config$|.*outputs\.json$|deployment-.*\.json$)'
For public repositories, also check for:

Internal-only docs
Access request drafts
Exported dashboards
Incident logs
IP addresses
Emails
Support notes
Private architecture notes
Local scratch files
Cached artifacts
Cloud state/output files
If any check is suspicious, the agent must inspect the match manually before committingCommit Policy
Local commits are allowed after the audit passes.
Each commit must be a coherent unit of work.
Commit messages must be clear and specific.
Do not hide unrelated changes inside the same commit.
If audit findings exist, do not commit until they are resolved or explicitly accepted by the user.
Record the audit outcome in AUDIT_LOG.md before committing.
Push Policy
Choose one mode and keep it consistent.

Recommended default:

The agent may push only after a clean audit and only to a non-protected feature branch dedicated to the current task.
The agent must never push directly to a protected branch without explicit user approval.
Stricter option:

The agent must never push without explicit user approval.
If you want the stricter option, replace the recommended default with that rule and use it everywhere.

Testing and Verification Rules
Run the smallest meaningful verification first.
Before ending work, run the most relevant tests, lint checks, type checks, or smoke checks available for the touched area.
If verification cannot be run, say exactly why.
Never claim something is working unless it was actually verified or the statement is clearly marked as an assumption.
Collaboration Rules
Write for the next collaborator, not just the current session.
Leave enough context in files that another human or agent can continue without chat history.
When blocked, record the blocker in TODO.md and WORKLOG.md.
When making assumptions, write them down.
If requirements are ambiguous, prefer the safest reversible option and document the assumption.
Do not rely on ephemeral chat memory for project-critical context.
End-of-Session Handoff
Before ending a session, the agent must:

Update TODO.md
Append to WORKLOG.md
Add any durable rationale to DECISIONS.md
Add the audit result to AUDIT_LOG.md
Summarize:
What changed
What was verified
What remains open
What risks or blockers exist
Which files were touched.Non-Negotiables
No real secrets in source control.
No silent behavior changes.
No destructive Git actions without explicit approval.
No wiping collaborator context.
No relying on temporary session memory for persistent project state.
# Agent Rules

This repo is worked on across multiple sessions by multiple humans and agents.
Work so another collaborator can resume without chat history.

## Standing Authority

- The agent may read files, edit code, run tests, run linters, update docs, and create local commits without asking again.
- The agent may push only after a clean audit, and only to the current non-protected working branch.
- The agent must not force-push, rewrite history, merge to protected branches, or run destructive Git commands unless explicitly told to.

## Persistent Memory

Maintain these files as project memory:

- `TODO.md`
- `WORKLOG.md`
- `DECISIONS.md`
- `AUDIT_LOG.md`

At the start of each session, read them.
At the end of each session, update them.

## TODO Rules

- `TODO.md` is the source of truth for open work.
- Every task should include ID, title, status, priority, owner, and notes.
- Valid statuses: `todo`, `in_progress`, `blocked`, `review`, `done`, `deferred`.
- Move the active item to `in_progress` before starting.

## Worklog Rules

- Append every meaningful session to `WORKLOG.md`.
- Include date, collaborator/agent, task, files touched, tests run, audit result, blockers, and next steps.

## Decision Rules

- Record important architecture, workflow, schema, deployment, or product decisions in `DECISIONS.md`.
- Include what was decided, why, alternatives, and consequences.

## Change Rules

- Prefer small, clear, reversible changes.
- Never silently change behavior.
- Preserve unrelated collaborator changes.
- Add comments only where intent or rationale would otherwise be unclear.

## Deletion Rules

- For important shared logic under active collaboration, do not immediately hard-delete by default.
- First comment out or disable the block when useful for team context, and explain:
- Date
- Author
- Reason
- Replacement or next step
- Removal condition
- For trivial dead code, generated code, or obvious duplication, delete cleanly instead of commenting it out.
- Never keep secrets in comments.

Suggested disabled-code marker:

DISABLED YYYY-MM-DD by <name>
Reason: <why>
Replacement: <new path/function or none yet>
Remove after: <condition>
Reference: <task/decision>

## Security Rules

- Never commit real secrets, tokens, passwords, keys, `.env` files, kubeconfigs, certificates, or cloud credentials.
- Never commit private/internal-only docs, support notes, tenant IDs, subscription IDs, client secrets, exported state, or PII unless explicitly approved as publishable.
- Use placeholders for examples.
- Azure secrets belong in Key Vault, not Git.

## Mandatory Audit Before Commit or Push

Before every commit or push:

- Review `git status`
- Review staged diff
- Check changed files for secrets, PII, and internal-only content
- Run relevant tests or verification
- Update `AUDIT_LOG.md`

If something looks sensitive, stop and report it before continuing.

## Session Closeout

Before ending a session:

- Update `TODO.md`
- Append to `WORKLOG.md`
- Add important rationale to `DECISIONS.md`
- Record audit outcome in `AUDIT_LOG.md`
- Summarize what changed, what was verified, and what remains open
# Agent Rules For Public Repositories

This repository is public or may become public.
Optimize for traceability, auditability, and zero secret leakage.

## Authority

- The agent may inspect files, modify code, run tests, maintain memory files, and create local commits without asking again.
- The agent may push only after all required audit checks pass and only to a non-protected feature branch.
- The agent must not push to `main`, force-push, rewrite history, delete branches, merge, tag releases, or run destructive Git cleanup unless explicitly instructed.

## Required Project Memory

The agent must maintain:

- `TODO.md`
- `WORKLOG.md`
- `DECISIONS.md`
- `AUDIT_LOG.md`

If missing, create them immediately.

The agent must read all four before beginning work.

## Required TODO Format

Each task entry must include:

- ID
- Title
- Status
- Priority
- Owner
- Date opened
- Dependencies
- Notes

Allowed statuses:

- `todo`
- `in_progress`
- `blocked`
- `review`
- `done`
- `deferred`

## Required Worklog Format

Every session must append an entry to `WORKLOG.md` including:

- Date and time
- Agent/collaborator
- Task ID
- Summary of work
- Files changed
- Commands run
- Tests run
- Audit result
- Risks
- Next steps

`WORKLOG.md` is append-only.

## Required Decision Log Format

Record all significant decisions in `DECISIONS.md`:

- Date
- Decision
- Reason
- Alternatives considered
- Consequences
- Supersedes or related decision, if any

## Change Management

- Prefer small, coherent commits.
- Do not mix refactor, feature, audit, and docs work in one commit unless tightly related.
- Do not overwrite unrelated work from other collaborators.
- Do not claim behavior is verified unless it was actually verified.

## Deprecation and Deletion Policy

- For important shared logic, first disable/comment out instead of hard-deleting when that context will help collaborators.
- Every disabled block must explain:
- Date
- Author
- Reason
- Replacement
- Removal trigger
- For trivial dead code or obvious duplication, delete it cleanly.
- For secrets, credentials, or dangerous logic, remove immediately and document the removal in `WORKLOG.md` and `AUDIT_LOG.md`. Never preserve secret values in comments.

Required tombstone style:

DISABLED YYYY-MM-DD by <name>
Reason: <why disabled>
Replacement: <what replaces it>
Remove after: <condition/date>
Reference: <task ID or decision>

## Public Repo Security Rules

Never commit any of the following:

- Real API keys
- Passwords
- Client secrets
- Private keys
- Certificates
- `.env` files with values
- Kubeconfigs
- Terraform state
- Deployment output files
- Tenant IDs
- Subscription IDs
- App IDs
- Client IDs tied to real environments
- Internal hostnames
- Private IPs
- Internal screenshots
- Access request docs
- Incident notes
- Customer data
- PII
- Support exports
- Debug dumps from real environments

Use obvious placeholders only.

All real secrets must live in secret managers such as Azure Key Vault.

## Mandatory Audit Before Every Commit

Before every commit, the agent must:

- Review `git status --short`
- Review `git diff --staged --stat`
- Review `git diff --staged`
- Review all changed files manually for secrets, PII, internal-only material, and accidental exports
- Run relevant tests, lint, type check, or smoke checks
- Update `AUDIT_LOG.md`

If available, run `gitleaks` on the working tree and reachable history.

If `gitleaks` is unavailable, run these fallback checks:

```bash
git status --short
git diff --staged --stat
git diff --staged

rg -n --hidden --glob '!.git' '(?i)(password|secret|token|api[_-]?key|client[_-]?secret|connection[_-]?string|tenant[_-]?id|subscription[_-]?id|app[_-]?id|private[_-]?key|access[_-]?key)'

git grep -nI -E '(AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]+|sk-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z\-_]{35}|-----BEGIN (RSA|EC|OPENSSH|PGP|PRIVATE) KEY-----|-----BEGIN CERTIFICATE-----)' $(git rev-list --all)

git log --all --name-only --pretty=format: | rg '(^|/)(\.env(\..*)?$|.*\.(pem|key|p12|pfx|crt|cer|jks|kubeconfig|tfstate|tfvars)$|id_rsa.*|id_ed25519.*|ngc-config$|.*outputs\.json$|deployment-.*\.json$)'
