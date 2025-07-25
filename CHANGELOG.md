# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2025-07-25

### Added
- New `Stocks` class for collection operations (search, list, filter)
- Smart search functionality with Thai/English auto-detection and improved matching algorithm
- Filtering capabilities by sector and market
- Enhanced listing with company details

### Changed
- API Refactoring: `Stock` class now focuses on individual stock operations
- Better organization: `Stocks` class handles collection operations

## [1.0.0] - TBD

### Changed
- All column names in the API have been updated to use snake_case
- Python compatibility updated to 3.11 and above for better performance and newer features

### Known Issues
- Google Colab users might have difficulty with Python 3.10 compatibility

[Unreleased]: https://github.com/ninyawee/thaifin/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/ninyawee/thaifin/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/ninyawee/thaifin/releases/tag/v1.0.0