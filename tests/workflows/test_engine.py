"""
Tests for workflow orchestration engine.

Verifies workflow execution, caching, error handling, and step coordination.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import Any

from aponyx.workflows import WorkflowEngine, WorkflowConfig
from aponyx.workflows.steps import BaseWorkflowStep


class MockStep(BaseWorkflowStep):
    """Mock workflow step for testing."""
    
    def __init__(self, config: WorkflowConfig, step_name: str, should_fail: bool = False):
        super().__init__(config)
        self._step_name = step_name
        self._should_fail = should_fail
        self._execute_called = False
        
    @property
    def name(self) -> str:
        return self._step_name
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        self._execute_called = True
        if self._should_fail:
            raise RuntimeError(f"Mock failure in {self.name}")
        return {f"{self.name}_result": f"data from {self.name}"}
    
    def output_exists(self) -> bool:
        return False
    
    def get_output_path(self) -> Path:
        return Path("/mock/output") / self.name


def test_workflow_config_validation():
    """Test WorkflowConfig validates step names."""
    # Valid config
    config = WorkflowConfig(
        signal_name="spread_momentum",
        strategy_name="balanced",
        steps=["data", "signal"],
    )
    assert config.steps == ["data", "signal"]
    
    # Invalid step name should raise
    with pytest.raises(ValueError, match="Invalid steps"):
        WorkflowConfig(
            signal_name="spread_momentum",
            strategy_name="balanced",
            steps=["data", "invalid_step"],
        )


def test_workflow_engine_execution_order():
    """Test steps execute in correct order."""
    config = WorkflowConfig(
        signal_name="test_signal",
        strategy_name="test_strategy",
    )
    
    execution_order = []
    
    class OrderedMockStep(BaseWorkflowStep):
        def __init__(self, config: WorkflowConfig, step_name: str):
            super().__init__(config)
            self._step_name = step_name
            
        @property
        def name(self) -> str:
            return self._step_name
        
        def execute(self, context: dict[str, Any]) -> dict[str, Any]:
            execution_order.append(self.name)
            return {"result": self.name}
        
        def output_exists(self) -> bool:
            return False
        
        def get_output_path(self) -> Path:
            return Path("/mock")
    
    # Mock registry to return ordered steps
    with patch("aponyx.workflows.engine.StepRegistry") as mock_registry_class:
        mock_registry = MagicMock()
        mock_registry.get_all_steps.return_value = [
            OrderedMockStep(config, "data"),
            OrderedMockStep(config, "signal"),
            OrderedMockStep(config, "backtest"),
        ]
        mock_registry_class.return_value = mock_registry
        
        engine = WorkflowEngine(config)
        result = engine.execute()
        
        assert execution_order == ["data", "signal", "backtest"]
        assert result["steps_completed"] == 3
        assert result["steps_skipped"] == 0
        assert len(result["errors"]) == 0


def test_workflow_engine_caching():
    """Test workflow skips steps with existing output."""
    config = WorkflowConfig(
        signal_name="test_signal",
        strategy_name="test_strategy",
    )
    
    class CachedMockStep(BaseWorkflowStep):
        def __init__(self, config: WorkflowConfig, step_name: str, is_cached: bool):
            super().__init__(config)
            self._step_name = step_name
            self._is_cached = is_cached
            self._execute_called = False
            
        @property
        def name(self) -> str:
            return self._step_name
        
        def execute(self, context: dict[str, Any]) -> dict[str, Any]:
            self._execute_called = True
            return {"result": self.name}
        
        def output_exists(self) -> bool:
            return self._is_cached
        
        def load_cached_output(self) -> dict[str, Any]:
            return {"result": f"{self.name}_cached"}
        
        def get_output_path(self) -> Path:
            return Path("/mock")
    
    with patch("aponyx.workflows.engine.StepRegistry") as mock_registry_class:
        step1 = CachedMockStep(config, "data", is_cached=True)
        step2 = CachedMockStep(config, "signal", is_cached=False)
        step3 = CachedMockStep(config, "backtest", is_cached=True)
        
        mock_registry = MagicMock()
        mock_registry.get_all_steps.return_value = [step1, step2, step3]
        mock_registry_class.return_value = mock_registry
        
        engine = WorkflowEngine(config)
        result = engine.execute()
        
        # Only step2 should execute
        assert not step1._execute_called
        assert step2._execute_called
        assert not step3._execute_called
        
        assert result["steps_completed"] == 1
        assert result["steps_skipped"] == 2


def test_workflow_engine_force_rerun():
    """Test force_rerun overrides caching."""
    config = WorkflowConfig(
        signal_name="test_signal",
        strategy_name="test_strategy",
        force_rerun=True,
    )
    
    class CachedMockStep(BaseWorkflowStep):
        def __init__(self, config: WorkflowConfig, step_name: str):
            super().__init__(config)
            self._step_name = step_name
            self._execute_called = False
            
        @property
        def name(self) -> str:
            return self._step_name
        
        def execute(self, context: dict[str, Any]) -> dict[str, Any]:
            self._execute_called = True
            return {"result": self.name}
        
        def output_exists(self) -> bool:
            return True  # Cached
        
        def get_output_path(self) -> Path:
            return Path("/mock")
    
    with patch("aponyx.workflows.engine.StepRegistry") as mock_registry_class:
        step1 = CachedMockStep(config, "data")
        step2 = CachedMockStep(config, "signal")
        
        mock_registry = MagicMock()
        mock_registry.get_all_steps.return_value = [step1, step2]
        mock_registry_class.return_value = mock_registry
        
        engine = WorkflowEngine(config)
        result = engine.execute()
        
        # All steps should execute despite caching
        assert step1._execute_called
        assert step2._execute_called
        
        assert result["steps_completed"] == 2
        assert result["steps_skipped"] == 0


def test_workflow_engine_error_handling():
    """Test workflow stops on first error and preserves partial results."""
    config = WorkflowConfig(
        signal_name="test_signal",
        strategy_name="test_strategy",
    )
    
    with patch("aponyx.workflows.engine.StepRegistry") as mock_registry_class:
        step1 = MockStep(config, "data", should_fail=False)
        step2 = MockStep(config, "signal", should_fail=True)
        step3 = MockStep(config, "backtest", should_fail=False)
        
        mock_registry = MagicMock()
        mock_registry.get_all_steps.return_value = [step1, step2, step3]
        mock_registry_class.return_value = mock_registry
        
        engine = WorkflowEngine(config)
        result = engine.execute()
        
        # Step 1 completes, step 2 fails, step 3 skipped
        assert step1._execute_called
        assert step2._execute_called
        assert not step3._execute_called
        
        assert result["steps_completed"] == 1
        assert result["steps_skipped"] == 0
        assert len(result["errors"]) == 1
        assert result["errors"][0]["step"] == "signal"
        assert "Mock failure" in result["errors"][0]["error"]


def test_workflow_engine_context_passing():
    """Test steps receive outputs from previous steps."""
    config = WorkflowConfig(
        signal_name="test_signal",
        strategy_name="test_strategy",
    )
    
    received_contexts = []
    
    class ContextTrackingStep(BaseWorkflowStep):
        def __init__(self, config: WorkflowConfig, step_name: str):
            super().__init__(config)
            self._step_name = step_name
            
        @property
        def name(self) -> str:
            return self._step_name
        
        def execute(self, context: dict[str, Any]) -> dict[str, Any]:
            received_contexts.append((self.name, dict(context)))
            return {f"{self.name}_output": f"data_{self.name}"}
        
        def output_exists(self) -> bool:
            return False
        
        def get_output_path(self) -> Path:
            return Path("/mock")
    
    with patch("aponyx.workflows.engine.StepRegistry") as mock_registry_class:
        mock_registry = MagicMock()
        mock_registry.get_all_steps.return_value = [
            ContextTrackingStep(config, "data"),
            ContextTrackingStep(config, "signal"),
            ContextTrackingStep(config, "backtest"),
        ]
        mock_registry_class.return_value = mock_registry
        
        engine = WorkflowEngine(config)
        engine.execute()
        
        # Verify context accumulates
        assert received_contexts[0] == ("data", {})
        assert received_contexts[1] == ("signal", {"data": {"data_output": "data_data"}})
        assert received_contexts[2][0] == "backtest"
        assert "data" in received_contexts[2][1]
        assert "signal" in received_contexts[2][1]


def test_workflow_engine_subset_execution():
    """Test executing specific subset of steps."""
    config = WorkflowConfig(
        signal_name="test_signal",
        strategy_name="test_strategy",
        steps=["data", "backtest"],  # Skip signal
    )
    
    execution_order = []
    
    class OrderedMockStep(BaseWorkflowStep):
        def __init__(self, config: WorkflowConfig, step_name: str):
            super().__init__(config)
            self._step_name = step_name
            
        @property
        def name(self) -> str:
            return self._step_name
        
        def execute(self, context: dict[str, Any]) -> dict[str, Any]:
            execution_order.append(self.name)
            return {"result": self.name}
        
        def output_exists(self) -> bool:
            return False
        
        def get_output_path(self) -> Path:
            return Path("/mock")
    
    with patch("aponyx.workflows.engine.StepRegistry") as mock_registry_class:
        mock_registry = MagicMock()
        # Registry returns all steps
        mock_registry.get_all_steps.return_value = [
            OrderedMockStep(config, "data"),
            OrderedMockStep(config, "signal"),
            OrderedMockStep(config, "backtest"),
        ]
        mock_registry_class.return_value = mock_registry
        
        engine = WorkflowEngine(config)
        result = engine.execute()
        
        # Only data and backtest should execute
        assert execution_order == ["data", "backtest"]
        assert result["steps_completed"] == 2
