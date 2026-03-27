# Changelog

## [1.0.0] - 2026-03-27

### Added

- Initial release of ship plugin
- End-to-end shipping workflow: status → smart staging → commit → test → push → PR
- Smart staging with change cohesion analysis: auto-stages when all changes are related, groups and asks when mixed concerns detected
- Auto-generated conventional commit messages (no user confirmation needed)
- Auto-generated branch names when creating feature branches from default branch
- Auto-detection of repo's default branch via `gh repo view`
- Test runner auto-detection (npm, pytest, make, cargo, go)
- `--skip-tests` flag to bypass test phase
- `--no-pr` flag to skip PR creation
- `--draft` flag to create draft PRs
- Stop hook showing PR URL and CI status
- Secret file exclusion (.env, credentials, tokens, private keys)
