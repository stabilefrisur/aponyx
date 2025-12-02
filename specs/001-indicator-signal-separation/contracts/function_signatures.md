# API Contracts: Function Signatures

**Feature**: Indicator-Signal Separation  
**Date**: 2025-11-30  
**Purpose**: Define Python function signatures for indicator computation and signal composition

---

## Indicator Computation API

### compute_indicator()

```python
def compute_indicator(
    indicator_name: str,
    market_data: dict[str, pd.DataFrame],
    config: IndicatorConfig | None = None,
    use_cache: bool = True,
) -> pd.Series:
    """
    Compute indicator from market data with caching.
    
    Parameters
    ----------
    indicator_name : str
        Indicator name from indicator_catalog.json
    market_data : dict[str, pd.DataFrame]
        Instrument type to DataFrame mapping
        (e.g., {"cdx": cdx_df, "etf": etf_df})
    config : IndicatorConfig or None
        Optional runtime configuration overrides
    use_cache : bool, default True
        Whether to use cached indicator values if available
    
    Returns
    -------
    pd.Series
        Indicator values with DatetimeIndex in economically interpretable units
    
    Raises
    ------
    ValueError
        If indicator_name not found in registry
        If data_requirements not satisfied by market_data
    KeyError
        If required instrument type missing from market_data
    
    Examples
    --------
    >>> market_data = {"cdx": cdx_df, "etf": etf_df}
    >>> basis = compute_indicator("cdx_etf_spread_diff", market_data)
    >>> basis.head()
    2024-01-01    15.2
    2024-01-02    14.8
    ...
    dtype: float64
    """
```

### Individual Indicator Functions

```python
def compute_cdx_etf_spread_diff(
    cdx_df: pd.DataFrame,
    etf_df: pd.DataFrame,
    parameters: dict[str, Any],
) -> pd.Series:
    """
    Compute CDX spread minus ETF spread in basis points.
    
    Parameters
    ----------
    cdx_df : pd.DataFrame
        CDX spread data with DatetimeIndex and 'spread' column
    etf_df : pd.DataFrame
        ETF spread data with DatetimeIndex and 'spread' column
    parameters : dict[str, Any]
        Indicator-specific parameters (from catalog)
    
    Returns
    -------
    pd.Series
        Spread difference in basis points
        
    Notes
    -----
    Output units: basis_points
    Positive values: CDX spreads wider than ETF spreads
    """
```

```python
def compute_spread_momentum(
    cdx_df: pd.DataFrame,
    parameters: dict[str, Any],
) -> pd.Series:
    """
    Compute N-day spread change in basis points.
    
    Parameters
    ----------
    cdx_df : pd.DataFrame
        CDX spread data with DatetimeIndex and 'spread' column
    parameters : dict[str, Any]
        Must contain 'lookback' key for N-day window
    
    Returns
    -------
    pd.Series
        N-day spread change in basis points
        
    Notes
    -----
    Output units: basis_points
    Positive values: Spreads widening (credit deteriorating)
    Negative values: Spreads tightening (credit improving)
    """
```

---

## Signal Composition API

### apply_signal_transformation()

```python
def apply_signal_transformation(
    indicator: pd.Series,
    transformation_name: str,
    config: TransformationConfig | None = None,
) -> pd.Series:
    """
    Apply transformation to indicator to create signal.
    
    Parameters
    ----------
    indicator : pd.Series
        Indicator values with DatetimeIndex
    transformation_name : str
        Transformation name from transformation_catalog.json
    config : TransformationConfig or None
        Optional runtime configuration overrides
    
    Returns
    -------
    pd.Series
        Transformed signal values with DatetimeIndex
    
    Raises
    ------
    ValueError
        If transformation_name not found in registry
    
    Examples
    --------
    >>> indicator = compute_indicator("cdx_etf_spread_diff", market_data)
    >>> signal = apply_signal_transformation(indicator, "z_score_20d")
    >>> signal.head()
    2024-01-01    2.1
    2024-01-02    1.8
    ...
    dtype: float64
    """
```

### compose_signal()

```python
def compose_signal(
    signal_name: str,
    market_data: dict[str, pd.DataFrame],
    config: SignalConfig | None = None,
    use_cache: bool = True,
) -> pd.Series:
    """
    Compose signal from indicators and transformations.
    
    This is the high-level API for signal computation that:
    1. Retrieves indicator dependencies from catalog
    2. Computes each required indicator (with caching)
    3. Applies transformations from catalog
    4. Combines indicators if composition_logic specified
    5. Applies sign_multiplier
    
    Parameters
    ----------
    signal_name : str
        Signal name from signal_catalog.json
    market_data : dict[str, pd.DataFrame]
        Instrument type to DataFrame mapping
    config : SignalConfig or None
        Optional runtime configuration overrides
    use_cache : bool, default True
        Whether to use cached indicator values
    
    Returns
    -------
    pd.Series
        Signal values with DatetimeIndex (typically z-score normalized)
    
    Raises
    ------
    ValueError
        If signal_name not found in registry
        If indicator dependencies cannot be computed
    
    Examples
    --------
    >>> market_data = {"cdx": cdx_df, "vix": vix_df}
    >>> signal = compose_signal("cdx_vix_gap", market_data)
    >>> signal.head()
    2024-01-01    2.1
    2024-01-02    1.8
    ...
    dtype: float64
    """
```

