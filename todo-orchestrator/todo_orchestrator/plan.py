"""Machine-readable v2 plan validation, diffing, scaffolding, and transactional upsert."""

from __future__ import annotations

import json
import sqlite3
from collections import deque
from pathlib import Path
from typing import Any

from . import SCHEMA_VERSION
from .config import utc_now
from .git_state import canonical_relative
from .graph import validate_acyclic
from .models import TodoError

TASK_KINDS = {"epic", "workstream", "task", "integration", "integration_task", "validation", "validation_task"}
PARALLEL_POLICIES = {"parallel_safe", "serial", "project_exclusive", "integration_exclusive"}
DEPENDENCY_TYPES = {"task", "checkpoint", "interface", "barrier", "decision"}
DISPOSITIONS = {"implemented", "validated", "evaluated_not_promoted", "no_change_required", "superseded", "failed"}


def load_plan(path: str | Path) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TodoError("invalid_plan_json", str(exc)) from exc
    if not isinstance(data, dict):
        raise TodoError("invalid_plan", "Plan root must be a JSON object")
    return data


def validate_plan(data: dict[str, Any], repo_root: Path | None = None) -> dict[str, object]:
    errors: list[str] = []

    def validate_path(value: object, label: str, *, allow_root: bool = False) -> None:
        try:
            if allow_root and str(value) == ".":
                return
            if repo_root:
                canonical_relative(repo_root, str(value))
            elif Path(str(value)).is_absolute() or ".." in Path(str(value)).parts:
                raise ValueError(value)
        except Exception:
            errors.append(f"{label} has unsafe repository path: {value}")
    if int(data.get("schema_version", 0)) != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        errors.append("tasks must be an array")
        tasks = []
    ids: list[str] = []
    for index, task in enumerate(tasks):
        if not isinstance(task, dict) or not task.get("id") or not task.get("title"):
            errors.append(f"tasks[{index}] requires id and title")
            continue
        task_id = str(task["id"])
        ids.append(task_id)
        if task.get("kind", "task") not in TASK_KINDS:
            errors.append(f"task {task_id} has unsupported kind")
        if task.get("parallel_policy", "serial") not in PARALLEL_POLICIES:
            errors.append(f"task {task_id} has unsupported parallel_policy")
        scope = task.get("scope", {})
        for field in ("exclusive_paths", "read_paths", "forbidden_paths"):
            for value in scope.get(field, []):
                validate_path(value, f"task {task_id} {field}")
        for dependency in task.get("depends_on", []):
            if dependency.get("type") not in DEPENDENCY_TYPES:
                errors.append(f"task {task_id} has unsupported dependency type {dependency.get('type')}")
            if dependency.get("type") == "decision" and dependency.get("operator", "equals") not in {"equals", "in"}:
                errors.append(f"task {task_id} has unsafe decision operator")
        allowed = task.get("result_policy", {}).get("allowed_dispositions", [])
        invalid = set(allowed) - DISPOSITIONS
        if invalid:
            errors.append(f"task {task_id} has invalid dispositions: {sorted(invalid)}")
    duplicates = sorted({task_id for task_id in ids if ids.count(task_id) > 1})
    if duplicates:
        errors.append(f"duplicate task IDs: {duplicates}")
    task_ids = set(ids)
    interfaces = data.get("interfaces", []) if isinstance(data.get("interfaces", []), list) else []
    barriers = data.get("barriers", []) if isinstance(data.get("barriers", []), list) else []
    decisions = data.get("decisions", []) if isinstance(data.get("decisions", []), list) else []
    invariants = data.get("invariants", []) if isinstance(data.get("invariants", []), list) else []
    locks = data.get("locks", []) if isinstance(data.get("locks", []), list) else []
    resource_classes = data.get("resource_classes", []) if isinstance(data.get("resource_classes", []), list) else []
    checkpoint_ids = [str(item["id"]) for task in tasks if isinstance(task, dict) for item in task.get("checkpoints", []) if isinstance(item, dict) and item.get("id")]
    gate_ids = [str(item["id"]) for task in tasks if isinstance(task, dict) for item in task.get("gates", []) if isinstance(item, dict) and item.get("id")]
    interface_ids = [str(item["id"]) for item in interfaces if isinstance(item, dict) and item.get("id")]
    barrier_ids = [str(item["id"]) for item in barriers if isinstance(item, dict) and item.get("id")]
    decision_ids = [str(item["id"]) for item in decisions if isinstance(item, dict) and item.get("id")]
    invariant_ids = [str(item["id"]) for item in invariants if isinstance(item, dict) and item.get("id")]
    lock_names = [str(item["name"]) for item in locks if isinstance(item, dict) and item.get("name")]
    resource_class_ids = [str(item["id"]) for item in resource_classes if isinstance(item, dict) and item.get("id")]
    resource_instance_ids = [str(instance["id"]) for item in resource_classes if isinstance(item, dict) for instance in item.get("instances", []) if isinstance(instance, dict) and instance.get("id")]

    for label, values in (
        ("checkpoint", checkpoint_ids), ("gate", gate_ids), ("interface", interface_ids),
        ("barrier", barrier_ids), ("decision", decision_ids), ("invariant", invariant_ids),
        ("lock", lock_names), ("resource class", resource_class_ids), ("resource instance", resource_instance_ids),
    ):
        repeated = sorted({value for value in values if values.count(value) > 1})
        if repeated:
            errors.append(f"duplicate {label} IDs: {repeated}")

    known_checkpoints, known_interfaces = set(checkpoint_ids), set(interface_ids)
    known_barriers, known_decisions = set(barrier_ids), set(decision_ids)
    known_invariants, known_locks = set(invariant_ids), set(lock_names)
    known_resource_classes, known_resource_instances = set(resource_class_ids), set(resource_instance_ids)

    def selector_known(selector: object) -> bool:
        value = str(selector)
        return (value.endswith(":any") and value[:-4] in known_resource_classes) or value in known_resource_instances

    for interface in interfaces:
        if not isinstance(interface, dict) or not interface.get("id") or interface.get("owner_task_id") not in task_ids:
            errors.append(f"interface {interface.get('id') if isinstance(interface, dict) else '?'} requires a known owner_task_id")
        if isinstance(interface, dict):
            for value in interface.get("contract_paths", []):
                validate_path(value, f"interface {interface.get('id')} contract")
    for task in tasks:
        if not isinstance(task, dict) or not task.get("id"):
            continue
        task_id = str(task["id"])
        for invariant_id in task.get("invariants", []):
            if invariant_id not in known_invariants:
                errors.append(f"task {task_id} references unknown invariant {invariant_id}")
        for lock_name in task.get("scope", {}).get("shared_locks", []):
            if lock_name not in known_locks:
                # Shared locks may be declared inline and are created on apply.
                known_locks.add(str(lock_name))
        for dependency in task.get("depends_on", []):
            kind = dependency.get("type")
            reference = {
                "task": (dependency.get("task_id"), task_ids),
                "checkpoint": (dependency.get("checkpoint_id"), known_checkpoints),
                "interface": (dependency.get("interface_id"), known_interfaces),
                "barrier": (dependency.get("barrier_id"), known_barriers),
                "decision": (dependency.get("decision_id"), known_decisions),
            }.get(kind)
            if reference and (not reference[0] or reference[0] not in reference[1]):
                errors.append(f"task {task_id} has unknown {kind} dependency {reference[0]}")
        for consumed in task.get("consumes_interfaces", []):
            if consumed.get("id") not in known_interfaces:
                errors.append(f"task {task_id} consumes unknown interface {consumed.get('id')}")
        for checkpoint in task.get("checkpoints", []):
            for published in checkpoint.get("publishes_interfaces", []):
                if published.get("id") not in known_interfaces:
                    errors.append(f"checkpoint {checkpoint.get('id')} publishes unknown interface {published.get('id')}")
        for gate in task.get("gates", []):
            if gate.get("type") in {"command", "benchmark", "json_predicate"} and (not isinstance(gate.get("argv"), list) or not gate.get("argv")):
                errors.append(f"gate {gate.get('id')} requires a non-empty argv array")
            if gate.get("checkpoint_id") and gate.get("checkpoint_id") not in known_checkpoints:
                errors.append(f"gate {gate.get('id')} references unknown checkpoint {gate.get('checkpoint_id')}")
            for field in ("cwd", "path", "metric_file"):
                if gate.get(field):
                    validate_path(gate[field], f"gate {gate.get('id')} {field}", allow_root=field == "cwd")
            for value in gate.get("input_paths", []):
                validate_path(value, f"gate {gate.get('id')} input")
            for selector in gate.get("resources", []):
                if not selector_known(selector):
                    errors.append(f"gate {gate.get('id')} references unknown resource selector {selector}")
        for request in task.get("resource_requests", []):
            if not selector_known(request.get("selector")):
                errors.append(f"task {task_id} references unknown resource selector {request.get('selector')}")
        for artifact in task.get("produced_artifacts", []):
            if artifact.get("path"):
                validate_path(artifact["path"], f"task {task_id} artifact")
    valid_requirement_types = {"task", "validation_task", "checkpoint", "interface", "gate"}
    requirement_sets = {"task": task_ids, "validation_task": task_ids, "checkpoint": known_checkpoints, "interface": known_interfaces, "gate": set(gate_ids)}
    for barrier in barriers:
        if not isinstance(barrier, dict) or not barrier.get("id"):
            errors.append("barriers require an id")
            continue
        if barrier.get("mode", "all") not in {"all", "quorum"}:
            errors.append(f"barrier {barrier['id']} has unsupported mode")
        requirements = barrier.get("requirements", [])
        if not requirements:
            errors.append(f"barrier {barrier['id']} requires at least one requirement")
        if barrier.get("mode") == "quorum" and not (isinstance(barrier.get("quorum"), int) and 1 <= barrier["quorum"] <= len(requirements)):
            errors.append(f"barrier {barrier['id']} has invalid quorum")
        for requirement in requirements:
            kind, entity_id = requirement.get("type"), requirement.get("id")
            if kind not in valid_requirement_types or entity_id not in requirement_sets.get(kind, set()):
                errors.append(f"barrier {barrier['id']} has unknown {kind} requirement {entity_id}")
    if not errors:
        try:
            validate_acyclic(tasks)
        except TodoError as exc:
            errors.append(exc.message)
    if errors:
        raise TodoError("plan_validation_failed", "Plan validation failed", details={"errors": errors})
    return {
        "valid": True,
        "task_count": len(tasks),
        "checkpoint_count": sum(len(task.get("checkpoints", [])) for task in tasks),
        "gate_count": sum(len(task.get("gates", [])) for task in tasks),
        "barrier_count": len(data.get("barriers", [])),
        "interface_count": len(data.get("interfaces", [])),
    }


