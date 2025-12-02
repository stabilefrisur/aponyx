# Remaining Test Fixes Required

**Date**: December 2, 2025  
**Status**: 23 CLI tests remaining (down from 64 total failures)  
**Progress**: 657 tests passing ✅

---

## Summary of Changes Needed

All remaining failures are in CLI tests due to API changes in the `report` and `clean` commands.

### API Changes Overview

#### Report Command
**Old API** (tests expect this):
```bash
aponyx report --signal spread_momentum --strategy balanced [--format FORMAT] [--output PATH]
```

**New API** (actual implementation):
```bash
aponyx report --workflow LABEL_OR_INDEX [--format FORMAT] [--output PATH]
```

#### Clean Command
**Old API** (tests expect this):
```bash
aponyx clean --signal SIGNAL    # Clean specific signal
aponyx clean --all              # Clean all
```

**New API** (actual implementation):
```bash
aponyx clean --workflows [--signal SIGNAL] [--all]  # --workflows flag required
aponyx clean --indicators                            # Clean indicator cache
```

---

## Category 1: Report Command Tests (11 failures)

### File: `tests/cli/test_commands.py`

#### Test 1: `test_report_command_generates_output` (line ~797)

**Current code**:
```python
def test_report_command_generates_output(runner):
    """Test report command generates console output."""
    with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
        mock_generate.return_value = "Mock report content"

        result = runner.invoke(
            cli,
            [
                "report",
                "--signal",
                "spread_momentum",
                "--strategy",
                "balanced",
            ],
        )

        assert result.exit_code == 0
        assert "Mock report content" in result.output
```

**Required fix**:
```python
def test_report_command_generates_output(runner, tmp_path):
    """Test report command generates console output."""
    # Create mock workflow directory
    workflow_dir = tmp_path / "test_label_20241202_120000"
    workflow_dir.mkdir()
    (workflow_dir / "metadata.json").write_text(
        '{"label": "test_label", "signal": "spread_momentum", "strategy": "balanced"}'
    )
    reports_dir = workflow_dir / "reports"
    reports_dir.mkdir()
    (reports_dir / "suitability_evaluation_20241202.md").write_text("Test content")
    
    with patch("aponyx.cli.commands.report.DATA_WORKFLOWS_DIR", tmp_path):
        with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
            mock_generate.return_value = "Mock report content"

            result = runner.invoke(cli, ["report", "--workflow", "test_label"])

            assert result.exit_code == 0
            assert "Mock report content" in result.output
```

#### Test 2: `test_report_command_markdown_format` (line ~810)

**Pattern**: Same as Test 1 - replace `--signal X --strategy Y` with `--workflow test_label`

#### Test 3: `test_report_command_html_format` (line ~830)

**Pattern**: Same as Test 1

#### Test 4: `test_report_command_with_output_path` (line ~852)

**Pattern**: Same as Test 1

#### Test 5: `test_report_command_no_workflow_results` (line ~875)

**Current code**:
```python
def test_report_command_no_workflow_results(runner):
    """Test report command handles missing workflow results."""
    with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
        mock_generate.side_effect = FileNotFoundError("No workflow results found")

        result = runner.invoke(
            cli,
            [
                "report",
                "--signal",
                "nonexistent_signal",
                "--strategy",
                "balanced",
            ],
        )

        assert result.exit_code != 0
        assert "No workflow results" in result.output
```

**Required fix**:
```python
def test_report_command_no_workflow_results(runner, tmp_path):
    """Test report command handles missing workflow results."""
    # Empty workflows directory
    with patch("aponyx.cli.commands.report.DATA_WORKFLOWS_DIR", tmp_path):
        result = runner.invoke(cli, ["report", "--workflow", "nonexistent"])

        assert result.exit_code != 0
        # Updated error message from new implementation
        assert "No workflows found" in result.output or "not found" in result.output
```

#### Test 6: `test_report_command_generation_error` (line ~904)

**Required fix**: Change to use `--workflow` and mock `_resolve_workflow_dir` to raise exception

#### Test 7: `test_report_help_text` (line ~941)

**Current code**:
```python
def test_report_help_text(runner):
    """Test report command help includes required parameters."""
    result = runner.invoke(cli, ["report", "--help"])
    
    assert result.exit_code == 0
    assert "--signal" in result.output
    assert "--strategy" in result.output
    assert "--format" in result.output
```

**Required fix**:
```python
def test_report_help_text(runner):
    """Test report command help includes required parameters."""
    result = runner.invoke(cli, ["report", "--help"])
    
    assert result.exit_code == 0
    assert "--workflow" in result.output  # Changed from --signal and --strategy
    assert "--format" in result.output
```

