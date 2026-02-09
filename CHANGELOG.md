# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Fleet Hub dashboard with comprehensive monitoring features
- Fleet Overview tab with VPS cards and real-time metrics
- Applications tab with hierarchical VPS → Apps view
- Log Stream tab with search, filtering, and export
- Analytics tab with charts and error summaries
- Fleet-wide KPI dashboard (server count, CPU/memory averages, health status)
- Recent alerts panel with navigation
- Clickable app badges in Fleet Overview
- Expandable VPS cards with 24h metrics timeline
- Health check history display
- Chart.js visualizations (log volume, response time, health timeline)
- Log export functionality (JSON/CSV)
- Responsive design for mobile devices
- Port configuration documentation
- Comprehensive Fleet Hub documentation
- Contributing guidelines
- MIT License

### Changed
- Updated monitoring section in README with Fleet Hub features
- Improved health check URL display (non-clickable)
- Fixed port references to use CLI arguments instead of hardcoded values

### Fixed
- Log filtering now uses proper API parameters (vps_name, app_name)
- Port consistency across configuration files
- Tab switching to support programmatic navigation

## [0.3.0] - 2026-02-09

### Added
- Fleet monitoring integration with obs-agent
- PostgreSQL-backed metrics storage
- LogCore structured logging library
- Basic Fleet Hub dashboard (initial version)
- Database schema for metrics and logs
- Monitoring agent systemd services

### Changed
- Integrated monitoring into deploy-paradigm setup flow
- Updated documentation for monitoring features

## [0.2.0] - Earlier

### Added
- Docker deployment support
- Blue-green deployment strategy
- Rolling deployment strategy
- Smoke tests support
- Health check system

## [0.1.0] - Initial Release

### Added
- Core deployment system for Python applications
- Simple deployment strategy with symlink swapping
- Git-based deployment workflow
- Systemd and PM2 process manager support
- Zero-downtime deployments
- Automatic rollback on failure
- Configuration via deploy.yml

## Future Plans

### v0.4.0 (Next Release)
- [ ] Authentication system for Fleet Hub
- [ ] Data retention policies
- [ ] Alerting and notifications
- [ ] Node.js deployment support

### v0.5.0
- [ ] Real-time updates via WebSocket
- [ ] Custom dashboard configurations
- [ ] Advanced analytics features

### v1.0.0
- [ ] Production-hardened release
- [ ] Comprehensive test coverage
- [ ] Security audit
- [ ] Performance optimization

---

[Unreleased]: https://github.com/stygmund/observ/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/stygmund/observ/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/stygmund/observ/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/stygmund/observ/releases/tag/v0.1.0
