"""Tests for scoring functions."""

from aponyx.evaluation.suitability import scoring
from aponyx.evaluation.suitability.config import SuitabilityConfig


class TestScoreDataHealth:
    """Test data health scoring."""

    def test_sufficient_obs_no_missing(self) -> None:
        """Test perfect data health."""
        score = scoring.score_data_health(
            valid_obs=600,
            missing_pct=0.0,
            min_obs=500,
        )

        assert score == 1.0

    def test_sufficient_obs_some_missing(self) -> None:
        """Test data health with some missing data."""
        score = scoring.score_data_health(
            valid_obs=600,
            missing_pct=10.0,  # 10% missing
            min_obs=500,
        )

        assert score == 0.5  # 1 - 10/20 = 0.5

    def test_insufficient_obs(self) -> None:
        """Test insufficient observations returns 0.0."""
        score = scoring.score_data_health(
            valid_obs=400,
            missing_pct=0.0,
            min_obs=500,
        )

        assert score == 0.0

    def test_high_missing_data(self) -> None:
        """Test that high missing data is heavily penalized."""
        score = scoring.score_data_health(
            valid_obs=600,
            missing_pct=20.0,  # 20% missing (threshold)
            min_obs=500,
        )

        assert score == 0.0

        score = scoring.score_data_health(
            valid_obs=600,
            missing_pct=25.0,  # Above threshold
            min_obs=500,
        )

        assert score == 0.0  # Capped at 0


class TestScorePredictive:
    """Test predictive scoring."""

    def test_weak_signal(self) -> None:
        """Test weak predictive signal."""
        score = scoring.score_predictive(mean_abs_tstat=1.0)

        assert abs(score - 1.0 / 3.0) < 1e-6

    def test_significant_signal(self) -> None:
        """Test statistically significant signal."""
        score = scoring.score_predictive(mean_abs_tstat=2.5)

        assert abs(score - 2.5 / 3.0) < 1e-6

    def test_strong_signal_capped(self) -> None:
        """Test that strong signal is capped at 1.0."""
        score = scoring.score_predictive(mean_abs_tstat=4.0)

        assert score == 1.0  # Capped

        score = scoring.score_predictive(mean_abs_tstat=10.0)

        assert score == 1.0  # Still capped


class TestScoreEconomic:
    """Test economic scoring."""

    def test_negligible_effect(self) -> None:
        """Test negligible economic effect."""
        score = scoring.score_economic(effect_size_bps=0.3)

        assert score == 0.2

    def test_moderate_effect(self) -> None:
        """Test moderate economic effect."""
        score = scoring.score_economic(effect_size_bps=1.0)

        assert score == 0.6

        score = scoring.score_economic(effect_size_bps=1.9)

        assert score == 0.6

    def test_meaningful_effect(self) -> None:
        """Test meaningful economic effect."""
        score = scoring.score_economic(effect_size_bps=2.5)

        assert score == 1.0

        score = scoring.score_economic(effect_size_bps=10.0)

        assert score == 1.0

    def test_threshold_boundaries(self) -> None:
        """Test scoring at exact threshold boundaries."""
        # Just below 0.5
        score = scoring.score_economic(effect_size_bps=0.49)
        assert score == 0.2

        # At 0.5
        score = scoring.score_economic(effect_size_bps=0.5)
        assert score == 0.6

        # Just below 2.0
        score = scoring.score_economic(effect_size_bps=1.99)
        assert score == 0.6

        # At 2.0
        score = scoring.score_economic(effect_size_bps=2.0)
        assert score == 1.0


class TestScoreStability:
    """Test stability scoring."""

    def test_consistent_sign(self) -> None:
        """Test consistent sign returns 1.0."""
        score = scoring.score_stability(sign_consistent=True)

        assert score == 1.0

    def test_inconsistent_sign(self) -> None:
        """Test inconsistent sign returns 0.0."""
        score = scoring.score_stability(sign_consistent=False)

        assert score == 0.0


class TestComputeCompositeScore:
    """Test composite scoring."""

    def test_default_weights(self) -> None:
        """Test composite with default weights."""
        config = SuitabilityConfig()

        composite = scoring.compute_composite_score(
            data_health_score=1.0,
            predictive_score=1.0,
            economic_score=1.0,
            stability_score=1.0,
            config=config,
        )

        assert composite == 1.0  # All perfect

    def test_weighted_average(self) -> None:
        """Test weighted average calculation."""
        config = SuitabilityConfig()

        composite = scoring.compute_composite_score(
            data_health_score=0.8,
            predictive_score=0.9,
            economic_score=0.6,
            stability_score=1.0,
            config=config,
        )

        expected = 0.2 * 0.8 + 0.4 * 0.9 + 0.2 * 0.6 + 0.2 * 1.0
        assert abs(composite - expected) < 1e-6

    def test_custom_weights(self) -> None:
        """Test composite with custom weights."""
        config = SuitabilityConfig(
            data_health_weight=0.1,
            predictive_weight=0.5,
            economic_weight=0.3,
            stability_weight=0.1,
        )

        composite = scoring.compute_composite_score(
            data_health_score=1.0,
            predictive_score=0.8,
            economic_score=0.6,
            stability_score=0.0,
            config=config,
        )

        expected = 0.1 * 1.0 + 0.5 * 0.8 + 0.3 * 0.6 + 0.1 * 0.0
        assert abs(composite - expected) < 1e-6


class TestAssignDecision:
    """Test decision assignment."""

    def test_pass_decision(self) -> None:
        """Test PASS decision."""
        config = SuitabilityConfig()

        decision = scoring.assign_decision(0.75, config)
        assert decision == "PASS"

        decision = scoring.assign_decision(0.7, config)  # Exactly at threshold
        assert decision == "PASS"

    def test_hold_decision(self) -> None:
        """Test HOLD decision."""
        config = SuitabilityConfig()

        decision = scoring.assign_decision(0.55, config)
        assert decision == "HOLD"

        decision = scoring.assign_decision(0.4, config)  # Exactly at threshold
        assert decision == "HOLD"

    def test_fail_decision(self) -> None:
        """Test FAIL decision."""
        config = SuitabilityConfig()

        decision = scoring.assign_decision(0.35, config)
        assert decision == "FAIL"

        decision = scoring.assign_decision(0.0, config)
        assert decision == "FAIL"

    def test_custom_thresholds(self) -> None:
        """Test decision with custom thresholds."""
        config = SuitabilityConfig(
            pass_threshold=0.8,
            hold_threshold=0.5,
        )

        decision = scoring.assign_decision(0.85, config)
        assert decision == "PASS"

        decision = scoring.assign_decision(0.65, config)
        assert decision == "HOLD"

        decision = scoring.assign_decision(0.45, config)
        assert decision == "FAIL"
