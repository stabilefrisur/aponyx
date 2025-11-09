"""
Return attribution and decomposition analysis.

Provides tools for attributing backtest returns to various sources including
trade direction, signal strength, and win/loss patterns.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def attribute_by_direction(
    pnl_df: pd.DataFrame,
    positions_df: pd.DataFrame,
) -> dict[str, float]:
    """
    Attribute returns by trade direction (long vs short).

    Parameters
    ----------
    pnl_df : pd.DataFrame
        P&L DataFrame with 'net_pnl' column.
    positions_df : pd.DataFrame
        Position DataFrame with 'position' column (+1 for long, -1 for short).

    Returns
    -------
    dict[str, float]
        Attribution with keys:
        - 'long_pnl': Total P&L from long positions
        - 'short_pnl': Total P&L from short positions
        - 'long_pct': Percentage of total P&L from longs
        - 'short_pct': Percentage of total P&L from shorts

    Notes
    -----
    For CDX overlay strategies:
    - Long position = sell protection (bullish credit)
    - Short position = buy protection (bearish credit)

    Examples
    --------
    >>> direction_attr = attribute_by_direction(result.pnl, result.positions)
    >>> print(f"Long contributed: {direction_attr['long_pct']:.1%}")
    """
    logger.debug("Computing directional attribution")

    # Align indices
    aligned_pnl = pnl_df.reindex(positions_df.index)["net_pnl"]
    position = positions_df["position"]

    # Separate P&L by direction
    long_mask = position > 0
    short_mask = position < 0

    long_pnl = aligned_pnl[long_mask].sum()
    short_pnl = aligned_pnl[short_mask].sum()
    total_pnl = long_pnl + short_pnl

    # Compute percentages
    if abs(total_pnl) > 0:
        long_pct = long_pnl / total_pnl
        short_pct = short_pnl / total_pnl
    else:
        long_pct = 0.0
        short_pct = 0.0

    logger.debug(
        "Direction attribution: long=%.2f (%.1f%%), short=%.2f (%.1f%%)",
        long_pnl,
        long_pct * 100,
        short_pnl,
        short_pct * 100,
    )

    return {
        "long_pnl": long_pnl,
        "short_pnl": short_pnl,
        "long_pct": long_pct,
        "short_pct": short_pct,
    }


def attribute_by_signal_strength(
    pnl_df: pd.DataFrame,
    positions_df: pd.DataFrame,
    n_quantiles: int = 3,
) -> dict[str, float]:
    """
    Attribute returns by signal strength quantiles.

    Separates P&L based on absolute signal strength at position entry,
    using quantile buckets (e.g., weak/medium/strong signals).

    Parameters
    ----------
    pnl_df : pd.DataFrame
        P&L DataFrame with 'net_pnl' column.
    positions_df : pd.DataFrame
        Position DataFrame with 'signal' and 'position' columns.
    n_quantiles : int
        Number of quantile buckets. Default: 3 (terciles).

    Returns
    -------
    dict[str, float]
        Attribution by quantile with keys:
        - 'q1_pnl', 'q2_pnl', ...: P&L per quantile
        - 'q1_pct', 'q2_pct', ...: Percentage contribution per quantile
        - 'quantile_labels': List of quantile labels

    Notes
    -----
    Uses absolute signal values to handle both long and short positions.
    Quantiles are computed on days when positioned (position != 0).

    Examples
    --------
    >>> signal_attr = attribute_by_signal_strength(result.pnl, result.positions, n_quantiles=3)
    >>> print(f"Strongest signals: {signal_attr['q3_pct']:.1%}")
    """
    logger.debug("Computing signal strength attribution: n_quantiles=%d", n_quantiles)

    # Filter to positioned days only
    positioned = positions_df[positions_df["position"] != 0].copy()

    if len(positioned) == 0:
        logger.warning("No positioned days found for signal attribution")
        return (
            {f"q{i+1}_pnl": 0.0 for i in range(n_quantiles)}
            | {f"q{i+1}_pct": 0.0 for i in range(n_quantiles)}
            | {"quantile_labels": [f"Q{i+1}" for i in range(n_quantiles)]}
        )

    # Use absolute signal strength
    positioned["abs_signal"] = positioned["signal"].abs()

    # Assign quantiles (1 = weakest, n_quantiles = strongest)
    positioned["quantile"] = pd.qcut(
        positioned["abs_signal"],
        q=n_quantiles,
        labels=range(1, n_quantiles + 1),
        duplicates="drop",
    )

    # Align P&L
    aligned_pnl = pnl_df.reindex(positioned.index)["net_pnl"]

    # Aggregate by quantile
    quantile_pnl = aligned_pnl.groupby(positioned["quantile"]).sum()
    total_pnl = aligned_pnl.sum()

    # Build result dictionary
    result = {}
    for q in range(1, n_quantiles + 1):
        pnl_value = quantile_pnl.get(q, 0.0)
        pct_value = pnl_value / total_pnl if abs(total_pnl) > 0 else 0.0

        result[f"q{q}_pnl"] = pnl_value
        result[f"q{q}_pct"] = pct_value

    result["quantile_labels"] = [f"Q{i+1}" for i in range(n_quantiles)]

    logger.debug(
        "Signal strength attribution: %s",
        ", ".join([f"Q{i+1}={result[f'q{i+1}_pct']:.1%}" for i in range(n_quantiles)]),
    )

    return result


def attribute_by_win_loss(
    pnl_df: pd.DataFrame,
    positions_df: pd.DataFrame,
) -> dict[str, float]:
    """
    Decompose P&L into winning and losing trade contributions.

    Parameters
    ----------
    pnl_df : pd.DataFrame
        P&L DataFrame with 'net_pnl' column.
    positions_df : pd.DataFrame
        Position DataFrame with 'position' column.

    Returns
    -------
    dict[str, float]
        Win/loss attribution with keys:
        - 'gross_wins': Sum of all positive daily P&L
        - 'gross_losses': Sum of all negative daily P&L (negative value)
        - 'net_pnl': gross_wins + gross_losses
        - 'win_contribution': Percentage from wins
        - 'loss_contribution': Percentage from losses

    Notes
    -----
    This is a daily P&L decomposition, not trade-level.
    Useful for understanding contribution from up-days vs down-days.

    Examples
    --------
    >>> wl_attr = attribute_by_win_loss(result.pnl, result.positions)
    >>> print(f"Wins contributed: {wl_attr['win_contribution']:.1%}")
    """
    logger.debug("Computing win/loss attribution")

    # Only include positioned days
    positioned_mask = positions_df["position"] != 0
    aligned_pnl = pnl_df.reindex(positions_df.index).loc[positioned_mask, "net_pnl"]

    # Separate wins and losses
    gross_wins = aligned_pnl[aligned_pnl > 0].sum()
    gross_losses = aligned_pnl[aligned_pnl < 0].sum()  # Negative value
    net_pnl = gross_wins + gross_losses

    # Compute contributions
    if abs(net_pnl) > 0:
        win_contribution = gross_wins / abs(net_pnl)
        loss_contribution = abs(gross_losses) / abs(net_pnl)
    else:
        win_contribution = 0.0
        loss_contribution = 0.0

    logger.debug(
        "Win/loss: wins=%.2f (%.1f%%), losses=%.2f (%.1f%%)",
        gross_wins,
        win_contribution * 100,
        gross_losses,
        loss_contribution * 100,
    )

    return {
        "gross_wins": gross_wins,
        "gross_losses": gross_losses,
        "net_pnl": net_pnl,
        "win_contribution": win_contribution,
        "loss_contribution": loss_contribution,
    }


def compute_attribution(
    pnl_df: pd.DataFrame,
    positions_df: pd.DataFrame,
    n_quantiles: int = 3,
) -> dict[str, dict[str, float]]:
    """
    Compute all attribution analyses.

    Orchestrates computation of directional, signal strength, and
    win/loss attribution.

    Parameters
    ----------
    pnl_df : pd.DataFrame
        P&L DataFrame with 'net_pnl' column.
    positions_df : pd.DataFrame
        Position DataFrame with 'signal' and 'position' columns.
    n_quantiles : int
        Number of quantiles for signal strength attribution. Default: 3.

    Returns
    -------
    dict[str, dict[str, float]]
        Nested dictionary with keys:
        - 'direction': Directional attribution
        - 'signal_strength': Signal quantile attribution
        - 'win_loss': Win/loss decomposition

    Notes
    -----
    This function provides comprehensive return attribution for
    understanding sources of backtest performance.

    Examples
    --------
    >>> attribution = compute_attribution(result.pnl, result.positions, n_quantiles=3)
    >>> print(f"Long P&L: ${attribution['direction']['long_pnl']:,.0f}")
    >>> print(f"Strongest signals: {attribution['signal_strength']['q3_pct']:.1%}")
    """
    logger.info("Computing return attribution: n_quantiles=%d", n_quantiles)

    direction_attr = attribute_by_direction(pnl_df, positions_df)
    signal_attr = attribute_by_signal_strength(pnl_df, positions_df, n_quantiles)
    wl_attr = attribute_by_win_loss(pnl_df, positions_df)

    attribution = {
        "direction": direction_attr,
        "signal_strength": signal_attr,
        "win_loss": wl_attr,
    }

    logger.info(
        "Attribution computed: long=%.1f%%, wins=%.1f%%",
        direction_attr["long_pct"] * 100,
        wl_attr["win_contribution"] * 100,
    )

    return attribution
