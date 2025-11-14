# Python project — concise uv + GitHub workflow

This is a compact, modern reference for creating, developing and publishing a Python project using uv, git and GitHub. Assumes a bash shell and that you use `uv` for venv, dependency and project management.

Core ideas (short):
- Use a `pyproject.toml`-based layout with source in `src/`.
- Keep `.venv/` out of source control. Use `uv venv` to create/manage the venv.
- Treat `pyproject.toml` as the single source of truth; run `uv sync` after manual edits.
- Default branch name: `master`.

Prerequisites:
- uv (CLI), git, a GitHub account.

## Quick start


Initialize a new project and create a venv (example using Python 3.12):

```bash
uv init my_project --lib --python 3.12
cd my_project
# create the venv (uses .python-version if present)
uv venv
```

Activate the venv (bash):

```bash
source .venv/bin/activate
```

Hello from my_project:
```bash
uv run python -c "import my_project; print(my_project.hello())"
```

Make a main file:
```bash
touch src/my_project/main.py
```

Insert code into main.py:
```python
def main():
    print("Hello from my_project!")


if __name__ == "__main__":
    main()
```


Run the project or a script with uv (no install required):

```bash
uv run src/my_project/main.py    # run a script directly
uv run my_project               # run an installed entry point (see below)
```

## Source layout and build system

Prefer the src layout:

```
my_project/
├─ pyproject.toml
└─ src/
	└─ my_project/
		└─ main.py
```


Use uv's native build backend (`uv_build`) for a fast, zero-config build by default. Add this to `pyproject.toml`:

```toml
[build-system]
requires = ["uv_build>=0.9.5,<0.10.0"]
build-backend = "uv_build"

[tool.uv.build-backend]
# optional overrides; defaults expect a single module under src/<name>
module-root = "src"
```

After editing `pyproject.toml` manually run:

```bash
uv sync   # ensures venv metadata and pyproject stay in sync
```

## Dependencies (best practices)

- Prefer pinned versions for reproducibility: `uv add requests==2.31.0`.
- Add dev dependencies with `--dev` and commit them to `pyproject.toml`.

Examples:

```bash
uv add pandas==2.2.0 scikit-learn plotly
uv add --dev pytest black ruff
uv pip list    # list packages in the current uv-managed venv
```

If you need to remove a package:

```bash
uv remove matplotlib
```

## Editable install & entry points

Register a CLI entry point in `pyproject.toml`:

```toml
[project.scripts]
my_project = "my_project.main:main"
```

Install in editable mode for local development:

```bash
uv pip install -e .
uv run my_project    # now available via uv run my_project
```

## Git & GitHub (concise)


Initialize repo, commit, and push to GitHub (use `master` as default):

```bash
git init
git branch -M master
git add .
git commit -m "chore: initial commit"
# create repo on GitHub (web UI or use gh cli), then add remote
git remote add origin https://github.com/<your-user>/my_project.git
git push -u origin master
```

.gitignore essentials (example):

```
.venv/
dist/
build/
*.pyc
__pycache__/
.env
```

Stop tracking a file already committed:

```bash
git rm --cached path/to/file
git commit -m "chore: remove sensitive file from VCS"
```

Branch workflow (feature branch → PR → merge to master):

```bash
git checkout -b feat/awesome
# work, stage, commit
git push -u origin feat/awesome
# open PR on GitHub and merge to master
git checkout master
git pull origin master
git branch -d feat/awesome
git push origin --delete feat/awesome
```

## Testing with pytest

Create `tests/` and configure pytest via `pyproject.toml` if desired:

```toml
[tool.pytest.ini_options]
pythonpath = "src"
testpaths = ["tests"]
```

Run tests:

```bash
uv run -m pytest
# or, if pytest is in the venv
pytest
```

## Build & publish

Build sdist and wheel:

```bash
uv build
# outputs will be in dist/
```

Synchronize and publish (follow prompts for credentials):

```bash
uv sync
uv publish
```

Notes: always commit and push tags/changes before publishing. Prefer using test.pypi.org for initial tests.

Tip: when running builds in CI or when you want to ensure the build works without any custom `tool.uv.sources` settings, run:

```bash
uv build --no-sources
```
This forces the build to use only `build-system.requires` and matches other frontends' behaviour.

## Short tips & best practices

- Keep `pyproject.toml` authoritative. Run `uv sync` after manual edits.
- Pin runtime deps for libraries; use ranges or caret for apps where appropriate.
- Keep secrets out of the repo. Use environment variables or a secrets manager.
- Add CI (GitHub Actions) to run lint, tests and build on PRs.
- Prefer `master` as the default branch name.

## Quick checklist

- [ ] uv init + uv venv
- [ ] add dependencies and run `uv sync`
- [ ] register entry points and `uv pip install -e .`
- [ ] add tests and CI
- [ ] build (`uv build`) and publish (`uv publish`)

---

If you want, I can also create a minimal `pyproject.toml` template, a `.gitignore`, and a GitHub Actions CI file for lint/test/build. Which would you like next?