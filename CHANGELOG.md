# Changelog

## [4.4.0] - 2026-06-04
### Features
- make `hm logs` tail all services by default if no service is specified
- implement line-aware log tailing to prevent interleaving of lines from different services
- improve output buffering and flushing for smoother real-time log viewing

## [4.3.0] - 2026-06-04
### Features
- add `--follow` flag to `hm up` to tail all logs after starting all services

## [4.2.0] - 2026-06-04
### Features
- add 'UPTIME' column to `hm ps` and dashboard for better service health monitoring
- implement short duration formatting (s, m, h, d) based on PID file lifecycle

## [4.1.0] - 2026-06-04
### Features
- implement persistent Inode-aware log tailing that survives service restarts and rotations
- add log truncation detection to reset tailing position automatically
- show last 2KB of log history when starting tailing
### Bug Fixes
- refactor `hm restart` to avoid redundant service stop calls and "not running" messages
- centralize service validation across all CLI commands
- fix Inode baseline refresh logic for reliable persistent tailing
### Other Changes
- update CLI usage documentation to include `--no-follow` for restart command

## [4.0.0] - 2026-05-31
### Other Changes
- update

## [3.0.0] - 2026-05-31

## [2.0.0] - 2026-05-30
### Bug Fixes
- consolidate configuration imports and update tests
### Other Changes
- achieve >90% test coverage across repository (#5)

## [1.0.0] - 2026-05-30
### Features
- implement production-grade Rich CLI experience
- implement advanced cli commands, root discovery, and log rotation
### Bug Fixes
- resolve code review issues from Rich UI PR
### Other Changes
- update
