"""
Metrics dataclasses and computation for parameter sweeps.

Provides frozen dataclasses for indicator and backtest metrics,
plus utility functions for computing indicator statistics.
"""

import logging
from dataclasses import dataclass

import pandas as pd
from scipy import stats as scipy_stats

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IndicatorMetrics:
    """
    Statistics computed for an indicator time series.

    Attributes
    ----------
    mean : float
        Indicator mean value.
    std : float
        Indicator standard deviation.
    skewness : float
        Indicator skewness (asymmetry measure).
    kurtosis : float
        Indicator kurtosis (tail thickness measure).
    autocorr_1 : float
        1-lag autocorrelation.
    correlation_to_product : float
        Correlation to underlying product.

    Examples
    --------
    >>> metrics = IndicatorMetrics(
    ...     mean=2.5,
    ...     std=15.3,
    ...     skewness=0.12,
    ...     kurtosis=3.2,
    ...     autocorr_1=0.85,
    ...     correlation_to_product=-0.42,
    ... )
    """

    mean: float
    std: float
    skewness: float
    kurtosis: float
    autocorr_1: float
    correlation_to_product: float

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary for DataFrame construction."""
        return {
            "mean": self.mean,
            "std": self.std,
            "skewness": self.skewness,
            "kurtosis": self.kurtosis,
            "autocorr_1": self.autocorr_1,
            "correlation_to_product": self.correlation_to_product,
        }


@dataclass(frozen=True)
class BacktestMetrics:
    """
    Performance metrics from a backtest run.

    Attributes
    ----------
    sharpe_ratio : float
        Annualized Sharpe ratio.
    max_drawdown : float
        Maximum drawdown (negative value).
    hit_rate : float
        Win rate (0-1 scale).
    n_trades : int
        Total trade count.
    annualized_return : float
        Compound annual growth rate (CAGR).

    Examples
    --------
    >>> metrics = BacktestMetrics(
    ...     sharpe_ratio=1.45,
    ...     max_drawdown=-0.08,
    ...     hit_rate=0.55,
    ...     n_trades=42,
    ...     annualized_return=0.12,
    ... )
    """

    sharpe_ratio: float
    max_drawdown: float
    hit_rate: float
    n_trades: int
    annualized_return: float

    def to_dict(self) -> dict[str, float | int]:
        """Convert to dictionary for DataFrame construction."""
        return {
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "hit_rate": self.hit_rate,
            "n_trades": self.n_trades,
            "annualized_return": self.annualized_return,
        }


def compute_indicator_statistics(
    indicator: pd.Series,
    product_prices: pd.Series,
) -> IndicatorMetrics:
    """
    Compute comprehensive statistics for an indicator time series.

    Uses pandas and scipy for statistical calculations.

    Parameters
    ----------
    indicator : pd.Series
        Indicator time series with DatetimeIndex.
    product_prices : pd.Series
        Product price/spread series for correlation calculation.

    Returns
    -------
    IndicatorMetrics
        Frozen dataclass with all computed statistics.

    Notes
    -----
    - NaN values are dropped before computation
    - Autocorrelation uses 1-lag
    - Correlation computed against product_prices aligned by index

    Examples
    --------
    >>> metrics = compute_indicator_statistics(indicator_series, cdx_spread)
    >>> print(f"Mean: {metrics.mean:.2f}, Autocorr: {metrics.autocorr_1:.2f}")
    """
    logger.debug(
        "Computing indicator statistics: %d observations", len(indicator.dropna())
    )

    clean_indicator = indicator.dropna()

    if len(clean_indicator) < 2:
        logger.warning("Insufficient data for statistics computation")
        return IndicatorMetrics(
            mean=float("nan"),
            std=float("nan"),
            skewness=float("nan"),
            kurtosis=float("nan"),
            autocorr_1=float("nan"),
            correlation_to_product=float("nan"),
        )

    # Basic statistics
    mean = float(clean_indicator.mean())
    std = float(clean_indicator.std())

    # Higher moments via scipy
    skewness = float(scipy_stats.skew(clean_indicator))
    kurtosis = float(scipy_stats.kurtosis(clean_indicator))

    # Autocorrelation (1-lag)
    autocorr_1 = float(clean_indicator.autocorr(lag=1))

    # Correlation to product (align by index)
    aligned = pd.DataFrame(
        {"indicator": indicator, "product": product_prices}
    ).dropna()
    if len(aligned) > 1:
        correlation_to_product = float(
            aligned["indicator"].corr(aligned["product"])
        )
    else:
        correlation_to_product = float("nan")

    logger.debug(
        "Computed statistics: mean=%.2f, std=%.2f, skew=%.2f, kurt=%.2f",
        mean,
        std,
        skewness,
        kurtosis,
    )

    return IndicatorMetrics(
        mean=mean,
        std=std,
        skewness=skewness,
        kurtosis=kurtosis,
        autocorr_1=autocorr_1,
        correlation_to_product=correlation_to_product,
    )
