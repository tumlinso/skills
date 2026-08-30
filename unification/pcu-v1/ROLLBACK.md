# PCU-V1 rollback inventory — Skills

Bootstrap rollback is by a new ordinary revert commit only. The original Skills commit is `35e7c5085a69cde8b74e8b18725ebceb69e4ea0c`; the original standalone Project Control commit is `603d48dbc4010487e74858541b5e3df50d770177`. Never reset, rebase, amend, squash, force-push, filter, or rewrite history.

The original live Codex registration is `coding-workflow`, stdio via `/home/tumlinson/.local/share/coding-workflow-mcp/venv/bin/python -m coding_workflow_mcp`, with the Skills root supplied by the registered compatibility environment variable. Restore it by re-registering that captured command only after removing a failed `project-control` registration; do not delete the candidate environment. Never run both registrations concurrently.

The original observer service unit comes from `/home/tumlinson/.config/systemd/user/project-control.service` (SHA-256 `ab4a5c371803698fdcbcf0e32282df481c6dc86478212d5a219d72adedcd6fd5`) and starts `/home/tumlinson/.local/state/project-control/venvs/project-control-0.3.1-603d48d/bin/project-control serve` in the standalone checkout. Restore that captured unit and executable path without deleting the candidate or standalone checkout. Preserve the existing endpoint and tunnel.

If a future submodule addition has not been committed, remove only the explicitly reviewed `project-control` gitlink and `.gitmodules` stanza with ordinary index/worktree operations; do not delete the standalone Project Control repository, copy `.git`, or run recursive cleanup. If committed, revert the adopting commit with a new revert commit.

Future implementation and release commits are rolled back with new `git revert` commits in dependency order. Todo history and UUIDs are never replaced. Compatibility packages, historical worktrees, stale sessions, and state files remain until separately authorized cleanup.
