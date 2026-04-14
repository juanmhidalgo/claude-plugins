# Changelog

## [1.1.0] - 2026-04-14

### Added
- Request Copilot code review by default when creating PRs (`gh pr edit --add-reviewer @copilot`)
- `--skip-copilot-review` flag to opt out of automatic Copilot review
- Graceful fallback: warns if Copilot review is unavailable on the repo's plan

## [1.0.1] - 2026-03-30

### Fixed
- Skip test phase when only non-code files are staged (docs, config, markdown, etc.)
- Prevents unnecessary test suite runs for documentation-only changes

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
