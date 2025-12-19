# Feature Specification: Data Channel Separation

**Feature Branch**: `010-data-channel-separation`  
**Created**: December 19, 2025  
**Status**: Draft  
**Input**: Separate indicator, PnL, and display data requirements with channel-based security catalog

## Problem Statement

The current data layer conflates three distinct data requirements:

1. **Indicator computation** - fields needed to calculate signals (typically spread)
2. **PnL calculation** - fields needed for backtest returns (spread-DV01 or price-return)
3. **Display/analysis** - fields shown in evaluation and visualization (typically spread)

This creates challenges when securities require data from multiple Bloomberg tickers or when different consumers need different data representations. For example:
- CDX indices have separate tickers for price and spread data
- ETFs provide spread via a specific field on the price ticker
- Indicators may need spread data while PnL uses price returns

## User Scenarios & Testing

### User Story 1 - Compute Indicator from Spread Data (Priority: P1)

As a researcher, I want indicators to automatically use spread data for CDX and ETF securities so that signal computations reflect credit risk metrics rather than price levels.

**Why this priority**: Indicator computation is the core use case - without correct data channel resolution, all downstream analysis is compromised.

**Independent Test**: Run a workflow with `cdx_hy_5y` security and verify the indicator transformation receives spread values (300-500 bps range typical), not price values (90-105 range typical).

**Acceptance Scenarios**:

1. **Given** a security catalog with CDX HY 5Y having spread channel defined, **When** computing indicator transformation, **Then** the data layer provides spread values from the correct Bloomberg ticker
2. **Given** an ETF security with spread available via `YAS_ISPREAD` field, **When** computing indicator transformation, **Then** the data layer extracts spread from the correct field on the primary ticker
3. **Given** a VIX security with only level data, **When** computing indicator transformation, **Then** the data layer provides level values as expected

---

### User Story 2 - Execute Backtest with Appropriate PnL Method (Priority: P1)

As a researcher, I want the backtest engine to automatically select the correct data channel based on the security's quote type so that P&L calculations use the appropriate return methodology.

**Why this priority**: Accurate P&L calculation is essential for strategy evaluation - using wrong data channel produces meaningless results.

**Independent Test**: Run backtest on a spread-quoted CDX product and verify DV01-based P&L calculation; run backtest on a price-quoted ETF and verify price-return P&L calculation.

**Acceptance Scenarios**:

1. **Given** a security with `quote_type: spread`, **When** running backtest, **Then** the engine uses spread data and DV01-based P&L calculation
2. **Given** a security with `quote_type: price`, **When** running backtest, **Then** the engine uses price data and price-return P&L calculation
3. **Given** a security with spread channel but `quote_type: price`, **When** running backtest, **Then** the engine uses price data for P&L (ignoring spread availability)

---

### User Story 3 - Display Analysis in Spread Terms (Priority: P2)

As a researcher reviewing results, I want evaluation and visualization outputs to display data in spread terms (for credit instruments) so that I can interpret results in familiar credit market units.

**Why this priority**: Consistent display improves interpretability but doesn't affect calculation correctness.

**Independent Test**: Generate suitability report for a CDX product and verify spread values are displayed, not prices.

**Acceptance Scenarios**:

1. **Given** a CDX security with spread channel available, **When** generating evaluation report, **Then** spread values are displayed in basis points
2. **Given** an ETF security with spread channel available, **When** generating visualization, **Then** spread values are used for charts by default
3. **Given** a workflow with `display_channel: price` override, **When** generating visualization, **Then** price values are used instead of spread

---

### User Story 4 - Unified Data Fetch Hiding Multi-Ticker Complexity (Priority: P2)

As a developer working with the data layer, I want to fetch security data without knowing which Bloomberg tickers are involved so that consumer code remains simple and maintainable.

**Why this priority**: Abstraction simplifies consumer code but is infrastructure improvement rather than user-facing feature.

