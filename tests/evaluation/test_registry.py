"""Tests for suitability registry."""

import json

import numpy as np
import pandas as pd
import pytest

from aponyx.evaluation.suitability import (
    SuitabilityRegistry,
    evaluate_signal_suitability,
)


@pytest.fixture
def temp_registry_path(tmp_path):
    """Create temporary registry path."""
    return tmp_path / "test_registry.json"


@pytest.fixture
def registry(temp_registry_path):
    """Create test registry instance."""
    return SuitabilityRegistry(temp_registry_path)


@pytest.fixture
def sample_result():
    """Create sample evaluation result."""
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=600, freq="D")
    signal = pd.Series(np.random.randn(600), index=dates, name="test_signal")
    target = signal * 2.0 + np.random.randn(600) * 0.5

    return evaluate_signal_suitability(signal, target)


class TestSuitabilityRegistryInitialization:
    """Test registry initialization."""

    def test_creates_new_registry(self, temp_registry_path):
        """Test creating new registry file."""
        assert not temp_registry_path.exists()

        registry = SuitabilityRegistry(temp_registry_path)

        assert temp_registry_path.exists()
        assert registry._catalog == {}

    def test_loads_existing_registry(self, temp_registry_path):
        """Test loading existing registry."""
        # Create registry with data
        initial_data = {
            "eval_1": {
                "signal_id": "test",
                "product_id": "PROD",
                "evaluated_at": "2025-01-01T00:00:00",
                "decision": "PASS",
                "composite_score": 0.85,
                "evaluator_version": "0.1.0",
                "report_path": None,
                "metadata": {},
            }
        }
        with open(temp_registry_path, "w") as f:
            json.dump(initial_data, f)

        registry = SuitabilityRegistry(temp_registry_path)

        assert len(registry._catalog) == 1
        assert "eval_1" in registry._catalog


class TestRegisterEvaluation:
    """Test evaluation registration."""

    def test_register_basic(self, registry, sample_result):
        """Test basic registration."""
        eval_id = registry.register_evaluation(
            sample_result,
            "test_signal",
            "TEST_PRODUCT",
        )

        assert eval_id.startswith("test_signal_TEST_PRODUCT_")
        assert eval_id in registry._catalog

    def test_register_with_report_path(self, registry, sample_result):
        """Test registration with report path."""
        eval_id = registry.register_evaluation(
            sample_result,
            "test_signal",
            "TEST_PRODUCT",
            report_path="/path/to/report.md",
        )

        entry = registry.get_evaluation(eval_id)
        assert entry.report_path == "/path/to/report.md"

    def test_register_persists_to_disk(self, registry, sample_result, temp_registry_path):
        """Test that registration persists to disk."""
        eval_id = registry.register_evaluation(
            sample_result,
            "test_signal",
            "TEST_PRODUCT",
        )

        # Reload registry from disk
        new_registry = SuitabilityRegistry(temp_registry_path)
        assert eval_id in new_registry._catalog


class TestGetEvaluation:
    """Test evaluation retrieval."""

    def test_get_existing_evaluation(self, registry, sample_result):
        """Test retrieving existing evaluation."""
        eval_id = registry.register_evaluation(
            sample_result,
            "test_signal",
            "TEST_PRODUCT",
        )

        entry = registry.get_evaluation(eval_id)

        assert entry.signal_id == "test_signal"
        assert entry.product_id == "TEST_PRODUCT"
        assert entry.decision == sample_result.decision
        assert entry.composite_score == sample_result.composite_score

    def test_get_nonexistent_evaluation_raises(self, registry):
        """Test that getting non-existent evaluation raises KeyError."""
        with pytest.raises(KeyError, match="Evaluation not found"):
            registry.get_evaluation("nonexistent_id")

    def test_get_evaluation_info(self, registry, sample_result):
        """Test retrieving evaluation as dict."""
        eval_id = registry.register_evaluation(
            sample_result,
            "test_signal",
            "TEST_PRODUCT",
        )

        info = registry.get_evaluation_info(eval_id)

        assert isinstance(info, dict)
        assert info["signal_id"] == "test_signal"
        assert info["product_id"] == "TEST_PRODUCT"