def _task_order(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {str(task["id"]): task for task in tasks}
    pending = deque(sorted(by_id))
    ordered: list[dict[str, Any]] = []
    inserted: set[str] = set()
    while pending:
        task_id = pending.popleft()
        task = by_id[task_id]
        parent = task.get("parent_id")
        if parent and str(parent) not in inserted:
            pending.append(task_id)
            continue
        ordered.append(task)
        inserted.add(task_id)
    return ordered


def _clear_task_details(conn: sqlite3.Connection, task_id: str) -> None:
    for table in ("task_dependencies", "ownership_scopes", "task_locks", "task_invariants", "task_artifacts", "resource_requests"):
        conn.execute(f"DELETE FROM {table} WHERE task_id=?", (task_id,))


def apply_plan(conn: sqlite3.Connection, data: dict[str, Any], repo_root: Path, revision: int) -> dict[str, object]:
    validate_plan(data, repo_root)
    now = utc_now()
    for lock in data.get("locks", []):
        conn.execute(
            "INSERT INTO named_locks(name,capacity,metadata_json) VALUES(?,?,?) ON CONFLICT(name) DO UPDATE SET capacity=excluded.capacity,metadata_json=excluded.metadata_json",
            (lock["name"], int(lock.get("capacity", 1)), json.dumps(lock.get("metadata", {}), sort_keys=True)),
        )
    for decision in data.get("decisions", []):
        conn.execute(
            "INSERT INTO decisions(id,title,value_json,allowed_json,updated_at,revision) VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET title=excluded.title,value_json=excluded.value_json,allowed_json=excluded.allowed_json,updated_at=excluded.updated_at,revision=excluded.revision",
            (
                decision["id"],
                decision.get("title", decision["id"]),
                json.dumps(decision.get("value")) if "value" in decision else None,
                json.dumps(decision.get("allowed", []), sort_keys=True),
                now,
                revision,
            ),
        )
    for invariant in data.get("invariants", []):
        conn.execute(
            "INSERT INTO invariants(id,rule,scope_json,severity,enforcement) VALUES(?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET rule=excluded.rule,scope_json=excluded.scope_json,severity=excluded.severity,enforcement=excluded.enforcement",
            (invariant["id"], invariant["rule"], json.dumps(invariant.get("scope", {}), sort_keys=True), invariant.get("severity", "error"), invariant.get("enforcement")),
        )
    tasks = _task_order(data.get("tasks", []))
    for task in tasks:
        task_id = str(task["id"])
        existing = conn.execute("SELECT created_at,status,result FROM tasks WHERE id=?", (task_id,)).fetchone()
        status = task.get("status", existing["status"] if existing else "planned")
        result = task.get("result", existing["result"] if existing else None)
        conn.execute(
            "INSERT INTO tasks(id,parent_id,kind,title,objective,status,priority,tags_json,parallel_policy,result,next_action,result_policy_json,notes,created_at,updated_at,version,revision) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?) "
            "ON CONFLICT(id) DO UPDATE SET parent_id=excluded.parent_id,kind=excluded.kind,title=excluded.title,objective=excluded.objective,status=excluded.status,priority=excluded.priority,tags_json=excluded.tags_json,parallel_policy=excluded.parallel_policy,result=excluded.result,next_action=excluded.next_action,result_policy_json=excluded.result_policy_json,notes=excluded.notes,updated_at=excluded.updated_at,version=tasks.version+1,revision=excluded.revision",
            (
                task_id,
                task.get("parent_id"),
                task.get("kind", "task"),
                task["title"],
                task.get("objective", ""),
                status,
                int(task.get("priority", 0)),
                json.dumps(task.get("tags", []), sort_keys=True),
                task.get("parallel_policy", "serial"),
                result,
                task.get("next_action", ""),
                json.dumps(task.get("result_policy", {}), sort_keys=True),
                task.get("notes", ""),
                existing["created_at"] if existing else now,
                now,
                revision,
            ),
        )
        _clear_task_details(conn, task_id)
        scope = task.get("scope", {})
        mapping = {"exclusive_paths": "exclusive", "read_paths": "read", "forbidden_paths": "forbidden"}
        for field, mode in mapping.items():
            for value in scope.get(field, []):
                conn.execute("INSERT INTO ownership_scopes(task_id,mode,path) VALUES(?,?,?)", (task_id, mode, canonical_relative(repo_root, str(value))))
        for lock_name in scope.get("shared_locks", []):
            conn.execute("INSERT OR IGNORE INTO named_locks(name,capacity,metadata_json) VALUES(?,1,'{}')", (lock_name,))
            conn.execute("INSERT INTO task_locks(task_id,lock_name,phase) VALUES(?,?,?)", (task_id, lock_name, "manual"))
        for lock in task.get("claim_locks", []):
            conn.execute("INSERT OR IGNORE INTO named_locks(name,capacity,metadata_json) VALUES(?,1,'{}')", (lock,))
            conn.execute("INSERT INTO task_locks(task_id,lock_name,phase) VALUES(?,?,?)", (task_id, lock, "claim"))
        for invariant_id in task.get("invariants", []):
            conn.execute("INSERT INTO task_invariants(task_id,invariant_id) VALUES(?,?)", (task_id, invariant_id))
        for artifact in task.get("produced_artifacts", []):
            conn.execute("INSERT INTO task_artifacts(task_id,kind,path) VALUES(?,?,?)", (task_id, artifact.get("kind", "artifact"), canonical_relative(repo_root, artifact["path"])))

    for interface in data.get("interfaces", []):
        paths = [canonical_relative(repo_root, value) for value in interface.get("contract_paths", [])]
        conn.execute(
            "INSERT INTO interfaces(id,owner_task_id,state,version,contract_paths_json,content_hash,frozen_at,revised_at,revision) VALUES(?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET owner_task_id=excluded.owner_task_id,state=excluded.state,version=excluded.version,contract_paths_json=excluded.contract_paths_json,revision=excluded.revision",
            (interface["id"], interface["owner_task_id"], interface.get("state", "draft"), str(interface.get("version", "0")), json.dumps(paths), interface.get("content_hash"), interface.get("frozen_at"), interface.get("revised_at"), revision),
        )
        conn.execute("DELETE FROM interface_consumers WHERE interface_id=?", (interface["id"],))

    for task in tasks:
        task_id = str(task["id"])
        for dependency in task.get("depends_on", []):
            kind = dependency["type"]
            condition = {key: value for key, value in dependency.items() if key in {"operator", "value", "state", "version", "dispositions"}}
            conn.execute(
                "INSERT INTO task_dependencies(task_id,type,prerequisite_task_id,checkpoint_id,interface_id,barrier_id,decision_id,condition_json) VALUES(?,?,?,?,?,?,?,?)",
                (
                    task_id,
                    kind,
                    dependency.get("task_id") if kind == "task" else None,
                    dependency.get("checkpoint_id") if kind == "checkpoint" else None,
                    dependency.get("interface_id") if kind == "interface" else None,
                    dependency.get("barrier_id") if kind == "barrier" else None,
                    dependency.get("decision_id") if kind == "decision" else None,
                    json.dumps(condition, sort_keys=True),
                ),
            )
        for consumed in task.get("consumes_interfaces", []):
            conn.execute(
                "INSERT OR REPLACE INTO interface_consumers(interface_id,task_id,required_state,required_version) VALUES(?,?,?,?)",
                (consumed["id"], task_id, consumed.get("required_state", "frozen"), consumed.get("required_version")),
            )
        for checkpoint in task.get("checkpoints", []):
            existing_checkpoint = conn.execute(
                "SELECT state,reached_at,revoked_at FROM checkpoints WHERE id=?", (checkpoint["id"],)
            ).fetchone()
            checkpoint_state = checkpoint.get(
                "state", existing_checkpoint["state"] if existing_checkpoint else "pending"
            )
            reached_at = existing_checkpoint["reached_at"] if existing_checkpoint else None
            revoked_at = existing_checkpoint["revoked_at"] if existing_checkpoint else None
            if not existing_checkpoint or checkpoint_state != existing_checkpoint["state"]:
                if checkpoint_state == "reached":
                    reached_at, revoked_at = now, None
                elif checkpoint_state == "revoked":
                    revoked_at = now
                elif checkpoint_state == "pending":
                    reached_at, revoked_at = None, None
            conn.execute(
                "INSERT INTO checkpoints(id,task_id,title,state,metadata_json,reached_at,revoked_at,revision) VALUES(?,?,?,?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET task_id=excluded.task_id,title=excluded.title,state=excluded.state,metadata_json=excluded.metadata_json,reached_at=excluded.reached_at,revoked_at=excluded.revoked_at,revision=excluded.revision",
                (checkpoint["id"], task_id, checkpoint.get("title", checkpoint["id"]), checkpoint_state, json.dumps(checkpoint.get("metadata", {}), sort_keys=True), reached_at, revoked_at, revision),
            )
            conn.execute("DELETE FROM checkpoint_interfaces WHERE checkpoint_id=?", (checkpoint["id"],))
            for published in checkpoint.get("publishes_interfaces", []):
                conn.execute("INSERT INTO checkpoint_interfaces(checkpoint_id,interface_id,version) VALUES(?,?,?)", (checkpoint["id"], published["id"], published.get("version")))
        for gate in task.get("gates", []):
            conn.execute(
                "INSERT INTO gates(id,task_id,checkpoint_id,type,config_json,required,status,valid,revision) VALUES(?,?,?,?,?,?,COALESCE((SELECT status FROM gates WHERE id=?),'pending'),COALESCE((SELECT valid FROM gates WHERE id=?),0),?) "
                "ON CONFLICT(id) DO UPDATE SET task_id=excluded.task_id,checkpoint_id=excluded.checkpoint_id,type=excluded.type,config_json=excluded.config_json,required=excluded.required,revision=excluded.revision",
                (gate["id"], task_id, gate.get("checkpoint_id"), gate["type"], json.dumps({key: value for key, value in gate.items() if key not in {"id", "type", "required", "checkpoint_id"}}, sort_keys=True), int(gate.get("required", True)), gate["id"], gate["id"], revision),
            )
            if gate.get("checkpoint_id"):
                conn.execute("INSERT OR REPLACE INTO checkpoint_gates(checkpoint_id,gate_id) VALUES(?,?)", (gate["checkpoint_id"], gate["id"]))
        for index, request in enumerate(task.get("resource_requests", [])):
            conn.execute(
                "INSERT INTO resource_requests(id,task_id,phase,selector,amount,mode,required) VALUES(?,?,?,?,?,?,?)",
                (request.get("id", f"{task_id}-resource-{index}"), task_id, request.get("phase", "manual"), request["selector"], int(request.get("amount", 1)), request.get("mode", "exclusive"), int(request.get("required", True))),
            )

    for barrier in data.get("barriers", []):
        conn.execute(
            "INSERT INTO barriers(id,title,mode,quorum,state,explanation,revision) VALUES(?,?,?,?,COALESCE((SELECT state FROM barriers WHERE id=?),'closed'),'pending reevaluation',?) "
            "ON CONFLICT(id) DO UPDATE SET title=excluded.title,mode=excluded.mode,quorum=excluded.quorum,revision=excluded.revision",
            (barrier["id"], barrier.get("title", barrier["id"]), barrier.get("mode", "all"), barrier.get("quorum"), barrier["id"], revision),
        )
        conn.execute("DELETE FROM barrier_requirements WHERE barrier_id=?", (barrier["id"],))
        for requirement in barrier.get("requirements", []):
            conn.execute(
                "INSERT INTO barrier_requirements(barrier_id,type,entity_id,required_state,dispositions_json) VALUES(?,?,?,?,?)",
                (barrier["id"], requirement["type"], requirement["id"], requirement.get("state", "done"), json.dumps(requirement.get("dispositions", []), sort_keys=True)),
            )
    for resource_class in data.get("resource_classes", []):
        conn.execute(
            "INSERT INTO resource_classes(id,mode,metadata_json) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET mode=excluded.mode,metadata_json=excluded.metadata_json",
            (resource_class["id"], resource_class.get("mode", "exclusive"), json.dumps(resource_class.get("metadata", {}), sort_keys=True)),
        )
        for instance in resource_class.get("instances", []):
            conn.execute(
                "INSERT INTO resource_instances(id,class_id,capacity,hostname,metadata_json,enabled) VALUES(?,?,?,?,?,1) "
                "ON CONFLICT(id) DO UPDATE SET capacity=excluded.capacity,hostname=excluded.hostname,metadata_json=excluded.metadata_json,enabled=1",
                (instance["id"], resource_class["id"], int(instance.get("capacity", 1)), instance.get("hostname"), json.dumps(instance.get("metadata", {}), sort_keys=True)),
            )
    from .graph import reevaluate_barriers

    barrier_changes = reevaluate_barriers(conn, revision)
    return {"tasks_upserted": len(tasks), "barriers": barrier_changes}


def plan_diff(conn: sqlite3.Connection, data: dict[str, Any]) -> dict[str, object]:
    existing = {row[0] for row in conn.execute("SELECT id FROM tasks")}
    incoming = {str(task["id"]) for task in data.get("tasks", [])}
    return {
        "add": sorted(incoming - existing),
        "update": sorted(incoming & existing),
        "unchanged_or_removed": sorted(existing - incoming),
    }


def scaffold(shape: str) -> dict[str, object]:
    base: dict[str, object] = {"schema_version": SCHEMA_VERSION, "project": {"name": "Project"}, "invariants": [], "decisions": [], "locks": [], "interfaces": [], "barriers": [], "resource_classes": [], "tasks": []}
    if shape == "fanout":
        base["tasks"] = [
            {"id": "EPIC-00", "kind": "epic", "title": "Parent", "parallel_policy": "serial"},
            *[{"id": f"TASK-{letter}", "parent_id": "EPIC-00", "kind": "task", "title": f"Child {letter}", "parallel_policy": "parallel_safe", "scope": {"exclusive_paths": [f"src/{letter.lower()}"]}} for letter in "ABC"],
            {"id": "INTEGRATE", "parent_id": "EPIC-00", "kind": "integration_task", "title": "Integrate", "parallel_policy": "integration_exclusive", "depends_on": [{"type": "barrier", "barrier_id": "FANIN"}]},
        ]
        base["barriers"] = [{"id": "FANIN", "mode": "all", "requirements": [{"type": "task", "id": f"TASK-{letter}", "state": "done"} for letter in "ABC"]}]
    elif shape == "producer-consumers":
        base["interfaces"] = [{"id": "contract", "owner_task_id": "PRODUCER", "contract_paths": ["include/contract.h"]}]
        base["tasks"] = [
            {"id": "PRODUCER", "kind": "workstream", "title": "Produce contract", "checkpoints": [{"id": "CONTRACT-FROZEN", "publishes_interfaces": [{"id": "contract", "version": "1"}]}]},
            {"id": "CONSUMER", "kind": "workstream", "title": "Consume contract", "depends_on": [{"type": "checkpoint", "checkpoint_id": "CONTRACT-FROZEN"}], "consumes_interfaces": [{"id": "contract", "required_state": "frozen"}]},
        ]
    elif shape == "benchmark":
        base["resource_classes"] = [{"id": "gpu", "instances": [{"id": "gpu:0"}, {"id": "gpu:1"}]}]
        base["tasks"] = [{"id": "BENCH", "kind": "workstream", "title": "Benchmark", "gates": [{"id": "BENCH-GATE", "type": "benchmark", "argv": ["python", "bench.py"], "resources": ["gpu:any"], "metric_path": "score", "operator": ">=", "threshold": 1.0}]}]
    elif shape == "integration-barrier":
        return scaffold("fanout")
    else:
        raise TodoError("unknown_scaffold", f"Unknown plan scaffold {shape}")
    return base