**Independent Test**: Call `fetch_security_data("cdx_hy_5y", channels=["price", "spread"])` and verify a single DataFrame is returned with both columns, regardless of underlying ticker structure.

**Acceptance Scenarios**:

1. **Given** a security requiring two Bloomberg tickers for different channels, **When** fetching all channels, **Then** data layer returns a single DataFrame with all channels merged by date
2. **Given** a security with channels on same ticker but different fields, **When** fetching specific channel, **Then** data layer extracts correct field
3. **Given** FileSource instead of BloombergSource, **When** fetching security data, **Then** same interface works with local parquet files

---

### User Story 5 - Validate Security Configuration (Priority: P3)

As a system administrator, I want the system to validate security configurations at startup so that misconfigured securities are caught early rather than causing runtime failures.

**Why this priority**: Validation improves reliability but is defensive programming rather than core functionality.

**Independent Test**: Create a security with `quote_type: spread` but missing `dv01_per_million` and verify validation error on catalog load.

**Acceptance Scenarios**:

1. **Given** a security with `quote_type: spread` but no `dv01_per_million`, **When** loading security catalog, **Then** validation fails with clear error message
2. **Given** a workflow requesting spread channel from security without spread defined, **When** starting workflow, **Then** clear error message identifies missing channel
3. **Given** valid security catalog, **When** loading at startup, **Then** all securities pass validation

---

### Edge Cases

- What happens when a security defines a channel but Bloomberg returns no data for that ticker?
- How does the system handle Bloomberg API failures for one ticker when multiple tickers are needed?
- What happens when FileSource parquet file is missing a column that the catalog says should exist?
- How does the system behave when `display_channel` override specifies a channel not defined for the security?

## Requirements

### Functional Requirements

- **FR-001**: System MUST support defining multiple data channels per security in the catalog
- **FR-002**: System MUST resolve channel requests to the correct ticker/field combination based on catalog configuration
- **FR-003**: System MUST merge data from multiple Bloomberg tickers into a single DataFrame when a security requires it
- **FR-004**: System MUST use instrument type defaults to determine which channel to use for indicator computation
- **FR-005**: System MUST use security's `quote_type` to determine which channel to use for P&L calculation
- **FR-006**: System MUST use instrument type defaults to determine which channel to use for display purposes
- **FR-007**: System MUST allow workflow-level override of display channel
- **FR-008**: System MUST validate that `dv01_per_million` is present when `quote_type: spread`
- **FR-009**: System MUST provide clear error messages when requested channels are not available
- **FR-010**: FileSource MUST work with the same catalog structure, validating channel columns exist in parquet files

### Key Entities

- **Security**: Tradeable instrument with primary ticker, data channels, quote type, and microstructure parameters
- **Data Channel**: Named data stream (spread, price, level) with optional explicit ticker and required field mapping
- **Instrument Type**: Category (cdx, etf, vix) with default channel preferences for indicator and display purposes
- **Usage Purpose**: Context (indicator, pnl, display) that determines which channel is selected

## Success Criteria

### Measurable Outcomes

- **SC-001**: All existing workflows produce identical backtest results after migration (regression test passes)
- **SC-002**: Indicator transformations receive correct channel data (spread for CDX/ETF, level for VIX) without code changes to indicator functions
- **SC-003**: Multi-ticker securities (CDX HY) fetch all channels in a single `fetch_security_data` call
- **SC-004**: Security catalog validation catches 100% of invalid configurations at load time
- **SC-005**: Consumer code (indicators, backtest, evaluation) requires zero knowledge of underlying Bloomberg ticker structure

## Assumptions

- Bloomberg API supports fetching multiple fields from a single ticker in one call
- All securities of the same instrument type share the same default channel preferences
- FileSource parquet files will be regenerated to include all required channel columns
- Existing `quote_type` field semantics remain unchanged (spread vs price for P&L method)
