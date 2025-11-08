"""
Signal-Product Suitability Evaluation Demonstration

Demonstrates pre-backtest screening workflow using suitability evaluation:
1. Generate synthetic signal and product data
2. Evaluate signal suitability for different products
3. Register evaluations in SuitabilityRegistry
4. Generate and save Markdown reports
5. Query registry with filters

The suitability evaluation acts as a quality gate before backtesting,
answering: "Does this signal contain meaningful information for this product?"

Four-component scoring framework:
- Data Health: Sample size and missing data quality
- Predictive Association: Statistical significance of relationship
- Economic Relevance: Magnitude of effect size in bps
- Temporal Stability: Consistency across subperiods

Output: Evaluation results, Markdown reports, registry tracking

Configuration:
  - Signals: strong_signal, weak_signal, noisy_signal
  - Products: CDX_IG_5Y, CDX_HY_5Y
  - Lags: [1, 3, 5] days
  - Min observations: 500
  - Decision thresholds: PASS ≥ 0.7, HOLD 0.4-0.7, FAIL < 0.4
"""

import logging
import sys

import numpy as np
import pandas as pd

import aponyx
from aponyx.config import EVALUATION_DIR, SUITABILITY_REGISTRY_PATH
from aponyx.evaluation.suitability import (
    evaluate_signal_suitability,
    SuitabilityConfig,
    SuitabilityRegistry,
    generate_suitability_report,
    save_report,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def generate_synthetic_data(
    n_obs: int = 600, seed: int | None = None
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Generate synthetic signal and target data for demonstration.

    Parameters
    ----------
    n_obs : int
        Number of observations.
    seed : int | None
        Random seed for reproducibility.

    Returns
    -------
    tuple[pd.Series, pd.Series, pd.Series]
        Strong signal, weak signal, and target series.
    """
    if seed is not None:
        np.random.seed(seed)

    dates = pd.date_range("2020-01-01", periods=n_obs, freq="D")

    # Strong signal: clear predictive content
    strong_signal = pd.Series(np.random.randn(n_obs), index=dates, name="strong_signal")

    # Weak signal: some predictive content but noisy
    weak_signal = pd.Series(np.random.randn(n_obs), index=dates, name="weak_signal")

    # Target: related to strong signal, weakly related to weak signal
    target = strong_signal * 2.0 + weak_signal * 0.3 + np.random.randn(n_obs) * 0.5

    return strong_signal, weak_signal, target


def main() -> None:
    """Run complete suitability evaluation demonstration."""
    print("=" * 70)
    print("SUITABILITY EVALUATION DEMONSTRATION")
    print("Pre-Backtest Signal Screening")
    print("=" * 70)
    print(f"Framework version: {aponyx.__version__}")

    # Generate synthetic data
    print("\n" + "=" * 70)
    print("PART 1: Generate Synthetic Data")
    print("=" * 70)

    print("\nGenerating synthetic signals and target...")
    strong_signal, weak_signal, target = generate_synthetic_data(n_obs=600, seed=42)

    print(f"  Strong signal observations: {len(strong_signal)}")
    print(f"  Weak signal observations: {len(weak_signal)}")
    print(f"  Target observations: {len(target)}")
    print(f"  Date range: {strong_signal.index[0]} to {strong_signal.index[-1]}")

    # Configure evaluation
    print("\n" + "=" * 70)
    print("PART 2: Configure Evaluation")
    print("=" * 70)

    config = SuitabilityConfig(
        lags=[1, 3, 5],
        min_obs=500,
        pass_threshold=0.7,
        hold_threshold=0.4,
    )

    print(f"\n  Lags: {config.lags}")
    print(f"  Minimum observations: {config.min_obs}")
    print(f"  PASS threshold: {config.pass_threshold:.1f}")
    print(f"  HOLD threshold: {config.hold_threshold:.1f}")
    print("  Component weights:")
    print(f"    - Data Health: {config.data_health_weight:.1f}")
    print(f"    - Predictive: {config.predictive_weight:.1f}")
    print(f"    - Economic: {config.economic_weight:.1f}")
    print(f"    - Stability: {config.stability_weight:.1f}")

    # Evaluate strong signal
    print("\n" + "=" * 70)
    print("PART 3: Evaluate Strong Signal")
    print("=" * 70)

    print("\nEvaluating strong_signal vs CDX_IG_5Y...")
    result_strong = evaluate_signal_suitability(strong_signal, target, config)

    print(f"\n  Decision: {result_strong.decision}")
    print(f"  Composite Score: {result_strong.composite_score:.3f}")
    print("  Component Scores:")
    print(f"    - Data Health: {result_strong.data_health_score:.3f}")
    print(f"    - Predictive: {result_strong.predictive_score:.3f}")
    print(f"    - Economic: {result_strong.economic_score:.3f}")
    print(f"    - Stability: {result_strong.stability_score:.3f}")

    # Evaluate weak signal
    print("\n" + "=" * 70)
    print("PART 4: Evaluate Weak Signal")
    print("=" * 70)

    print("\nEvaluating weak_signal vs CDX_IG_5Y...")
    result_weak = evaluate_signal_suitability(weak_signal, target, config)

    print(f"\n  Decision: {result_weak.decision}")
    print(f"  Composite Score: {result_weak.composite_score:.3f}")
    print("  Component Scores:")
    print(f"    - Data Health: {result_weak.data_health_score:.3f}")
    print(f"    - Predictive: {result_weak.predictive_score:.3f}")
    print(f"    - Economic: {result_weak.economic_score:.3f}")
    print(f"    - Stability: {result_weak.stability_score:.3f}")

    # Generate reports
    print("\n" + "=" * 70)
    print("PART 5: Generate Markdown Reports")
    print("=" * 70)

    print("\nGenerating reports...")
    report_strong = generate_suitability_report(result_strong, "strong_signal", "CDX_IG_5Y")
    report_weak = generate_suitability_report(result_weak, "weak_signal", "CDX_IG_5Y")

    # Save reports
    output_dir = EVALUATION_DIR / "demo_reports"
    path_strong = save_report(report_strong, "strong_signal", "CDX_IG_5Y", output_dir)
    path_weak = save_report(report_weak, "weak_signal", "CDX_IG_5Y", output_dir)

    print(f"  Saved strong signal report: {path_strong}")
    print(f"  Saved weak signal report: {path_weak}")

    # Registry tracking
    print("\n" + "=" * 70)
    print("PART 6: Registry Tracking")
    print("=" * 70)

    print("\nInitializing SuitabilityRegistry...")
    registry = SuitabilityRegistry(SUITABILITY_REGISTRY_PATH)

    print("\nRegistering evaluations...")
    id_strong = registry.register_evaluation(
        result_strong, "strong_signal", "CDX_IG_5Y", report_path=path_strong
    )
    id_weak = registry.register_evaluation(
        result_weak, "weak_signal", "CDX_IG_5Y", report_path=path_weak
    )

    print(f"  Registered strong signal: {id_strong}")
    print(f"  Registered weak signal: {id_weak}")

    # Query registry
    print("\n" + "=" * 70)
    print("PART 7: Query Registry")
    print("=" * 70)

    print("\nQuerying all evaluations...")
    all_evals = registry.list_evaluations()
    print(f"  Total evaluations: {len(all_evals)}")

    print("\nQuerying PASS evaluations...")
    pass_evals = registry.list_evaluations(decision="PASS")
    print(f"  PASS evaluations: {len(pass_evals)}")
    for eval_id in pass_evals:
        info = registry.get_evaluation_info(eval_id)
        print(f"    - {eval_id}: {info['signal_id']} + {info['product_id']}")

    print("\nQuerying HOLD/FAIL evaluations...")
    non_pass_evals = [eval_id for eval_id in all_evals if eval_id not in pass_evals]
    print(f"  HOLD/FAIL evaluations: {len(non_pass_evals)}")
    for eval_id in non_pass_evals:
        info = registry.get_evaluation_info(eval_id)
        print(f"    - {eval_id}: {info['signal_id']} + {info['product_id']}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print("\nEvaluation Results:")
    print(f"  Strong Signal -> {result_strong.decision}")
    print(f"    Composite Score: {result_strong.composite_score:.3f}")
    print(
        f"    Recommendation: {'Proceed to backtest' if result_strong.decision == 'PASS' else 'Do not backtest'}"
    )

    print(f"\n  Weak Signal -> {result_weak.decision}")
    print(f"    Composite Score: {result_weak.composite_score:.3f}")
    print(
        f"    Recommendation: {'Proceed to backtest' if result_weak.decision == 'PASS' else 'Requires judgment or skip'}"
    )

    print("\nKey Insights:")
    print("  1. Strong signals with clear predictive content score PASS")
    print("  2. Weak or noisy signals score HOLD/FAIL, avoiding wasted backtest effort")
    print("  3. Four-component framework provides interpretable scoring")
    print("  4. Registry enables tracking and comparison across evaluations")
    print("  5. Markdown reports provide detailed documentation")

    print("\nNext Steps:")
    print("  - Review reports in:")
    print(f"      {output_dir}")
    print("  - Run backtests only for PASS signals")
    print("  - Iterate on signals that score HOLD with rationale")
    print("  - Archive FAIL signals with documentation")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.exception("Demo failed")
        print(f"\nError: {e}")
        sys.exit(1)
