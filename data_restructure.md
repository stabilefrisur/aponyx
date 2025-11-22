Restructure how data is persisted in this project. 

```
data/
  .registries/                            # Runtime registries (JSON)
    registry.json                         # DataRegistry
    suitability.json                      # SuitabilityRegistry
    performance.json                      # PerformanceRegistry
  
  raw/                                    # Permanent source data
    bloomberg/{instrument}_{hash}.parquet
    synthetic/{instrument}_{hash}.parquet
  
  cache/                                  # TTL-based performance cache
    bloomberg/{instrument}_{key}.parquet
    file/{instrument}_{key}.parquet
  
  workflows/                              # Complete workflow runs
    {signal}_{strategy}_{timestamp}/
      data/                               # Data artifacts (parquet)
        raw.parquet
        features.parquet
      signals/                            # Signal values (parquet)
        {signal_name}.parquet
      backtest/                           # Backtest results (parquet)
        pnl.parquet
        positions.parquet
      reports/                            # THIS RUN'S reports
        suitability.md
        performance.md
      visualizations/                     # THIS RUN'S visualizations
        equity_curve.html
        drawdown.html
        signal.html
      metadata.json                       # Workflow metadata

logs/                                     # Runtime logs only
  workflow_{signal}_{strategy}_{timestamp}.log
```

Reports belong WITH the data that produced them, not in a separate top-level folder. This ensures:
- Complete traceability: Each workflow run is self-contained
- Easy cleanup: Delete old runs without losing associations
- Version control: Can compare how reports evolved as code changed
- Reproducibility: All inputs, outputs, and reports in one place
