# Changelog

All notable changes to Agentary will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Actions CI workflow (lint, type-check, test for backend and dashboard)
- Security workflow: Bandit, pip-audit, npm audit, gitleaks, CodeQL
- Dependabot configuration for pip, npm, GitHub Actions, and Docker
- Pull request template, bug report and feature request issue templates
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`
- Pre-commit hooks via `pre-commit` (ruff, black, isort, eslint, gitleaks)
- `.editorconfig` for consistent line endings and indentation
- Expanded `backend/pyproject.toml` with ruff, black, isort, mypy, coverage config

### Changed
- Pinned `requires-python = ">=3.13"` (was `>=3.10`) to match Docker base image
- Hardened `.gitignore`: explicit archive patterns, additional editor and OS files

## [0.2.0] - 2026-04-01

Major platform revamp — see `git log v0.1.0..v0.2.0` for full changes.

[Unreleased]: https://github.com/madhavcodez/agentary/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/madhavcodez/agentary/releases/tag/v0.2.0
