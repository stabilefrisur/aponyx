# Clean Up Git Worktrees and Feature Branches

Clean up stale git worktrees and merged feature branches from this repository.

## Tasks

1. **List all git worktrees** using `git worktree list`
2. **Remove any worktrees** that are not the main workspace (remove nested worktrees first, working from deepest to shallowest)
3. **Prune stale worktree references** using `git worktree prune`
4. **List all local branches** using `git branch`
5. **Identify feature branches** that have been merged to master (branches matching patterns like `###-feature-name` where ### is a spec number)
6. **Confirm with user** which branches to delete before removing them
7. **Delete confirmed branches** using `git branch -D <branch-name>`
8. **Clean up worktree directories** if any remain (e.g., `*.worktrees` folders)

## Commands Reference

```bash
# List worktrees
git worktree list

# Remove a worktree (use --force if needed)
git worktree remove "<path>" --force

# Prune stale worktree references
git worktree prune

# List all branches
git branch -a

# Delete local branch
git branch -D <branch-name>

# Check if branch is merged to master
git branch --merged master
```

## Notes

- Always remove nested worktrees before their parent worktrees
- Use `--force` flag when removing worktrees that may have uncommitted changes
- Feature branches following the `###-feature-name` pattern (e.g., `007-research-dashboard`) are typically safe to delete once merged
- Worktree branches often follow the pattern `worktree-YYYY-MM-DDTHH-MM-SS`
