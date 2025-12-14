---
description: Automate the complete PyPI release workflow including version bumping, quality checks, building, publishing, and verification.
arguments:
  - name: bump_mode
    description: Version bump type (patch, minor, or major)
    required: true
---

## User Input

```text
$ARGUMENTS
```

You **MUST** parse the bump_mode argument before proceeding. Valid values: `patch`, `minor`, `major`.

## Goal

Execute a complete PyPI release workflow for the aponyx package:
1. Bump version and update documentation
2. Run quality checks and tests
3. Build distribution packages
4. Publish to PyPI (with user authentication)
5. Create git tag and GitHub release
6. Verify installation from PyPI

## Prerequisites Validation

Before executing any steps, verify:

1. **Working directory is clean**
   ```bash
   git status
   ```
   No uncommitted changes allowed.

2. **On master branch**
   ```bash
   git branch --show-current
   ```
   Must be on `master`.

3. **Local branch is up to date**
   ```bash
   git fetch origin
   git status
   ```
   Must be in sync with remote.

4. **Confirm bump_mode parameter**
   Extract from $ARGUMENTS and validate it's one of: patch, minor, major

If any prerequisite fails, **STOP** and report the issue to the user.

## Execution Steps

### Step 1: Version Bump and Documentation

**1.1 Bump version**
```bash
uv version --bump {bump_mode}
```

This automatically updates `pyproject.toml` and `uv.lock`.

**1.2 Determine version numbers**
- Extract new version from `pyproject.toml`: `version = "X.Y.Z"`
- Determine previous version by subtracting 1 from the bumped component

**1.3 Review changes since last release**

**CRITICAL:** You MUST review ALL commits before writing the changelog. Do not skip this step.

```bash
# Get commit list
git log v{previous_version}..HEAD --oneline --no-merges

# Get detailed commit messages with bodies
git log v{previous_version}..HEAD --format="%H|%s|%b" --no-merges

# Get diff statistics
git diff v{previous_version}..HEAD --stat
```

**Required:** Read through every commit message and body to understand:
- What features were added
- What functionality changed
- What bugs were fixed
- What breaking changes occurred
- Test coverage changes
- Documentation updates

**1.4 Update CHANGELOG.md**

**CRITICAL:** Base the changelog entry on the actual commit history reviewed in step 1.3, not on assumptions.

- Add new version section at top (after "Unreleased" if present)
- Format: `## [X.Y.Z] - YYYY-MM-DD`
- Categorize changes into:
  - **Added** - New features (from feature commits)
  - **Changed** - Changes in existing functionality (from refactor/change commits)
  - **Fixed** - Bug fixes (from fix commits)
  - **Deprecated** - Soon-to-be removed features (if any)
  - **Removed** - Removed features (if any)
  - **Security** - Security fixes (if any)
  - **Breaking Changes** - List all breaking changes in separate section
  - **Test Coverage** - Document test count changes
- Include comprehensive details from commit messages and bodies
- Group related commits under common themes (e.g., "Four-Stage Transformation Pipeline")
- Update version comparison links at bottom:
  - Add: `[X.Y.Z]: https://github.com/stabilefrisur/aponyx/compare/v{previous}...vX.Y.Z`

**Validation:**
- Changelog entry covers ALL commits from step 1.3
- No commits are missing from the changelog
- Breaking changes are clearly documented
- Test coverage updates are included

**1.5 Update README.md**
- Find footer section with version/date
- Update version number to X.Y.Z
- Update date to current date (YYYY-MM-DD)

**1.6 Update PROJECT_STATUS.md**
- Update version number to X.Y.Z
- Update "Last Updated" date to current date

**Validation:**
- Confirm `pyproject.toml` shows new version
- Confirm `CHANGELOG.md` has comprehensive new entry
- Confirm `README.md` footer updated
- Confirm `PROJECT_STATUS.md` updated

**DO NOT COMMIT YET** - All changes committed together after quality checks.

### Step 2: Clean Build Environment

