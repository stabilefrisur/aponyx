"""
Workflow step abstractions.

Defines protocol for executable workflow steps with dependency tracking,
caching, and standardized I/O.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Protocol

from .config import WorkflowConfig

logger = logging.getLogger(__name__)


class WorkflowStep(Protocol):
    """
    Protocol for executable workflow steps.
    
    All workflow steps must implement this interface for orchestration.
    
    Attributes
    ----------
    name : str
        Step identifier (used for caching and logging).
    config : WorkflowConfig
        Workflow configuration.
        
    Methods
    -------
    execute(context)
        Execute step logic and return output data.
    output_exists()
        Check if step output already exists (for caching).
    get_output_path()
        Return path to expected output files.
    """
    
    name: str
    config: WorkflowConfig
    
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute workflow step.
        
        Parameters
        ----------
        context : dict[str, Any]
            Outputs from previous steps (keyed by step name).
            
        Returns
        -------
        dict[str, Any]
            Step output data to pass to subsequent steps.
            
        Notes
        -----
        Steps should be idempotent: running twice produces same results.
        Use context["data"] to access data from DataStep, etc.
        """
        ...
    
    def output_exists(self) -> bool:
        """
        Check if step output files exist.
        
        Returns
        -------
        bool
            True if all required outputs exist, False otherwise.
            
        Notes
        -----
        Used by caching logic to skip completed steps.
        Should check file existence and basic validation.
        """
        ...
    
    def get_output_path(self) -> Path:
        """
        Get expected output directory path.
        
        Returns
        -------
        Path
            Directory where step outputs are saved.
        """
        ...


class BaseWorkflowStep(ABC):
    """
    Abstract base class for workflow steps.
    
    Provides common functionality for concrete step implementations.
    
    Parameters
    ----------
    config : WorkflowConfig
        Workflow configuration.
    """
    
    def __init__(self, config: WorkflowConfig) -> None:
        self.config = config
        
    @property
    @abstractmethod
    def name(self) -> str:
        """Step identifier."""
        ...
    
    @abstractmethod
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute step logic."""
        ...
    
    @abstractmethod
    def output_exists(self) -> bool:
        """Check if output exists."""
        ...
    
    @abstractmethod
    def get_output_path(self) -> Path:
        """Get output directory."""
        ...
    
    def _log_start(self) -> None:
        """Log step start."""
        logger.info("Starting step: %s", self.name)
        
    def _log_complete(self, output: dict[str, Any]) -> None:
        """Log step completion."""
        logger.info("Completed step: %s", self.name)
