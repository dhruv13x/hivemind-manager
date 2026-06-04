# Changelog

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