**2.1 Remove Python bytecode**
```bash
uv run python scripts/clean_pycache.py
```

**2.2 Clean runtime data**
```bash
uv run python scripts/clean_runtime_data.py
```

**2.3 Clean workflow outputs**
```bash
uv run aponyx clean --all
```

**Validation:**
- Confirm no `__pycache__` directories remain
- Confirm `data/.registries/` cleaned
- Confirm `data/workflows/` cleaned

### Step 3: Quality Checks and Fixes

**3.1 Run tests**
```bash
uv run pytest tests/ --ignore=tests/data/test_bloomberg.py -v
```

**Expected:** All tests should pass. Check actual test count from output (documented as 755 as of v0.1.16).

If ANY tests fail, **STOP** and report to user which tests failed and why.

**3.2 Auto-fix linting**
```bash
uv run ruff check --fix src/aponyx
```

**3.3 Auto-format code**
```bash
uv run ruff format src/ tests/
```

**Validation:**
- All tests passed
- No ruff violations remain
- Code formatting applied

**3.4 Single atomic commit**

After all quality checks pass, create ONE commit with all changes:

```bash
git add -A
git commit -m "chore: release vX.Y.Z

- Bump version to X.Y.Z
- Update CHANGELOG.md with comprehensive release notes
- Update version in README.md and PROJECT_STATUS.md
- Apply ruff formatting and linting fixes"
```

Use actual version number in commit message.

### Step 4: Build Distribution

**4.1 Clean old build artifacts**
```bash
rm -f dist/aponyx-*
```

**4.2 Build distributions**
```bash
uv build
```

**4.3 Verify artifacts**
```bash
ls dist/
```

**Validation:**
- `dist/aponyx-X.Y.Z-py3-none-any.whl` exists
- `dist/aponyx-X.Y.Z.tar.gz` exists

### Step 5: Local Installation Test

**5.1 Create clean test environment**
```bash
uv venv test-env --python 3.12
```

**5.2 Install from local wheel**
```bash
uv pip install dist/aponyx-X.Y.Z-py3-none-any.whl --python test-env
```

**5.3 Test version import**
```bash
test-env/Scripts/python -c "from aponyx import __version__; print(__version__)"
```

Expected output: `X.Y.Z`

**5.4 Test basic functionality**
```bash
test-env/Scripts/python -c "from aponyx.models import compute_cdx_etf_basis; print('Import successful')"
```

Expected output: `Import successful`

**5.5 Clean up test environment**
```bash
rm -rf test-env
```

**Validation:**
- Package installed without errors
- Version matches expected X.Y.Z
- Core imports work correctly

### Step 6: Publish to PyPI

**⚠️ HUMAN INTERVENTION REQUIRED ⚠️**

Execute publish command:
```bash
uv publish
```

**Report to user:**
```
=== PyPI AUTHENTICATION REQUIRED ===

Please complete the PyPI upload:
1. The publish command will prompt for credentials
2. Enter your PyPI username (or __token__)
3. Enter your PyPI password (or API token)
4. Confirm upload when prompted

If using API token:
- Username: __token__
- Password: pypi-... (your token)

Waiting for upload completion...
```

**After user completes:** Verify success message appears.

### Step 7: Create Git Tag and Push

**7.1 Create annotated tag**
```bash
git tag -a vX.Y.Z -m "Release version X.Y.Z"
```

**7.2 Push commits to remote**
```bash
git push origin master
```

**7.3 Push tag to remote**
```bash
git push origin vX.Y.Z
```

**Validation:**
- Tag created successfully locally
- Commits pushed to remote
- Tag pushed to remote

### Step 8: Create GitHub Release

**⚠️ HUMAN INTERVENTION REQUIRED ⚠️**

