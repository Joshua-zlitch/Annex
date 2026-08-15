# ANNEX Governance

This document describes how the ANNEX project ("Learn Before You Believe") is
governed. It is intentionally lightweight: this is a small project with a small
core team, and the goal is to stay easy to join and easy to contribute to.

## License

ANNEX is licensed under the MIT License. By contributing, you agree that your
contributions are licensed under the same terms. (See `LICENSE`.)

## Roles

### Maintainers

Maintainers are the people who own the repository and have write access. They
are responsible for:

- Reviewing and merging pull requests.
- Triaging issues and steering the roadmap.
- Enforcing the [Code of Conduct](CODE_OF_CONDUCT.md).
- Releasing versions.

### Contributors

Anyone who submits an issue, a pull request, documentation, or feedback is a
contributor. Contributors have no write access but their input shapes the
project. Good contributions are the fastest path to becoming a maintainer.

## Decision-making

- **Day-to-day decisions** (bug fixes, small features, documentation) are made by
  the maintainers, ideally with consensus among the contributors involved.
- **Roadmap and architectural decisions** are discussed in issues. Where a
  decision affects the public API, the security model, or the architecture
  boundaries, it is documented in the issue thread before implementation.
- Disagreements are resolved by discussion first. If consensus cannot be
  reached, the final call rests with the maintainers.

## Adding and removing maintainers

- A contributor can be invited to become a maintainer when they have a history
  of quality contributions and the existing maintainers agree.
- A maintainer can step down at any time, or be removed by the other maintainers
  for sustained Code of Conduct violations or inactivity over a long period.

## Roadmap

The project currently delivers the Phase 1 backend foundation described in
`README.md`. Planned later phases (video/audio/document/URL ingestion,
polling/webhooks, a durable queue, multi-model verification) are tracked in
issues and discussed openly. Anyone can propose roadmap items by opening an
issue.

## Community norms

- Be respectful: follow the [Code of Conduct](CODE_OF_CONDUCT.md).
- Stay on topic in issues and pull requests.
- Credit external work (models, datasets, code, research) used in the project.

## Contact

For governance questions, security reports (see `SECURITY.md`), or anything that
should not go into a public issue, reach out to the maintainers directly.

## Changes to this document

Proposed changes to this governance document are themselves governed by this
process: open an issue or pull request, discuss it, and let the maintainers
ratify it.