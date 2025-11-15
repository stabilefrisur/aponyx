# Visualization Layer Design

## Purpose

The visualization layer provides interactive charts for analyzing backtest results, signals, and risk metrics. It prioritizes **modularity** and **integration flexibility** over styling complexity or built-in analytics.

## Architecture

### Layer Structure

```
visualization/
├── plots.py          # Pure plotting functions (functional interface)
├── visualizer.py     # Optional OO wrapper (extensibility interface)
└── app.py            # Streamlit integration stub (future)
```

### Core Design Principles

**1. Separation of Concerns**
- Plotting logic separated from computation (no analytics in viz layer)
- No direct dependencies on data/models/backtest modules
- Accepts generic pandas Series/DataFrames as inputs

**2. Return Values Over Side Effects**
- All functions return `plotly.graph_objects.Figure` instances
- No automatic `.show()` or `.write_html()` calls
- Caller controls rendering context (Jupyter, Streamlit, HTML export)

**3. Function-First Design**
- Pure functions as primary interface (`plot_equity_curve`, `plot_signal`, `plot_drawdown`)
- `Visualizer` class exists only for: theme management, batch operations, export utilities
- Avoids class bloat for simple plotting tasks

**4. Minimal Styling**
- Default Plotly themes (`plotly_white`, `plotly_dark`)
- No custom color palettes or chart decorations
- Focus on clarity and information density over aesthetics

## API Design Decisions

### Why Return Figures?

**Problem:** Many plotting libraries have side effects (display windows, save files).

**Solution:** Return figure objects for maximum flexibility:

```python
# Jupyter: immediate display
fig = plot_equity_curve(pnl)
fig.show()

# Streamlit: integrate with layout
st.plotly_chart(plot_equity_curve(pnl))

# Batch export: programmatic control
for strategy in strategies:
    fig = plot_equity_curve(strategy.pnl)
    fig.write_html(f"results/{strategy.name}.html")
```

This pattern enables:
- Testing without rendering
- Flexible integration contexts
- Post-processing (add annotations, combine subplots)

### Why Both Functions and a Class?

**Trade-off:** Functions are simple; classes enable state management.

**Resolution:** Provide both interfaces:

| Use Case | Recommended Interface |
|----------|----------------------|
| Quick one-off plot | `plot_equity_curve(pnl)` |
| Consistent theming across plots | `viz = Visualizer(theme="dark"); viz.equity_curve(pnl)` |
| Batch export with metadata | `viz = Visualizer(export_path="./output"); viz.equity_curve(...)` |
| Extension (caching, custom themes) | Subclass `Visualizer` |

The class is **optional**—all functionality accessible via pure functions.

### Why Minimal Chart Types?

**Constraint:** Avoid premature feature creep.

**Rationale:**
- Start with high-value charts (P&L, signals, drawdown)
- Add complexity only when usage patterns emerge
- Placeholders (`plot_attribution`, `plot_exposures`) signal intent without commitment

**Future expansion criteria:**
1. Chart type used in >3 different contexts
2. Clear separation from computation logic
3. Non-trivial implementation (not just `px.line` wrapper)

## Integration Patterns

### Jupyter Notebooks

**Use case:** Exploratory analysis, iterative development.

```python
from aponyx.visualization import plot_equity_curve, plot_signal

# Inline display
plot_equity_curve(backtest.pnl).show()
plot_signal(cdx_vix_gap, threshold_lines=[-2, 2]).show()
```

**Design consideration:** `.show()` not called automatically to allow figure modification.

### Streamlit Dashboards

**Use case:** Interactive web interface, parameter exploration.

```python
import streamlit as st
from aponyx.visualization import Visualizer

viz = Visualizer()
st.plotly_chart(viz.equity_curve(pnl), use_container_width=True)

# Future: sidebar controls
theme = st.sidebar.selectbox("Theme", ["plotly_white", "plotly_dark"])
viz = Visualizer(theme=theme)
```

