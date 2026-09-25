# repository-mirroring Specification

## Purpose

Define the safe one-way mirror of the public GitHub `main` branch to the private GitLab `main` branch.

## ADDED Requirements

### Requirement: Main branch mirror is fast-forward only

The repository SHALL provide an automation that fetches `tbnhan/codex-lb` `refs/heads/main` over HTTPS and updates only `A.L.V.I.S/codex-lb` `refs/heads/main` over SSH. It MUST push an explicit refspec without force, tag following, or deletion behavior. It MUST fail when either branch is missing or when GitLab is not an ancestor of the selected GitHub commit. Equal commit IDs MUST be a successful no-op.

#### Scenario: GitHub main advances

- **WHEN** GitHub `main` advances and GitLab `main` is its ancestor
- **THEN** automation fast-forwards GitLab `main` to the selected GitHub commit
- **AND** verifies GitLab resolves to that exact commit after the push

#### Scenario: GitLab is ahead or diverged

- **WHEN** GitLab `main` is not an ancestor of GitHub `main`
- **THEN** automation fails without changing any GitLab ref

#### Scenario: Source or target main is missing

- **WHEN** either repository does not expose its required `main` ref
- **THEN** automation fails without creating or deleting a ref

### Requirement: Mirror credentials and invocation are constrained

The workflow MUST run only for repository `tbnhan/codex-lb` and ref `refs/heads/main`, with an explicit empty/minimal GitHub token permission set, serialized non-cancelling concurrency, a bounded hosted-runner timeout, and the `gitlab-main-mirror` environment. It MUST use only the `GITLAB_SYNC_SSH_KEY` environment secret, hold private key material in the process environment/SSH agent rather than a file, pin GitLab.com's SSH host key, and constrain SSH identity selection to the temporary agent. It MUST expose only result and commit IDs in the step summary.

#### Scenario: Manual dispatch is requested outside main or repository

- **WHEN** workflow dispatch originates outside `tbnhan/codex-lb` main
- **THEN** the mirror job is skipped or its shell guard fails before any remote mutation

#### Scenario: SSH host identity differs

- **WHEN** the GitLab SSH host key does not match the pinned key
- **THEN** SSH refuses the connection and the workflow fails closed

### Requirement: Unrelated refs remain unchanged

The automation MUST NOT update, create, or delete GitLab branches other than `main`, and MUST NOT update or create tags.

#### Scenario: Other source refs differ from destination refs

- **WHEN** GitHub and GitLab have different `dev` branches or tags
- **THEN** a successful `main` sync leaves the GitLab `dev` branch and all tags unchanged
