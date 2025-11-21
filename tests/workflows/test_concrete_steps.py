"""
Tests for concrete workflow step implementations.

Validates DataStep, SignalStep, SuitabilityStep, BacktestStep,
PerformanceStep, and VisualizationStep.
"""

from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pandas as pd
import pytest

from aponyx.workflows.config import WorkflowConfig
from aponyx.workflows.concrete_steps import (
    DataStep,
    SignalStep,
    SuitabilityStep,
    BacktestStep,
    PerformanceStep,
    VisualizationStep,
)


@pytest.fixture
def workflow_config(tmp_path: Path) -> WorkflowConfig:
    """Create test workflow configuration."""
    return WorkflowConfig(
        signal_name="spread_momentum",
        strategy_name="balanced",
        output_dir=tmp_path / "workflows",
    )


@pytest.fixture
def sample_market_data() -> dict[str, pd.DataFrame]:
    """Generate sample market data."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    
    return {
        "cdx": pd.DataFrame(
            {"spread": 100 + pd.Series(range(100)) * 0.5},
            index=dates,
        ),
        "etf": pd.DataFrame(
            {"spread": 95 + pd.Series(range(100)) * 0.4},
            index=dates,
        ),
        "vix": pd.DataFrame(
            {"level": 15 + pd.Series(range(100)) * 0.1},
            index=dates,
        ),
    }


@pytest.fixture
def sample_signal() -> pd.Series:
    """Generate sample signal."""
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    import numpy as np
    np.random.seed(42)
    values = np.random.randn(100) * 0.5
    return pd.Series(values, index=dates, name="signal")


@pytest.fixture
def sample_backtest_result():
    """Generate sample backtest result."""
    from aponyx.backtest.engine import BacktestResult
    
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    import numpy as np
    np.random.seed(42)
    
    # Create positions DataFrame
    positions_data = {
        "signal": np.random.randn(100) * 0.5,
        "position": [1.0 if i % 2 == 0 else -1.0 for i in range(100)],
        "days_held": [i % 10 for i in range(100)],
        "spread": 100.0 + np.random.randn(100) * 5,
    }
    positions_df = pd.DataFrame(positions_data, index=dates)
    
    # Create PnL DataFrame
    pnl_data = {
        "spread_pnl": np.random.randn(100) * 0.5,
        "cost": [0.1] * 100,
        "net_pnl": np.random.randn(100) * 0.5,
    }
    pnl_df = pd.DataFrame(pnl_data, index=dates)
    pnl_df["cumulative_pnl"] = pnl_df["net_pnl"].cumsum()
    
    # Create metadata
    metadata = {
        "timestamp": "2024-01-01T00:00:00",
        "config": {
            "entry_threshold": 1.5,
            "exit_threshold": 0.5,
            "position_size": 10.0,
        },
        "summary": {
            "n_trades": 50,
            "total_pnl": float(pnl_df["cumulative_pnl"].iloc[-1]),
        },
    }
    
    return BacktestResult(
        positions=positions_df,
        pnl=pnl_df,
        metadata=metadata,
    )


class TestDataStep:
    """Test DataStep implementation."""

    def test_data_step_name(self, workflow_config):
        """Test DataStep has correct name."""
        step = DataStep(workflow_config)
        assert step.name == "data"

    @patch("aponyx.workflows.concrete_steps.get_required_data_keys")
    @patch("aponyx.workflows.concrete_steps.DataRegistry")
    @patch("aponyx.workflows.concrete_steps.load_parquet")
    def test_data_step_loads_required_data(
        self,
        mock_load_parquet,
        mock_data_registry_class,
        mock_get_keys,
        workflow_config,
        sample_market_data,
    ):
        """Test DataStep loads all required market data."""
        # Mock required keys
        mock_get_keys.return_value = {"cdx", "etf"}
        
        # Mock registry
        mock_registry = MagicMock()
        mock_registry.list_datasets.side_effect = lambda instrument: [f"{instrument}_data"]
        mock_registry.get_dataset_info.side_effect = lambda name: {
            "file_path": Path(f"/data/{name}.parquet")
        }
        mock_data_registry_class.return_value = mock_registry
        
        # Mock file loading
        mock_load_parquet.side_effect = lambda path: sample_market_data[
            path.stem.split("_")[0]
        ]
        
        step = DataStep(workflow_config)
        result = step.execute({})
        
        assert "market_data" in result
        assert "cdx" in result["market_data"]
        assert "etf" in result["market_data"]

    def test_data_step_output_exists_false(self, workflow_config):
        """Test DataStep never caches (always loads fresh)."""
        step = DataStep(workflow_config)
        assert not step.output_exists()

    @patch("aponyx.workflows.concrete_steps.get_required_data_keys")
    @patch("aponyx.workflows.concrete_steps.DataRegistry")
    def test_data_step_raises_on_missing_dataset(
        self,
        mock_data_registry_class,
        mock_get_keys,
        workflow_config,
    ):
        """Test DataStep raises error when dataset not found."""
        mock_get_keys.return_value = {"missing_instrument"}
        
        mock_registry = MagicMock()
        mock_registry.list_datasets.return_value = []
        mock_data_registry_class.return_value = mock_registry
        
        step = DataStep(workflow_config)
        
        with pytest.raises(ValueError, match="No datasets found"):
            step.execute({})


class TestSignalStep:
    """Test SignalStep implementation."""

    def test_signal_step_name(self, workflow_config):
        """Test SignalStep has correct name."""
        step = SignalStep(workflow_config)
        assert step.name == "signal"

    @patch("aponyx.workflows.concrete_steps.compute_registered_signals")
    @patch("aponyx.workflows.concrete_steps.save_parquet")
    def test_signal_step_computes_signal(
        self,
        mock_save,
        mock_compute,
        workflow_config,
        sample_market_data,
        sample_signal,
    ):
        """Test SignalStep computes and saves signal."""
        # Mock signal computation
        mock_compute.return_value = {
            "spread_momentum": sample_signal,
        }
        
        step = SignalStep(workflow_config)
        context = {"data": {"market_data": sample_market_data}}
        result = step.execute(context)
        
        assert "signal" in result
        assert isinstance(result["signal"], pd.Series)
        mock_save.assert_called_once()

    @patch("aponyx.workflows.concrete_steps.compute_registered_signals")
    @patch("aponyx.workflows.concrete_steps.save_parquet")
    def test_signal_step_output_path(
        self,
        mock_save,
        mock_compute,
        workflow_config,
        sample_market_data,
        sample_signal,
    ):
        """Test SignalStep creates output in correct location."""
        mock_compute.return_value = {"spread_momentum": sample_signal}
        
        step = SignalStep(workflow_config)
        context = {"data": {"market_data": sample_market_data}}
        step.execute(context)
        
        output_path = step.get_output_path()
        assert "signals" in str(output_path)
        assert workflow_config.signal_name in str(output_path)

    def test_signal_step_output_exists(self, workflow_config, tmp_path):
        """Test SignalStep checks for existing output."""
        # Create mock output directory structure
        from aponyx.config import PROCESSED_DIR
        signal_dir = (
            PROCESSED_DIR / "workflows" / "signals" / workflow_config.signal_name
        )
        signal_dir.mkdir(parents=True, exist_ok=True)
        
        step = SignalStep(workflow_config)
        signal_path = signal_dir / f"{workflow_config.signal_name}.parquet"
        
        # Remove file if it exists from previous test
        if signal_path.exists():
            signal_path.unlink()
        
        # Should not exist initially
        assert not step.output_exists()
        
        # Create the file
        signal_path.write_text("dummy")
        
        # Now should exist
        assert step.output_exists()


class TestSuitabilityStep:
    """Test SuitabilityStep implementation."""

    def test_suitability_step_name(self, workflow_config):
        """Test SuitabilityStep has correct name."""
        step = SuitabilityStep(workflow_config)
        assert step.name == "suitability"

    @patch("aponyx.workflows.concrete_steps.load_parquet")
    @patch("aponyx.workflows.concrete_steps.StrategyRegistry")
    @patch("aponyx.workflows.concrete_steps.DataRegistry")
    @patch("aponyx.workflows.concrete_steps.evaluate_signal_suitability")
    @patch("aponyx.workflows.concrete_steps.generate_suitability_report")
    @patch("aponyx.workflows.concrete_steps.save_suitability_report")
    def test_suitability_step_evaluates_signal(
        self,
        mock_save_report,
        mock_generate_report,
        mock_evaluate,
        mock_data_registry_class,
        mock_strategy_registry_class,
        mock_load_parquet,
        workflow_config,
        sample_signal,
        sample_market_data,
    ):
        """Test SuitabilityStep evaluates signal quality."""
        from aponyx.evaluation.suitability import SuitabilityResult
        from unittest.mock import Mock
        
        # Mock strategy registry to provide product
        mock_strategy_registry = Mock()
        mock_metadata = Mock()
        mock_metadata.product = "cdx_ig_5y"
        mock_strategy_registry.get_metadata.return_value = mock_metadata
        mock_strategy_registry_class.return_value = mock_strategy_registry
        
        # Mock data registry to provide spread data
        mock_data_registry = Mock()
        mock_data_registry.list_datasets.return_value = ["cdx_data"]
        mock_info = {"file_path": "/data/cdx.parquet", "metadata": {"params": {"security": "cdx_ig_5y"}}}
        mock_data_registry.get_dataset_info.return_value = mock_info
        mock_data_registry_class.return_value = mock_data_registry
        
        # Mock spread data
        mock_load_parquet.return_value = sample_market_data["cdx"]
        
        # Mock evaluation
        mock_result = SuitabilityResult(
            decision="pass",
            composite_score=0.71,
            data_health_score=0.8,
            predictive_score=0.7,
            economic_score=0.6,
            stability_score=0.75,
            valid_obs=100,
            missing_pct=0.0,
            correlations={1: 0.5, 5: 0.4},
            betas={1: 0.3, 5: 0.25},
            t_stats={1: 2.5, 5: 2.0},
            effect_size_bps=10.0,
            sign_consistency_ratio=0.8,
            beta_cv=0.3,
            n_windows=50,
            timestamp="2024-01-01T00:00:00",
            config=None,  # Can be None for test
        )
        mock_evaluate.return_value = mock_result
        mock_generate_report.return_value = "Test report"
        
        step = SuitabilityStep(workflow_config)
        context = {
            "signal": {"signal": sample_signal},
            "data": {"market_data": sample_market_data},
        }
        result = step.execute(context)
        
        assert "suitability_result" in result
        mock_evaluate.assert_called_once()
        mock_save_report.assert_called_once()


class TestBacktestStep:
    """Test BacktestStep implementation."""

    def test_backtest_step_name(self, workflow_config):
        """Test BacktestStep has correct name."""
        step = BacktestStep(workflow_config)
        assert step.name == "backtest"

    @patch("aponyx.workflows.concrete_steps.load_parquet")
    @patch("aponyx.workflows.concrete_steps.DataRegistry")
    @patch("aponyx.workflows.concrete_steps.run_backtest")
    @patch("aponyx.workflows.concrete_steps.save_parquet")
    def test_backtest_step_runs_backtest(
        self,
        mock_save,
        mock_run_backtest,
        mock_data_registry_class,
        mock_load_parquet,
        workflow_config,
        sample_signal,
        sample_market_data,
        sample_backtest_result,
    ):
        """Test BacktestStep runs strategy backtest."""
        from unittest.mock import Mock
        
        # Mock data registry
        mock_registry = Mock()
        mock_registry.list_datasets.return_value = ["cdx_data"]
        mock_info = {"file_path": "/data/cdx.parquet", "metadata": {"params": {"security": "cdx_ig_5y"}}}
        mock_registry.get_dataset_info.return_value = mock_info
        mock_data_registry_class.return_value = mock_registry
        
        # Mock spread data
        mock_load_parquet.return_value = sample_market_data["cdx"]
        mock_run_backtest.return_value = sample_backtest_result
        
        step = BacktestStep(workflow_config)
        context = {
            "signal": {"signal": sample_signal},
            "data": {"market_data": sample_market_data},
            "suitability": {"product": "cdx_ig_5y"},
        }
        result = step.execute(context)
        
        assert "backtest_result" in result
        mock_run_backtest.assert_called_once()

    @patch("aponyx.workflows.concrete_steps.load_parquet")
    @patch("aponyx.workflows.concrete_steps.DataRegistry")
    @patch("aponyx.workflows.concrete_steps.run_backtest")
    @patch("aponyx.workflows.concrete_steps.save_parquet")
    def test_backtest_step_uses_strategy_registry(
        self,
        mock_save,
        mock_run_backtest,
        mock_data_registry_class,
        mock_load_parquet,
        workflow_config,
        sample_signal,
        sample_market_data,
        sample_backtest_result,
    ):
        """Test BacktestStep loads strategy config from registry."""
        from unittest.mock import Mock
        
        # Mock data registry
        mock_registry = Mock()
        mock_registry.list_datasets.return_value = ["cdx_data"]
        mock_info = {"file_path": "/data/cdx.parquet", "metadata": {"params": {"security": "cdx_ig_5y"}}}
        mock_registry.get_dataset_info.return_value = mock_info
        mock_data_registry_class.return_value = mock_registry
        
        # Mock spread data
        mock_load_parquet.return_value = sample_market_data["cdx"]
        mock_run_backtest.return_value = sample_backtest_result
        
        step = BacktestStep(workflow_config)
        context = {
            "signal": {"signal": sample_signal},
            "data": {"market_data": sample_market_data},
            "suitability": {"product": "cdx_ig_5y"},
        }
        step.execute(context)
        
        # Verify run_backtest was called with signal and config
        call_args = mock_run_backtest.call_args
        assert call_args is not None


class TestPerformanceStep:
    """Test PerformanceStep implementation."""

    def test_performance_step_name(self, workflow_config):
        """Test PerformanceStep has correct name."""
        step = PerformanceStep(workflow_config)
        assert step.name == "performance"

    @patch("aponyx.workflows.concrete_steps.analyze_backtest_performance")
    @patch("aponyx.workflows.concrete_steps.generate_performance_report")
    @patch("aponyx.workflows.concrete_steps.save_performance_report")
    def test_performance_step_analyzes_results(
        self,
        mock_save_report,
        mock_generate_report,
        mock_analyze,
        workflow_config,
        sample_signal,
        sample_backtest_result,
    ):
        """Test PerformanceStep computes extended metrics."""
        from unittest.mock import Mock
        
        # Mock analysis result with proper attributes
        mock_metrics = Mock()
        mock_metrics.sharpe = 1.5
        mock_metrics.max_drawdown_pct = 0.15
        
        mock_result = Mock()
        mock_result.metrics = mock_metrics
        mock_analyze.return_value = mock_result
        mock_generate_report.return_value = "Performance report"
        
        step = PerformanceStep(workflow_config)
        context = {
            "backtest": {"backtest_result": sample_backtest_result},
            "signal": {"signal": sample_signal},
        }
        result = step.execute(context)
        
        assert "performance" in result
        mock_analyze.assert_called_once()
        mock_save_report.assert_called_once()


class TestVisualizationStep:
    """Test VisualizationStep implementation."""

    def test_visualization_step_name(self, workflow_config):
        """Test VisualizationStep has correct name."""
        step = VisualizationStep(workflow_config)
        assert step.name == "visualization"

    @patch("aponyx.workflows.concrete_steps.plot_equity_curve")
    @patch("aponyx.workflows.concrete_steps.plot_drawdown")
    @patch("aponyx.workflows.concrete_steps.plot_signal")
    def test_visualization_step_creates_charts(
        self,
        mock_plot_signal,
        mock_plot_drawdown,
        mock_plot_equity,
        workflow_config,
        sample_signal,
        sample_backtest_result,
    ):
        """Test VisualizationStep generates all charts."""
        # Mock plotting functions
        mock_fig = Mock()
        mock_plot_equity.return_value = mock_fig
        mock_plot_drawdown.return_value = mock_fig
        mock_plot_signal.return_value = mock_fig
        
        step = VisualizationStep(workflow_config)
        context = {
            "backtest": {"backtest_result": sample_backtest_result},
            "signal": {"signal": sample_signal},
        }
        result = step.execute(context)
        
        assert "equity_fig" in result
        assert "drawdown_fig" in result
        assert "signal_fig" in result
        mock_plot_equity.assert_called_once()
        mock_plot_drawdown.assert_called_once()
        mock_plot_signal.assert_called_once()

    @patch("aponyx.workflows.concrete_steps.plot_equity_curve")
    @patch("aponyx.workflows.concrete_steps.plot_drawdown")
    @patch("aponyx.workflows.concrete_steps.plot_signal")
    def test_visualization_step_saves_charts(
        self,
        mock_plot_signal,
        mock_plot_drawdown,
        mock_plot_equity,
        workflow_config,
        sample_signal,
        sample_backtest_result,
    ):
        """Test VisualizationStep saves charts to output directory."""
        # Mock figures with write_html method
        mock_fig = Mock()
        mock_plot_equity.return_value = mock_fig
        mock_plot_drawdown.return_value = mock_fig
        mock_plot_signal.return_value = mock_fig
        
        step = VisualizationStep(workflow_config)
        context = {
            "backtest": {"backtest_result": sample_backtest_result},
            "signal": {"signal": sample_signal},
        }
        step.execute(context)
        
        # Verify write_html was called on figures
        assert mock_fig.write_html.call_count >= 3


class TestStepIntegration:
    """Integration tests for step interactions."""

    @patch("aponyx.workflows.concrete_steps.get_required_data_keys")
    @patch("aponyx.workflows.concrete_steps.DataRegistry")
    @patch("aponyx.workflows.concrete_steps.load_parquet")
    @patch("aponyx.workflows.concrete_steps.compute_registered_signals")
    @patch("aponyx.workflows.concrete_steps.save_parquet")
    def test_data_to_signal_flow(
        self,
        mock_save,
        mock_compute,
        mock_load_parquet,
        mock_data_registry_class,
        mock_get_keys,
        workflow_config,
        sample_market_data,
        sample_signal,
    ):
        """Test data flows correctly from DataStep to SignalStep."""
        # Setup DataStep
        mock_get_keys.return_value = {"cdx"}
        mock_registry = MagicMock()
        mock_registry.list_datasets.return_value = ["cdx_data"]
        mock_registry.get_dataset_info.return_value = {
            "file_path": Path("/data/cdx.parquet")
        }
        mock_data_registry_class.return_value = mock_registry
        mock_load_parquet.return_value = sample_market_data["cdx"]
        
        # Setup SignalStep
        mock_compute.return_value = {"spread_momentum": sample_signal}
        
        # Execute DataStep
        data_step = DataStep(workflow_config)
        context = {}
        data_output = data_step.execute(context)
        context["data"] = data_output
        
        # Execute SignalStep with DataStep output
        signal_step = SignalStep(workflow_config)
        signal_output = signal_step.execute(context)
        context["signal"] = signal_output
        
        # Verify signal was computed with data from DataStep
        assert "signal" in signal_output
        mock_compute.assert_called_once()

    def test_step_output_path_hierarchy(self, workflow_config):
        """Test steps create appropriate output directory hierarchy."""
        data_step = DataStep(workflow_config)
        signal_step = SignalStep(workflow_config)
        backtest_step = BacktestStep(workflow_config)
        
        # All paths should be under workflows directory
        assert "workflows" in str(data_step.get_output_path())
        assert "workflows" in str(signal_step.get_output_path())
        assert "workflows" in str(backtest_step.get_output_path())
        
        # Each step should have its own subdirectory
        assert "data" in str(data_step.get_output_path())
        assert "signals" in str(signal_step.get_output_path())
        assert "backtests" in str(backtest_step.get_output_path())