**Design consideration:** Returns figure objects compatible with `st.plotly_chart()`.

### Batch Reporting

**Use case:** Automated performance reports, regression testing.

```python
from aponyx.visualization import Visualizer

viz = Visualizer(export_path="./reports")
for strategy in strategies:
    viz.equity_curve(strategy.pnl)  # Auto-exports if path configured
```

**Design consideration:** Export logic in class, not functions (optional behavior).

## Technology Choices

### Why Plotly?

**Alternatives considered:** Matplotlib, Bokeh, Altair

**Decision factors:**
1. **Interactivity:** Hover tooltips, zoom, pan without configuration
2. **Streamlit compatibility:** First-class integration via `st.plotly_chart()`
3. **JSON serialization:** Figures serializable for caching/storage
4. **Consistent API:** Express and Graph Objects for simple/complex cases

**Trade-offs:**
- ❌ Larger dependency footprint than Matplotlib
- ❌ Steeper learning curve for custom layouts
- ✅ Better out-of-box experience for web interfaces
- ✅ No separate "interactive backend" configuration

### Why Plotly Express?

**Pattern:** Use `px.line()`, `px.area()` for simple charts; `go.Figure()` for customization.

**Rationale:**
- Express functions handle common cases cleanly
- Easy to upgrade to Graph Objects when needed
- Consistent with "simple by default" philosophy

**Example progression:**
```python
# Simple: Plotly Express
fig = px.line(x=dates, y=values)

# Customized: Graph Objects
fig = go.Figure()
fig.add_trace(go.Scatter(x=dates, y=values, line=dict(color="blue")))
fig.update_layout(template="plotly_white")
```

Current implementation uses Express; future complexity may require Graph Objects.

## Design Constraints

### What This Layer Does NOT Do

**Analytics / Computation**
- No Sharpe ratio calculations in plotting functions
- No signal generation or transformation
- No automatic metric annotations beyond labels

*Rationale:* Computation belongs in `evaluation.performance` or `models`. Visualization consumes pre-computed values.

**Styling / Theming**
- No custom color palettes (use Plotly defaults)
- No logo/branding overlays
- Minimal chart decoration

*Rationale:* Focus on information clarity. Custom styling can be added post-hoc if needed.

**Data Loading**
- No file I/O in plotting functions
- No registry lookups or automatic data fetching

*Rationale:* Caller provides data. Keeps viz layer stateless and testable.

### Performance Considerations

**Current approach:** Eager rendering (no lazy evaluation).

**Trade-off:**
- ✅ Simple implementation, predictable behavior
- ❌ May become slow for large datasets (>10k points per chart)