**Report to user:**
```
=== GITHUB RELEASE CREATION REQUIRED ===

Please create the GitHub release manually:

1. Navigate to: https://github.com/stabilefrisur/aponyx/releases/new

2. Fill in the form:
   - Tag: vX.Y.Z (select from dropdown)
   - Release title: vX.Y.Z - [Brief Description]
   - Description: Copy the CHANGELOG.md section below

3. Click "Publish release"

--- CHANGELOG SECTION TO COPY ---
[Extract and format the CHANGELOG.md section for vX.Y.Z]
--- END CHANGELOG SECTION ---
```

Provide user with:
- Direct URL to release creation page
- Formatted CHANGELOG section ready to copy-paste

### Step 9: Verify PyPI Installation

**Note:** PyPI indexing may take 2-3 minutes. If installation fails immediately, wait and retry.

**9.1 Create verification environment**
```bash
uv venv verify-env --python 3.12
```

**9.2 Install from PyPI**
```bash
uv pip install aponyx==X.Y.Z --python verify-env
```

If this fails with "No matching distribution", wait 60 seconds and retry up to 3 times.

**9.3 Verify version**
```bash
verify-env/Scripts/python -c "from aponyx import __version__; print(__version__)"
```

Expected: `X.Y.Z`

**9.4 Clean up**
```bash
rm -rf verify-env
```

**9.5 Optional: Test viz extras**
```bash
pip install aponyx[viz]==X.Y.Z --dry-run
```

**Validation:**
- Package available on PyPI
- Installation successful
- Version matches release

## Success Criteria

Report success when ALL of the following are complete:
- ✅ Version bumped in pyproject.toml, CHANGELOG.md, README.md, PROJECT_STATUS.md
- ✅ All commits since last release reviewed and documented in CHANGELOG.md
- ✅ All tests passed (verify actual count from test output)
- ✅ Ruff checks and formatting applied
- ✅ Single atomic commit created
- ✅ Distribution built (.whl and .tar.gz)
- ✅ Local installation test passed
- ✅ Published to PyPI successfully
- ✅ Git tag created and pushed
- ✅ GitHub release created (by user)
- ✅ PyPI installation verified

**Final report:**
```
=== PYPI RELEASE COMPLETE ===

Version: X.Y.Z
Bump mode: {bump_mode}
Commit: {git_commit_hash}
Tag: vX.Y.Z
PyPI URL: https://pypi.org/project/aponyx/X.Y.Z/
GitHub Release: https://github.com/stabilefrisur/aponyx/releases/tag/vX.Y.Z

All steps completed successfully!
```

## Rollback Procedure

If failure occurs **before Step 6** (PyPI publish):

```bash
# Reset commit
git reset --hard HEAD~1

# Delete local tag if created
git tag -d vX.Y.Z

# Clean build artifacts
rm -rf dist/

# Reset version in pyproject.toml manually to previous version
```

Report to user: "Release aborted. All changes rolled back."

If failure occurs **after Step 6** (PyPI published):

**CANNOT ROLLBACK** - PyPI does not allow deleting published versions.

Options:
1. Create a hotfix version (X.Y.Z+1)
2. Document the issue in the GitHub release notes
3. Yank the version on PyPI if critically broken

Report to user: "Version published to PyPI - cannot rollback. Consider hotfix release."

## Common Issues

**Tests fail:**
- Do NOT proceed with release
- Report which tests failed
- Instruct user to fix tests and restart workflow

**Ruff violations can't be auto-fixed:**
- Report violations
- Apply `--fix` where possible
- Instruct user to manually fix remaining issues

**PyPI upload fails:**
- Check if version already exists on PyPI
- Verify credentials format
- Ensure 2FA token is valid (if using token auth)

**Git push fails:**
- Check remote permissions
- Verify branch protection rules
- Ensure remote URL is correct

**PyPI package not found after publish:**
- Normal - indexing takes 2-3 minutes
- Retry verification up to 3 times with delays
- Check https://pypi.org/project/aponyx/ manually

## Notes

- Version format follows semantic versioning: X.Y.Z
- Single commit strategy ensures atomic release state
- Always test local installation before publishing
- PyPI uploads are permanent (cannot delete)
- Notebooks using `aponyx.__version__` auto-update (no manual changes needed)
