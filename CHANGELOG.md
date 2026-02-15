# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

### Fixed

### Changed
- Auto-include California stories in first-pass day assignment (#35)
- Code cleanup: structural refactors batch (#34)
- Replace tuple returns with dicts in main.py (#29)
- Split curator.py into data model and TUI layers (#28)
- Add tests for untested modules (#27)
- Replace print() with logging in library modules (#24)
- Standardize on httpx (remove requests dependency) (#23)
- Code cleanup: DRY consolidation batch (#33)
- Deduplicate LLM JSON parsing (xkcd.py) (#26)
- Consolidate week-targeting logic (DRY violation) (#25)
- Consolidate theme constants (DRY violation) (#20)
- Code cleanup: quick wins batch (#32)
- Extract duplicated unused-review loop in curate.py (#31)
- Remove dead get_selected_for_week() from xkcd.py (#30)
- Move inline imports to top-level (#22)
- Remove dead code in utils.py (#21)
- Fix scheduled PDF generation (cron doesn't run when machine is auto-stopped) (#19)
- Work with Asa to add a cartoon every day (#1)
- Add 'combine stories' feature to curation TUI (#10)
- Fix scheduled PDF generation (cron doesn't run when machine is auto-stopped) (#19)
- Work with Asa to add a cartoon every day (#1)
- Vet and consistently implement a two-mode approach (family vs friends) (#16)
- Extract or generate news highlight feature boxes (#5)
- Add PDF preview capability for review before printing (#12)
- Add print queue integration for automatic printing (#4)
- Generate tomorrow teaser content automatically (#7)
- news-fixed run doesn't prompt to refresh stale xkcd cache (#15)
- Allow LLM to suggest/adjust day themes based on week's content (#8)
- Improve 'By The Numbers' quality - reduce count and add generation rules (#2)