### File: `tests/cli/test_error_handling.py`

#### Test 8: `test_report_command_file_not_found_detailed` (line ~281)

**Pattern**: Replace `--signal X --strategy Y` with `--workflow test_label`

#### Test 9: `test_report_command_unexpected_error` (line ~302)

**Pattern**: Same

#### Test 10: `test_report_command_output_with_absolute_path` (line ~420)

**Pattern**: Same

### File: `tests/cli/test_integration.py`

#### Test 11: `test_report_all_formats` (line ~215)

**Current code**:
```python
def test_report_all_formats(runner):
    """Test report generation in all formats."""
    formats = ["console", "markdown", "html"]

    for format_type in formats:
        with patch("aponyx.cli.commands.report.generate_report") as mock_generate:
            mock_generate.return_value = f"Mock {format_type} report"

            result = runner.invoke(
                cli,
                [
                    "report",
                    "--signal",
                    "spread_momentum",
                    "--strategy",
                    "balanced",
                    "--format",
                    format_type,
                ],
            )

            assert result.exit_code == 0
```

**Required fix**: Add workflow directory setup and use `--workflow test_label`

---

## Category 2: Clean Command Tests (6 failures)

### File: `tests/cli/test_commands.py`

#### Test 1: `test_clean_command_requires_signal_or_all` (line ~702)

**Current code**:
```python
def test_clean_command_requires_signal_or_all(runner):
    """Test clean command requires --signal or --all."""
    result = runner.invoke(cli, ["clean"])
    assert result.exit_code != 0
    assert "Must specify --signal or --all" in result.output
```

**Required fix**:
```python
def test_clean_command_requires_flag(runner):
    """Test clean command requires --workflows or --indicators flag."""
    result = runner.invoke(cli, ["clean"])
    assert result.exit_code != 0
    assert "Must specify --workflows, --indicators, or --all" in result.output
```

#### Test 2: `test_clean_command_specific_signal` (line ~750)

**Current code**:
```python
def test_clean_command_specific_signal(runner, tmp_path):
    """Test clean command for specific signal."""
    # Mock workflows directory
    with patch("aponyx.cli.commands.clean.DATA_WORKFLOWS_DIR", tmp_path):
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()

        # Create test workflow directory
        test_dir = workflows_dir / "spread_momentum_balanced_20241120_123456"
        test_dir.mkdir()

        result = runner.invoke(cli, ["clean", "--signal", "spread_momentum"])

        assert result.exit_code == 0
        assert not test_dir.exists()
```

**Required fix**:
```python
def test_clean_command_specific_signal(runner, tmp_path):
    """Test clean command for specific signal."""
    workflows_dir = tmp_path
    workflows_dir.mkdir(exist_ok=True)

    # Create test workflow directory with metadata
    test_dir = workflows_dir / "test_label_20241120_123456"
    test_dir.mkdir()
    (test_dir / "metadata.json").write_text(
        '{"label": "test_label", "signal": "spread_momentum", "strategy": "balanced", "timestamp": "2024-11-20T12:34:56"}'
    )

    with patch("aponyx.cli.commands.clean.DATA_WORKFLOWS_DIR", workflows_dir):
        result = runner.invoke(cli, ["clean", "--workflows", "--signal", "spread_momentum"])

        assert result.exit_code == 0
        assert not test_dir.exists()
```

#### Test 3: `test_clean_command_no_cached_results` (line ~772)

**Required fix**: Add `--workflows` flag and update expected message from "No cached results" to "No workflows found"

#### Test 4: `test_clean_command_signal_not_found` (line ~772)

**Required fix**: Add `--workflows` flag

### File: `tests/cli/test_error_handling.py`

#### Test 5: `test_clean_command_permission_error` (line ~238)

**Required fix**: Add `--workflows` flag to clean command invocation

#### Test 6: `test_clean_command_dry_run_with_multiple_items` (line ~257)

**Required fix**: Add `--workflows` flag

### File: `tests/cli/test_integration.py`

#### Test 7: `test_clean_with_different_scopes` (line ~240)

**Current code**:
```python
def test_clean_with_different_scopes(runner, tmp_path):
    """Test clean command with different scopes."""
    with patch("aponyx.cli.commands.clean.DATA_WORKFLOWS_DIR", tmp_path):
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir(parents=True)

        # Create files for multiple signals
        signals = ["spread_momentum", "cdx_vix_gap", "vix_spread"]
        for signal in signals:
            signal_dir = workflows_dir / f"{signal}_balanced_20251120_123456"
            signal_dir.mkdir()

        # Test cleaning specific signal
        result = runner.invoke(cli, ["clean", "--signal", "spread_momentum"])
        assert result.exit_code == 0
```