---

## Cache Management API

### generate_indicator_cache_key()

```python
def generate_indicator_cache_key(
    indicator_name: str,
    parameters: dict[str, Any],
    input_data: dict[str, pd.DataFrame],
) -> str:
    """
    Generate cache key for indicator with parameter and data hashing.
    
    Parameters
    ----------
    indicator_name : str
        Indicator name from catalog
    parameters : dict[str, Any]
        Indicator parameters
    input_data : dict[str, pd.DataFrame]
        Market data used for computation
    
    Returns
    -------
    str
        Cache key: {indicator_name}_{params_hash}_{data_hash}
    
    Examples
    --------
    >>> key = generate_indicator_cache_key(
    ...     "cdx_etf_spread_diff",
    ...     {},
    ...     {"cdx": cdx_df, "etf": etf_df}
    ... )
    >>> key
    'cdx_etf_spread_diff_d41d8cd9_a3f5b2c1'
    """
```

### save_indicator_to_cache()

```python
def save_indicator_to_cache(
    cache_key: str,
    indicator_values: pd.Series,
    cache_dir: Path,
) -> Path:
    """
    Save computed indicator to cache.
    
    Parameters
    ----------
    cache_key : str
        Cache key from generate_indicator_cache_key()
    indicator_values : pd.Series
        Computed indicator time series
    cache_dir : Path
        Cache directory (data/cache/indicators/)
    
    Returns
    -------
    Path
        Path to saved cache file
    """
```

### load_indicator_from_cache()

```python
def load_indicator_from_cache(
    cache_key: str,
    cache_dir: Path,
) -> pd.Series | None:
    """
    Load indicator from cache if exists.
    
    Parameters
    ----------
    cache_key : str
        Cache key from generate_indicator_cache_key()
    cache_dir : Path
        Cache directory (data/cache/indicators/)
    
    Returns
    -------
    pd.Series or None
        Cached indicator values, or None if cache miss
    """
```

### invalidate_indicator_cache()

```python
def invalidate_indicator_cache(
    indicator_name: str | None = None,
    cache_dir: Path = INDICATOR_CACHE_DIR,
) -> int:
    """
    Invalidate indicator cache (delete cached files).
    
    Parameters
    ----------
    indicator_name : str or None
        If specified, delete only this indicator's cache files
        If None, delete entire indicator cache directory
    cache_dir : Path
        Cache directory to clean
    
    Returns
    -------
    int
        Number of cache files deleted
    
    Examples
    --------
    >>> # Invalidate specific indicator
    >>> count = invalidate_indicator_cache("cdx_etf_spread_diff")
    >>> print(f"Deleted {count} cache files")
    
    >>> # Invalidate all indicators (e.g., after catalog change)
    >>> count = invalidate_indicator_cache()
    >>> print(f"Deleted {count} cache files")
    """
```

---

## Registry Query API

### IndicatorRegistry.get_dependent_signals()

```python
class IndicatorRegistry:
    def get_dependent_signals(self, indicator_name: str) -> list[str]:
        """
        Get list of signals that depend on this indicator.
        
        Parameters
        ----------
        indicator_name : str
            Indicator name to query
        
        Returns
        -------
        list[str]
            Signal names that have indicator_name in their dependencies
        
        Raises
        ------
        ValueError
            If indicator_name not found in registry
        
        Examples
        --------
        >>> registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)
        >>> signals = registry.get_dependent_signals("cdx_etf_spread_diff")
        >>> signals
        ['cdx_etf_basis', 'cdx_etf_percentile']
        """
```

### IndicatorRegistry.get_all_dependencies()

```python
class IndicatorRegistry:
    def get_all_dependencies(self) -> dict[str, list[str]]:
        """
        Get complete dependency graph (indicator → signals).
        
        Returns
        -------
        dict[str, list[str]]
            Mapping of indicator names to lists of dependent signal names
        
        Examples
        --------
        >>> registry = IndicatorRegistry(INDICATOR_CATALOG_PATH)
        >>> deps = registry.get_all_dependencies()
        >>> deps
        {
            'cdx_etf_spread_diff': ['cdx_etf_basis'],
            'spread_momentum_5d': ['spread_momentum'],
            'cdx_vix_deviation_gap_20d': ['cdx_vix_gap']
        }
        """
```

---

## Configuration Classes

### IndicatorConfig

```python
@dataclass(frozen=True)
class IndicatorConfig:
    """
    Runtime configuration for indicator computation.
    
    Attributes
    ----------
    cache_enabled : bool, default True
        Whether to use indicator caching
    cache_dir : Path
        Directory for indicator cache files
    """
    cache_enabled: bool = True
    cache_dir: Path = INDICATOR_CACHE_DIR
    
    def __post_init__(self) -> None:
        if not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True, exist_ok=True)
```

### TransformationConfig

```python
@dataclass(frozen=True)
class TransformationConfig:
    """
    Runtime configuration for signal transformations.
    
    Currently no runtime overrides needed (all params in catalog).
    Placeholder for future extensibility.
    """
    pass
```

---

**API Contracts Complete**: All function signatures defined for indicator computation, signal composition, caching, and registry queries.
