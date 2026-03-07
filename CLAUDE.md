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
