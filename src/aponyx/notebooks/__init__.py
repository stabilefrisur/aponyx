"""
Research workflow notebooks for systematic macro credit strategies.

This package contains Jupyter notebooks that implement the complete research
workflow from data download through performance analysis.

Scripts
-------
generate_synthetic_data.py
    Generate synthetic market data for development when Bloomberg unavailable.
    Replaces step 01 in development environments.

Notebooks
---------
01_data_download.ipynb
    Download market data from Bloomberg Terminal for all configured securities.
    First step in production workflow (skip in development).

02_signal_computation.ipynb
    Compute tactical credit signals from cached market data using SignalRegistry.
    Auto-detects Bloomberg or synthetic data cache.
    Second step in the systematic research workflow.

03_suitability_evaluation.ipynb
    Evaluate signal-product suitability using four-component scoring framework.
    Works with both Bloomberg and synthetic data.
    Third step in the systematic research workflow.

Workflow Sequence
-----------------
**Production (Bloomberg):**
1. Data Download (01_data_download.ipynb)
2. Signal Computation (02_signal_computation.ipynb)
3. Signal Suitability Evaluation (03_suitability_evaluation.ipynb)
4. Backtest Execution (04_backtest_execution.ipynb)
5. Performance Analysis (05_performance_analysis.ipynb)

**Development (Synthetic Data):**
1. Generate Data (python generate_synthetic_data.py)
2. Signal Computation (02_signal_computation.ipynb)
3. Signal Suitability Evaluation (03_suitability_evaluation.ipynb)
4. Backtest Execution (04_backtest_execution.ipynb)
5. Performance Analysis (05_performance_analysis.ipynb)

Notes
-----
These notebooks are included in the PyPI distribution to provide runnable
examples of the complete research workflow. They demonstrate best practices
for using the aponyx framework and can be copied/modified for custom research.

Notebooks 02+ automatically detect which data cache is available (Bloomberg
or synthetic) and work identically with both sources.
"""

__all__ = []
