# Changelog

All notable changes to this project will be documented in this file.

## [v4.3.1] - 2026-02-25 "The Data Integrity Fix"

### Fixed

- **Zero-Score Bug**: Resolved issue where technical scores and AI probabilities displayed as 0.0% due to binary blob storage in SQLite.
- **Smart Versioning**: Updated candidate filtering to prefer the most representative model version (highest record count).

### Added

- **Data Integrity Logic**: Explicit type casting for numpy scalars in `core/data.py` to ensure native float storage.
- **Migration Utilities**: Added `scripts/migrate_scores_robust.py` for existing database repair.

## [v4.3.0] - 2026-02-24 "The Superpowers Infrastructure Upgrade"

### Added

- **AI Brain Template v3.4.1**: Upgraded to "Antigravity Superpowers Edition" for enhanced governance.
- **Engineering Constitution**: Introduced a formal "Constitution Layer" for AI-Project alignment.
- **Superpowers Logic**: Integrated structured `/bootstrap` and `/plan` workflows into the development lifecycle.
- **Collaboration Guardrails**: Standardized Pull Request and Testing protocols.

## [v4.2.0] - 2026-02-14 "The Stability & Automation Update"

### Added

- **CI Integration**: Added GitHub Actions workflow for automated `pytest`.
- **Centralized Logging**: New `core/logger.py` with rotation and alert triggers.
- **Modular AI Core**: Refactored `core/ai.py` into a package (`common.py`, `trainer.py`, `predictor.py`).

### Fixed

- **Logging Consistency**: Unified logging across all core and backend modules.

## [v4.1.0] - 2026-02-14 "The Sniper Optimizer"

### Added

- **AI Model Versioning**: Added `Model Version Switcher` in Backtest UI to compare historical models.
- **Persistent Scoring**: V2 scores are now pre-calculated and stored in DB for <100ms API response.
- **Refined Backtest**: "Time Machine" simulation now supports selecting specific model versions.

### Changed

- **Data Pipeline**: Fully optimized for Taiwan Stock Market (TWSE).
- **Documentation**: Major overhaul of system docs (Architecture, Contributing, etc.).
- **Cleanup**: Removed legacy `stock_data.db` and old HTML files.

## [v2.1.0] - 2026-02-13 "The Market Pulse"

### Added

- **Global Search**: API endpoint `/api/search` for universal stock queries.
- **Market Pulse Chart**: Visualized 30-day market temperature and AI sentiment.
- **Interactive Backtest**: Clickable rows in backtest results to view details.

### Fixed

- **Search Scope**: Fixed issue where search was limited to local ranking list.
- **UI Bugs**: Fixed `handleSearch` scope and state dependency regressions.

## [v2.0.0] - 2026-02-12 "The React Pivot"

### Added

- **Modern Frontend**: Replaced vanilla JS with React + Vite + Tailwind.
- **Glassmorphism UI**: New dark mode design with translucent components.
- **New Components**: StockList, SniperCard, ChartContainer.

## [v1.0.0] - Initial Release

- Basic Technical Analysis Engine.
- Random Forest AI Model.
- Simple HTML Dashboard.