**Required fix**:
```python
def test_clean_with_different_scopes(runner, tmp_path):
    """Test clean command with different scopes."""
    workflows_dir = tmp_path
    workflows_dir.mkdir(exist_ok=True)

    # Create workflows with metadata for multiple signals
    signals = ["spread_momentum", "cdx_vix_gap", "vix_spread"]
    for signal in signals:
        signal_dir = workflows_dir / f"test_{signal}_20251120_123456"
        signal_dir.mkdir()
        (signal_dir / "metadata.json").write_text(
            f'{{"label": "test_{signal}", "signal": "{signal}", "strategy": "balanced", "timestamp": "2025-11-20T12:34:56"}}'
        )

    with patch("aponyx.cli.commands.clean.DATA_WORKFLOWS_DIR", workflows_dir):
        # Test cleaning specific signal - now requires --workflows flag
        result = runner.invoke(cli, ["clean", "--workflows", "--signal", "spread_momentum"])
        assert result.exit_code == 0
```

#### Test 8: `test_concurrent_command_safety` (line ~372)

**Required fix**: Add `--workflows` flag

---

## Category 3: Integration/Error Tests (6 failures)

### File: `tests/cli/test_integration.py`

#### Test 1: `test_full_workflow_integration` (line ~92)

**Issue**: Uses old report command API  
**Fix**: After workflow run succeeds, use `--workflow 0` or workflow label for report command

### File: `tests/cli/test_error_handling.py`

#### Test 2: `test_run_command_config_validation_error` (line ~?)

**Issue**: Likely expects different error message format  
**Fix**: Update error message assertion to match "Missing required field(s) in config file: X"

#### Test 3: `test_run_command_multiple_errors_in_workflow` (line ~?)

**Issue**: Error output format changed  
**Fix**: Update error message format expectations

#### Test 4: `test_run_command_config_with_relative_path` (line ~?)

**Issue**: Missing `label` field in test config  
**Status**: Should already be fixed by automated script, may need manual check

---

## Implementation Checklist

### Quick Wins (Mechanical Changes)
- [ ] Replace all `["report", "--signal", X, "--strategy", Y]` with `["report", "--workflow", "test_label"]`
- [ ] Add workflow directory setup with metadata.json for report tests
- [ ] Add `--workflows` flag to all clean command invocations
- [ ] Update clean test assertions from "No cached results" to "No workflows found"
- [ ] Update report help text test to check for `--workflow` instead of `--signal`/`--strategy`

### Tests Requiring Custom Logic
- [ ] `test_report_command_no_workflow_results` - needs empty directory setup
- [ ] `test_clean_command_requires_signal_or_all` - update error message assertion
- [ ] `test_clean_with_different_scopes` - needs metadata.json files created
- [ ] Integration tests - may need workflow label tracking

---

## Automated Fix Script Template

```python
# For report tests - add before test invocation:
workflow_dir = tmp_path / "test_label_20241202_120000"
workflow_dir.mkdir()
(workflow_dir / "metadata.json").write_text(
    '{"label": "test_label", "signal": "spread_momentum", "strategy": "balanced"}'
)
reports_dir = workflow_dir / "reports"
reports_dir.mkdir()
(reports_dir / "suitability_evaluation_20241202.md").write_text("Test content")

with patch("aponyx.cli.commands.report.DATA_WORKFLOWS_DIR", tmp_path):
    result = runner.invoke(cli, ["report", "--workflow", "test_label"])

# For clean tests - add metadata.json to workflow dirs:
(test_dir / "metadata.json").write_text(
    '{"label": "test_label", "signal": "spread_momentum", "strategy": "balanced", "timestamp": "2024-11-20T12:34:56"}'
)
result = runner.invoke(cli, ["clean", "--workflows", "--signal", "spread_momentum"])
```

---

## Estimated Effort

- **Report tests**: ~30 minutes (11 tests, mostly mechanical)
- **Clean tests**: ~20 minutes (6 tests, mostly mechanical)
- **Integration tests**: ~15 minutes (6 tests, minor adjustments)
- **Total**: ~65 minutes for experienced developer

---

## Notes

1. All workflow tests ✅ and reporting module tests ✅ are now passing
2. Main remaining work is CLI test adaptation to new command signatures
3. No actual functionality bugs - just test adaptation needed
4. Consider creating helper fixtures for workflow directory setup to reduce duplication
