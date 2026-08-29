"""Installed owner command for universal workflow recovery."""

from __future__ import annotations

import argparse
import json

from ._canonical import runtime_identity


def main() -> None:
    runtime_identity()
    from todo_orchestrator.service import Service
    from todo_orchestrator.workflow.admin import inspect_owner_recovery, run_owner_recovery
    from todo_orchestrator.workflow.recovery import RecoveryEngine

    parser = argparse.ArgumentParser(prog="coding-workflow-admin")
    commands = parser.add_subparsers(dest="command", required=True)
    recover = commands.add_parser("recover", help="inspect and safely recover workflow ownership")
    recover.add_argument("--repo", required=True)
    recover.add_argument("--task")
    recover.add_argument("--reason", required=True)
    recover.add_argument("--inspect-only", action="store_true")
    arguments = parser.parse_args()

    service = Service(arguments.repo, mutation_mode="self_debug")
    engine = RecoveryEngine(service.db, service.paths.repo_root, str(service.project["project_uuid"]))
    if arguments.inspect_only:
        print(json.dumps(inspect_owner_recovery(engine, arguments.task), sort_keys=True, separators=(",", ":")))
        return
    run_owner_recovery(
        engine,
        database_path=service.paths.db_file,
        reason=arguments.reason,
        task_id=arguments.task,
    )


if __name__ == "__main__":
    main()
