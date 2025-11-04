# 🧭 Maintenance Manual for Forked Package

This document describes how to **keep the local fork of the external PyPI package up to date** using `uv`, `Git`, and `PowerShell` on **GitLab**.  
This workflow applies to **a single upstream package**.  
Your main branch is named **`master`**, and you **will not publish to TestPyPI**.

---

## ⚙️ Prerequisites

Before running updates, ensure that you have:

- **`uv`** installed — [https://docs.astral.sh/uv](https://docs.astral.sh/uv)  
- **Git** installed and configured with your GitLab credentials  
- **PowerShell** ≥ 7.0  
- A local fork repository set up with:
  - `master` branch → your modified fork  
  - `upstream` branch → raw imports from PyPI  
- The script `Update-Upstream.ps1` placed in the repository root.

---

## 🏗️ Initial Setup: Creating the Fork from PyPI

If you're setting up the fork for the first time, follow these steps:

### Step 1 — Create GitLab Repository

Create a new repository on GitLab:

```bash
# On GitLab: New Project → Blank Project
# Name: <package-name>-fork
# Visibility: Private (recommended)
# Initialize with README: No
```

### Step 2 — Initialize Local Repository

```powershell
# Create project directory
mkdir <package-name>-fork
cd <package-name>-fork

# Initialize git and create master branch
git init
git checkout -b master
```

### Step 3 — Download Package from PyPI

```powershell
# Check available versions
pip index versions <PackageName>

# Download the latest version (adjust version as needed)
$version = "X.Y.Z"
pip download --no-deps --no-binary :all: <PackageName>
```

This downloads the `.tar.gz` source distribution to the current directory.

### Step 4 — Extract and Import Source Code

```powershell
# Extract the tarball
tar -xzf <PackageName>-$version.tar.gz

# Copy source files to repository root
cp -r <PackageName>-$version/* .

# Remove extraction artifacts
rm -r <PackageName>-$version
rm <PackageName>-$version.tar.gz
```

### Step 5 — Create Upstream Branch

```powershell
# Commit to master
git add .
git commit -m "Initial import from PyPI v$version"

# Create upstream branch from master
git checkout -b upstream
git tag "v$version-upstream"

# Return to master
git checkout master
```

### Step 6 — Configure Remote and Push

```powershell
# Add GitLab remote
git remote add origin git@gitlab.com:<username>/<package-name>-fork.git

# Push both branches
git push -u origin master
git push -u origin upstream
git push --tags
```

### Step 7 — Make Your Modifications

Now you can modify the code on `master`:

```powershell
# Make changes to source files
# ...

# Commit your modifications
git add .
git commit -m "feat: Add custom modifications"

# Update version in pyproject.toml
# version = "X.Y.Z.post1"

# Tag the fork
git tag "v$version-fork1"
git push origin master --tags
```

### Step 8 — Copy Update Script

Copy `Update-Upstream.ps1` to your repository root for future updates.

---

## 🚀 Workflow: Keeping the Fork Updated

### Step 1 — Check for New Upstream Version

From PowerShell:

```powershell
uv pip index versions <PackageName>
```

Compare with the last version tag in your repo (e.g., `v1.4.2-fork1`).

---

### Step 2 — Run the Upstream Update Script

Run the provided script to fetch and merge the latest version from PyPI:

```powershell
.\Update-Upstream.ps1 -PackageName <PackageName> -MainBranch master
```

The script will:

1. Detect the newest version available on PyPI  
2. Download the `.tar.gz` sdist  
3. Replace the `upstream` branch with the new code  
4. Merge upstream into `master`  
5. Run `uv sync` and `uv build`  
6. Tag the result (e.g., `v2.0.0-fork1`)

---

### Step 3 — Resolve Merge Conflicts (if any)

If Git reports conflicts:

```powershell
# Open files and resolve manually
git add .
git commit -m "Resolved merge conflicts from upstream vX.Y.Z"
```

Then re-run:

```powershell
uv sync
uv build
```

---

### Step 4 — Test the Updated Fork

Verify that your changes and build work correctly:

```powershell
uv run pytest
# or
uv run python -m <yourpackage>
```

---

### Step 5 — Push Updates to GitLab

When the update is tested and stable:

```powershell
git push origin master --tags
```

---

### Step 6 — Bump Fork Version (if Modified)

If you made code changes beyond upstream:

Edit `pyproject.toml`:

```toml
version = "X.Y.Z.post1"
```

Then commit:

```powershell
git commit -am "Bump fork version to X.Y.Z.post1"
git push origin master
```

---

## 🪶 Branch Structure

| Branch | Purpose |
|---------|----------|
| `master` | Your forked version with modifications |
| `upstream` | Raw upstream code imported from PyPI |

> Never modify the `upstream` branch directly.

---

## 🏷️ Version Tag Convention

| Type | Example | Meaning |
|------|----------|---------|
| Upstream import | `v2.0.0-upstream` | Raw code only |
| Merged fork | `v2.0.0-fork1` | Merged upstream + your fork |
| Incremental fixes | `v2.0.0-fork2` | Later updates on the same upstream |

---

## 🧼 Best Practices

- Keep `upstream` branch **clean and untouched** except for imports.  
- Always run `uv sync` after merging.  
- Push tags to GitLab after each upstream merge for traceability.  
- Keep `LICENSE` and attribution files intact after updates.  
- Maintain a simple `UPSTREAM.md` with the source version and checksum for compliance.

---

✅ **You’re all set.**  
Run the script whenever a new upstream release appears to stay up to date.
