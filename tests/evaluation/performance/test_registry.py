"""Tests for performance registry."""

from pathlib import Path

import pytest

from aponyx.evaluation.performance import (
    PerformanceConfig,
    PerformanceEntry,
    PerformanceRegistry,
    PerformanceResult,
)


@pytest.fixture
def sample_performance_result() -> PerformanceResult:
    """Generate sample performance result for testing."""
    return PerformanceResult(
        metrics={
            "rolling_sharpe_mean": 1.5,
            "rolling_sharpe_std": 0.3,
            "max_dd_recovery_days": 45.0,
            "avg_recovery_days": 20.0,
            "n_drawdowns": 5,
            "tail_ratio": 1.2,
            "profit_factor": 1.8,
            "consistency_score": 0.65,
        },
        subperiod_analysis={
            "subperiod_returns": [1000, 1500, -500, 2000],
            "subperiod_sharpes": [1.2, 1.5, -0.5, 2.0],
            "positive_periods": 3,
            "consistency_rate": 0.75,
        },
        attribution={
            "direction": {"long_pnl": 3000, "short_pnl": 1000},
            "signal_strength": {"q1_pnl": 500, "q2_pnl": 1500, "q3_pnl": 2000},
            "win_loss": {"gross_wins": 5000, "gross_losses": -1000},
        },
        stability_score=0.75,
        summary="Test summary",
        timestamp="2024-01-01T12:00:00",
        config=PerformanceConfig(),
        metadata={"evaluator_version": "0.1.0", "sharpe_ratio": 1.5, "max_drawdown": -1000},
    )


class TestPerformanceRegistry:
    """Test PerformanceRegistry CRUD operations."""

    def test_registry_creation(self, tmp_path: Path) -> None:
        """Test creating new registry."""
        registry_path = tmp_path / "performance_registry.json"
        registry = PerformanceRegistry(registry_path)

        assert registry.registry_path == registry_path
        assert registry_path.exists()

    def test_register_evaluation(
        self, tmp_path: Path, sample_performance_result: PerformanceResult
    ) -> None:
        """Test registering evaluation."""
        registry_path = tmp_path / "performance_registry.json"
        registry = PerformanceRegistry(registry_path)

        eval_id = registry.register_evaluation(
            sample_performance_result, "test_signal", "test_strategy"
        )

        assert "test_signal" in eval_id
        assert "test_strategy" in eval_id

    def test_get_evaluation(
        self, tmp_path: Path, sample_performance_result: PerformanceResult
    ) -> None:
        """Test retrieving evaluation."""
        registry_path = tmp_path / "performance_registry.json"
        registry = PerformanceRegistry(registry_path)

        eval_id = registry.register_evaluation(
            sample_performance_result, "test_signal", "test_strategy"
        )

        entry = registry.get_evaluation(eval_id)

        assert isinstance(entry, PerformanceEntry)
        assert entry.signal_id == "test_signal"
        assert entry.strategy_id == "test_strategy"
        assert entry.stability_score == 0.75

    def test_get_evaluation_not_found(self, tmp_path: Path) -> None:
        """Test retrieving non-existent evaluation raises."""
        registry_path = tmp_path / "performance_registry.json"
        registry = PerformanceRegistry(registry_path)

        with pytest.raises(KeyError, match="Performance evaluation not found"):
            registry.get_evaluation("nonexistent_id")

    def test_list_evaluations(
        self, tmp_path: Path, sample_performance_result: PerformanceResult
    ) -> None:
        """Test listing evaluations."""
        registry_path = tmp_path / "performance_registry.json"
        registry = PerformanceRegistry(registry_path)

        eval_id1 = registry.register_evaluation(
            sample_performance_result, "signal1", "strategy1"
        )
        registry.register_evaluation(
            sample_performance_result, "signal2", "strategy1"
        )

        all_evals = registry.list_evaluations()
        assert len(all_evals) == 2

        signal1_evals = registry.list_evaluations(signal_id="signal1")
        assert len(signal1_evals) == 1
        assert eval_id1 in signal1_evals

        strategy1_evals = registry.list_evaluations(strategy_id="strategy1")
        assert len(strategy1_evals) == 2

    def test_remove_evaluation(
        self, tmp_path: Path, sample_performance_result: PerformanceResult
    ) -> None:
        """Test removing evaluation."""
        registry_path = tmp_path / "performance_registry.json"
        registry = PerformanceRegistry(registry_path)

        eval_id = registry.register_evaluation(
            sample_performance_result, "test_signal", "test_strategy"
        )

        assert len(registry.list_evaluations()) == 1

        registry.remove_evaluation(eval_id)

        assert len(registry.list_evaluations()) == 0

    def test_remove_evaluation_not_found(self, tmp_path: Path) -> None:
        """Test removing non-existent evaluation raises."""
        registry_path = tmp_path / "performance_registry.json"
        registry = PerformanceRegistry(registry_path)

        with pytest.raises(KeyError, match="Performance evaluation not found"):
            registry.remove_evaluation("nonexistent_id")

    def test_registry_persistence(
        self, tmp_path: Path, sample_performance_result: PerformanceResult
    ) -> None:
        """Test that registry persists to disk."""
        registry_path = tmp_path / "performance_registry.json"
        registry1 = PerformanceRegistry(registry_path)

        eval_id = registry1.register_evaluation(
            sample_performance_result, "test_signal", "test_strategy"
        )

        # Create new registry instance from same path
        registry2 = PerformanceRegistry(registry_path)

        # Should load existing data
        entry = registry2.get_evaluation(eval_id)
        assert entry.signal_id == "test_signal"
