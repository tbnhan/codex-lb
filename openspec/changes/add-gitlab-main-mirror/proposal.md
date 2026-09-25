# Proposal: Mirror GitHub main to GitLab

## Goal

Provide a narrow GitHub Actions workflow that keeps the public GitHub repository's `main` available in the private GitLab project while preserving GitLab-only work safely.

## Scope

- Fetch `tbnhan/codex-lb` `refs/heads/main` freshly over HTTPS.
- Fast-forward only `A.L.V.I.S/codex-lb` `refs/heads/main` over SSH.
- Refuse missing refs, target-ahead/diverged history, wrong repository, and non-main invocations.
- Serialize runs without cancellation and verify the destination SHA after push.
- Keep credentials in a GitHub environment secret and a temporary SSH agent; publish no other refs.

## Non-goals

No GitLab-to-GitHub sync, tags, other branches, deletions, force pushes, deployment, credential creation, or GitHub/GitLab configuration writes are performed by this change.

## Acceptance

The workflow shell passes syntax validation and a disposable local bare-repository test suite covering fast-forward, equality, ahead/diverged histories, missing refs, repository/branch guards, and preservation of unrelated destination refs. Activation requires an operator to create a project-scoped GitLab write deploy key and configure the `gitlab-main-mirror` GitHub environment secret and protected-branch permission.
