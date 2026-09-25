# Proposal: Mirror GitHub main to GitLab

**Status:** Implemented and verified on 2026-09-25.

## Goal

Provide a narrow GitHub Actions workflow that keeps the public GitHub repository's `main` available in the private GitLab project while preserving GitLab-only work safely.

## Scope

- Fetch `tbnhan/codex-lb` `refs/heads/main` freshly over HTTPS.
- Fast-forward only `A.L.V.I.S/codex-lb` `refs/heads/main` over SSH.
- Refuse missing refs, target-ahead/diverged history, wrong repository, and non-main invocations.
- Serialize runs without cancellation and verify the destination SHA after push.
- Keep credentials in the `gitlab-main-mirror` GitHub environment secret and a temporary SSH agent; publish no other refs.

## Non-goals

No GitLab-to-GitHub sync, tags, other branches, deletions, force pushes, or deployment are included.

## Acceptance

The local bare-repository regression suite covers fast-forward, equality, target-ahead/diverged history, missing refs, repository/branch guards, and preservation of unrelated refs. The workflow was published and both push run [36119173346](https://github.com/tbnhan/codex-lb/actions/runs/36119173346) and manual run [36119338154](https://github.com/tbnhan/codex-lb/actions/runs/36119338154) succeeded. The manual run reported `already up to date`; GitHub and GitLab `main` both resolved to `99a2c9c0753a455a19d742948b0912dd8647e9d0`. GitLab `dev` remained at `07712912fcae14407a31c0849aeb64ae70879bb7`, and no tags were present.