**Future optimization strategies:**
1. Downsampling for large time series (Plotly's built-in decimation)
2. Caching figure objects (via Visualizer class state)
3. Incremental updates (for real-time dashboards)

**Threshold:** Optimize when single chart generation >200ms.

### Testing Philosophy

**What we test:**
- Functions return valid `Figure` objects
- Calculations (cumulative sum, drawdown) are correct
- Parameters (titles, thresholds) applied properly
- Edge cases (NaN values, empty series) handled

**What we don't test:**
- Pixel-perfect rendering (Plotly's responsibility)
- Browser compatibility (Plotly's responsibility)
- Visual aesthetics (subjective, hard to automate)

**Rationale:** Focus on contract (API behavior) over implementation (pixel output).

## Extension Points

### Planned Additions

**Implementation Status:** These features are designed but not yet implemented. Function stubs exist in `plots.py` but raise `NotImplementedError`.

**Signal Attribution (`plot_attribution`)** — 🔜 Planned
- **Input:** `pd.DataFrame` with columns per signal's P&L contribution
- **Output:** Stacked area chart showing decomposition over time
- **Design question:** Absolute P&L or percentage contribution?
- **Blocker:** Requires backtest engine to track per-signal attribution
- **Current status:** Stub raises `NotImplementedError`

**Position Exposures (`plot_exposures`)** — 🔜 Planned
- **Input:** `pd.DataFrame` with notional, delta, DV01 columns
- **Output:** Multi-line chart with dual y-axes (notional vs Greeks)
- **Design question:** Single chart or separate panels?
- **Blocker:** Requires position tracking beyond simple long/short
- **Current status:** Stub raises `NotImplementedError`

**Multi-Panel Dashboard (`plot_dashboard`)** — 🔜 Planned
- **Input:** Complete backtest results dictionary
- **Output:** Plotly subplots (2×2 grid: equity, drawdown, signals, metrics)
- **Design question:** Fixed layout or configurable panels?
- **Implementation:** Use `plotly.subplots.make_subplots()`
- **Current status:** Stub raises `NotImplementedError`

### Streamlit Integration

**Status:** Placeholder implementation in `app.py`

The Streamlit dashboard (`visualization/app.py`) currently contains only a stub:

```python
import streamlit as st

st.write("Placeholder for Streamlit dashboard")
```

**Planned features:**
- Interactive parameter controls for backtests
- Multi-strategy comparison views
- Real-time signal monitoring (future consideration)

**Timeline:** Will be implemented after core plotting functions are complete.

### Extensibility Mechanisms

**Subclassing `Visualizer`:**
```python
class CustomVisualizer(Visualizer):
    def __init__(self):
        super().__init__(theme="plotly_dark")
        self.brand_color = "#1f77b4"
    
    def equity_curve(self, pnl):
        fig = super().equity_curve(pnl)
        fig.update_traces(line_color=self.brand_color)
        return fig
```

**Custom Themes:**
```python
# Define in visualizer.py
CUSTOM_THEMES = {
    "dark_mode": "plotly_dark",
    "minimal": "simple_white",
    "publication": "ggplot2",
}

viz = Visualizer(theme=CUSTOM_THEMES["publication"])
```

**Post-Processing Pattern:**
```python
fig = plot_equity_curve(pnl)
# Add annotations
fig.add_annotation(x="2024-06-01", y=100, text="Regime change")
# Add shape
fig.add_vrect(x0="2024-01-01", x1="2024-03-01", fillcolor="red", opacity=0.1)
```

## Open Design Questions

### 1. Caching Strategy

**Question:** Should `Visualizer` cache generated figures?

**Options:**
- **No caching:** Simple, stateless (current approach)
- **LRU cache:** Automatic memoization based on inputs
- **Explicit cache:** `viz.equity_curve(pnl, cache_key="strategy_1")`

**Considerations:**
- Caching requires hashable inputs (DataFrames aren't hashable)
- Figure objects are large (serialization overhead)
- Use case: redraw same chart with different themes

**Decision:** Defer until performance becomes an issue.

### 2. Export Utilities

**Question:** Should export be automatic or explicit?

**Current:** `Visualizer(export_path="./output")` enables auto-export (not yet implemented)

**Alternative:** Explicit export method: `viz.export_all(path="./output", format="html")`

**Considerations:**
- Auto-export: convenient but magical
- Explicit export: verbose but clear
- Batch reporting favors automation

**Decision:** Implement both—auto-export via constructor, explicit via method.

### 3. Real-Time Updates

**Question:** How to handle streaming data / live backtests?

**Challenge:** Plotly figures are static; updates require re-rendering.

**Options:**
- **Dash framework:** Real-time callbacks (heavy dependency)
- **Streamlit reruns:** Simple but full page refresh
- **Incremental updates:** Modify figure traces in-place

**Decision:** Not in scope for initial release. Revisit if real-time monitoring required.

## References

- **Plotly Documentation:** https://plotly.com/python/
- **Streamlit Integration:** https://docs.streamlit.io/library/api-reference/charts/st.plotly_chart
- **Project Standards:** `python_guidelines.md` (in same directory)
- **Signal Convention:** All signals in `models/` use consistent positive = long credit convention

---

**Last Updated:** October 31, 2025  
**Maintainer:** stabilefrisur