class TestListEvaluations:
    """Test evaluation listing with filters."""

    def test_list_all_evaluations(self, registry, sample_result):
        """Test listing all evaluations."""
        id1 = registry.register_evaluation(sample_result, "signal_a", "PROD1")
        id2 = registry.register_evaluation(sample_result, "signal_b", "PROD2")

        evaluations = registry.list_evaluations()

        assert len(evaluations) == 2
        assert id1 in evaluations
        assert id2 in evaluations

    def test_filter_by_signal(self, registry, sample_result):
        """Test filtering by signal_id."""
        id1 = registry.register_evaluation(sample_result, "signal_a", "PROD1")
        id2 = registry.register_evaluation(sample_result, "signal_b", "PROD1")

        evaluations = registry.list_evaluations(signal_id="signal_a")

        assert len(evaluations) == 1
        assert id1 in evaluations
        assert id2 not in evaluations

    def test_filter_by_product(self, registry, sample_result):
        """Test filtering by product_id."""
        id1 = registry.register_evaluation(sample_result, "signal_a", "PROD1")
        id2 = registry.register_evaluation(sample_result, "signal_a", "PROD2")

        evaluations = registry.list_evaluations(product_id="PROD1")

        assert len(evaluations) == 1
        assert id1 in evaluations
        assert id2 not in evaluations

    def test_filter_by_decision(self, registry):
        """Test filtering by decision."""
        # Create PASS result (signal predicts future movements)
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=600, freq="D")
        signal_pass = pd.Series(np.random.randn(600), index=dates, name="pass_signal")
        target_changes_pass = signal_pass * 5.0 + np.random.randn(600) * 0.1
        target_pass = target_changes_pass.cumsum() + 100.0
        result_pass = evaluate_signal_suitability(signal_pass, target_pass)

        # Create non-PASS result (no correlation)
        signal_other = pd.Series(np.random.randn(600), index=dates, name="other_signal")
        # Independent random walk - no relationship to signal_other
        independent_changes = pd.Series(np.random.randn(600), index=dates)
        target_other = independent_changes.cumsum() + 100.0
        result_other = evaluate_signal_suitability(signal_other, target_other)

        id_pass = registry.register_evaluation(result_pass, "pass_signal", "PROD")
        id_other = registry.register_evaluation(result_other, "other_signal", "PROD")

        pass_evaluations = registry.list_evaluations(decision="PASS")
        other_decision = result_other.decision  # Could be HOLD or FAIL
        other_evaluations = registry.list_evaluations(decision=other_decision)

        assert id_pass in pass_evaluations
        assert id_other in other_evaluations
        assert id_other not in pass_evaluations


class TestRemoveEvaluation:
    """Test evaluation removal."""

    def test_remove_existing_evaluation(self, registry, sample_result):
        """Test removing existing evaluation."""
        eval_id = registry.register_evaluation(
            sample_result,
            "test_signal",
            "TEST_PRODUCT",
        )

        assert eval_id in registry._catalog

        registry.remove_evaluation(eval_id)

        assert eval_id not in registry._catalog

    def test_remove_nonexistent_raises(self, registry):
        """Test that removing non-existent evaluation raises KeyError."""
        with pytest.raises(KeyError, match="Evaluation not found"):
            registry.remove_evaluation("nonexistent_id")

    def test_remove_persists_to_disk(self, registry, sample_result, temp_registry_path):
        """Test that removal persists to disk."""
        eval_id = registry.register_evaluation(
            sample_result,
            "test_signal",
            "TEST_PRODUCT",
        )

        registry.remove_evaluation(eval_id)

        # Reload from disk
        new_registry = SuitabilityRegistry(temp_registry_path)
        assert eval_id not in new_registry._catalog
