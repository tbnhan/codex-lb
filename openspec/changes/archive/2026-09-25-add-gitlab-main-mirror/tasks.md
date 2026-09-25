# Tasks

- [x] Define the main-only, fast-forward-only operator contract.
- [x] Add the self-contained GitHub Actions workflow with strict SSH host verification and temporary-agent credentials.
- [x] Add regression coverage for fast-forward, equal-SHA no-op, target-ahead/diverged rejection, missing refs, invocation guards, and unrelated-ref preservation.
- [x] Validate workflow shell syntax, repository-configured Ruff lint/format, and the local bare-repository suite.
- [x] Publish the workflow, OpenSpec change, and regression test in PR [#1](https://github.com/tbnhan/codex-lb/pull/1), merged as `99a2c9c0753a455a19d742948b0912dd8647e9d0`.
- [x] Configure the approved GitLab deploy-key access and GitHub environment secret, then verify push run [36119173346](https://github.com/tbnhan/codex-lb/actions/runs/36119173346) and manual run [36119338154](https://github.com/tbnhan/codex-lb/actions/runs/36119338154).
- [x] Confirm the push run updates GitLab `main` to `99a2c9c0753a455a19d742948b0912dd8647e9d0`; confirm the manual run reports `already up to date` and both `main` refs remain equal at that SHA. GitLab `dev` remains `07712912fcae14407a31c0849aeb64ae70879bb7`; tags remain empty.
