"""SQLite schema and forward-only migrations."""

from __future__ import annotations

SCHEMA_VERSION = 2

MIGRATION_1 = r"""
CREATE TABLE IF NOT EXISTS schema_migrations(
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(
  id TEXT PRIMARY KEY, label TEXT NOT NULL UNIQUE, token_hash TEXT NOT NULL UNIQUE,
  external_id TEXT, hostname TEXT NOT NULL, pid INTEGER, process_start TEXT,
  repo_root TEXT NOT NULL, worktree_root TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, state TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks(
  id TEXT PRIMARY KEY, parent_id TEXT REFERENCES tasks(id), kind TEXT NOT NULL,
  title TEXT NOT NULL, objective TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'planned',
  priority INTEGER NOT NULL DEFAULT 0, tags_json TEXT NOT NULL DEFAULT '[]',
  parallel_policy TEXT NOT NULL DEFAULT 'serial', result TEXT, next_action TEXT NOT NULL DEFAULT '',
  result_policy_json TEXT NOT NULL DEFAULT '{}',
  notes TEXT NOT NULL DEFAULT '', legacy_owner TEXT, legacy_payload_json TEXT NOT NULL DEFAULT '{}',
  attention_reason TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1, revision INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_tasks_parent ON tasks(parent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status_priority ON tasks(status, priority DESC, id);
CREATE TABLE IF NOT EXISTS decisions(
  id TEXT PRIMARY KEY, title TEXT NOT NULL, value_json TEXT, allowed_json TEXT NOT NULL DEFAULT '[]',
  updated_at TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS task_dependencies(
  id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  type TEXT NOT NULL, prerequisite_task_id TEXT REFERENCES tasks(id), checkpoint_id TEXT,
  interface_id TEXT, barrier_id TEXT, decision_id TEXT, condition_json TEXT NOT NULL DEFAULT '{}',
  UNIQUE(task_id,type,prerequisite_task_id,checkpoint_id,interface_id,barrier_id,decision_id)
);
CREATE INDEX IF NOT EXISTS idx_dependencies_task ON task_dependencies(task_id);
CREATE TABLE IF NOT EXISTS checkpoints(
  id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id), title TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'pending', reached_at TEXT, revoked_at TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}', revision INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS barriers(
  id TEXT PRIMARY KEY, title TEXT NOT NULL, mode TEXT NOT NULL DEFAULT 'all', quorum INTEGER,
  state TEXT NOT NULL DEFAULT 'closed', explanation TEXT NOT NULL DEFAULT '', opened_at TEXT,
  revision INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS barrier_requirements(
  id INTEGER PRIMARY KEY AUTOINCREMENT, barrier_id TEXT NOT NULL REFERENCES barriers(id) ON DELETE CASCADE,
  type TEXT NOT NULL, entity_id TEXT NOT NULL, required_state TEXT NOT NULL,
  dispositions_json TEXT NOT NULL DEFAULT '[]', UNIQUE(barrier_id,type,entity_id,required_state)
);
CREATE TABLE IF NOT EXISTS interfaces(
  id TEXT PRIMARY KEY, owner_task_id TEXT NOT NULL REFERENCES tasks(id), state TEXT NOT NULL DEFAULT 'draft',
  version TEXT NOT NULL DEFAULT '0', contract_paths_json TEXT NOT NULL DEFAULT '[]', content_hash TEXT,
  frozen_at TEXT, revised_at TEXT, revision INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS interface_consumers(
  interface_id TEXT NOT NULL REFERENCES interfaces(id) ON DELETE CASCADE,
  task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  required_state TEXT NOT NULL DEFAULT 'frozen', required_version TEXT,
  PRIMARY KEY(interface_id,task_id)
);
CREATE TABLE IF NOT EXISTS checkpoint_interfaces(
  checkpoint_id TEXT NOT NULL REFERENCES checkpoints(id) ON DELETE CASCADE,
  interface_id TEXT NOT NULL REFERENCES interfaces(id) ON DELETE CASCADE,
  version TEXT, PRIMARY KEY(checkpoint_id,interface_id)
);
CREATE TABLE IF NOT EXISTS invariants(
  id TEXT PRIMARY KEY, rule TEXT NOT NULL, scope_json TEXT NOT NULL DEFAULT '{}',
  severity TEXT NOT NULL DEFAULT 'error', enforcement TEXT
);
CREATE TABLE IF NOT EXISTS task_invariants(
  task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  invariant_id TEXT NOT NULL REFERENCES invariants(id) ON DELETE CASCADE,
  PRIMARY KEY(task_id,invariant_id)
);
CREATE TABLE IF NOT EXISTS ownership_scopes(
  task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  mode TEXT NOT NULL, path TEXT NOT NULL, PRIMARY KEY(task_id,mode,path)
);
CREATE INDEX IF NOT EXISTS idx_scope_path ON ownership_scopes(path,mode);
CREATE TABLE IF NOT EXISTS task_artifacts(
  task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  kind TEXT NOT NULL, path TEXT NOT NULL, content_hash TEXT,
  PRIMARY KEY(task_id,kind,path)
);
CREATE TABLE IF NOT EXISTS named_locks(name TEXT PRIMARY KEY, capacity INTEGER NOT NULL DEFAULT 1, metadata_json TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS task_locks(
  task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE, lock_name TEXT NOT NULL REFERENCES named_locks(name),
  phase TEXT NOT NULL DEFAULT 'claim', PRIMARY KEY(task_id,lock_name,phase)
);
CREATE TABLE IF NOT EXISTS claims(
  id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id), session_id TEXT NOT NULL REFERENCES sessions(id),
  token_hash TEXT NOT NULL UNIQUE, state TEXT NOT NULL, created_at TEXT NOT NULL, heartbeat_at TEXT NOT NULL,
  expires_at TEXT NOT NULL, baseline_head TEXT, baseline_manifest_json TEXT NOT NULL DEFAULT '{}',
  baseline_revision INTEGER NOT NULL, orphan_reason TEXT, released_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_claim_per_task ON claims(task_id) WHERE state='active';
CREATE INDEX IF NOT EXISTS idx_claims_state_expiry ON claims(state,expires_at);
CREATE TABLE IF NOT EXISTS lock_leases(
  id TEXT PRIMARY KEY, lock_name TEXT NOT NULL REFERENCES named_locks(name), claim_id TEXT REFERENCES claims(id),
  session_id TEXT NOT NULL REFERENCES sessions(id), token_hash TEXT NOT NULL, state TEXT NOT NULL,
  acquired_at TEXT NOT NULL, heartbeat_at TEXT NOT NULL, expires_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_exclusive_lock ON lock_leases(lock_name) WHERE state='active';
CREATE TABLE IF NOT EXISTS resource_classes(
  id TEXT PRIMARY KEY, mode TEXT NOT NULL DEFAULT 'exclusive', metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS resource_instances(
  id TEXT PRIMARY KEY, class_id TEXT NOT NULL REFERENCES resource_classes(id), capacity INTEGER NOT NULL DEFAULT 1,
  hostname TEXT, metadata_json TEXT NOT NULL DEFAULT '{}', enabled INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_resources_class ON resource_instances(class_id,enabled,id);
CREATE TABLE IF NOT EXISTS resource_requests(
  id TEXT PRIMARY KEY, task_id TEXT REFERENCES tasks(id) ON DELETE CASCADE, gate_id TEXT,
  phase TEXT NOT NULL, selector TEXT NOT NULL, amount INTEGER NOT NULL DEFAULT 1,
  mode TEXT NOT NULL DEFAULT 'exclusive', required INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS resource_leases(
  id TEXT PRIMARY KEY, instance_id TEXT NOT NULL REFERENCES resource_instances(id), claim_id TEXT REFERENCES claims(id),
  session_id TEXT NOT NULL REFERENCES sessions(id), request_id TEXT, token_hash TEXT NOT NULL,
  state TEXT NOT NULL, hostname TEXT NOT NULL, pid INTEGER, process_start TEXT, command_json TEXT,
  acquired_at TEXT NOT NULL, heartbeat_at TEXT NOT NULL, expires_at TEXT NOT NULL, released_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_resource_leases_active ON resource_leases(instance_id,state,expires_at);
CREATE TABLE IF NOT EXISTS gates(
  id TEXT PRIMARY KEY, task_id TEXT REFERENCES tasks(id) ON DELETE CASCADE,
  checkpoint_id TEXT REFERENCES checkpoints(id) ON DELETE CASCADE, type TEXT NOT NULL,
  config_json TEXT NOT NULL DEFAULT '{}', required INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'pending', valid INTEGER NOT NULL DEFAULT 0,
  input_fingerprint TEXT, last_run_at TEXT, revision INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS checkpoint_gates(
  checkpoint_id TEXT NOT NULL REFERENCES checkpoints(id) ON DELETE CASCADE,
  gate_id TEXT NOT NULL REFERENCES gates(id) ON DELETE CASCADE,
  PRIMARY KEY(checkpoint_id,gate_id)
);
CREATE TABLE IF NOT EXISTS evidence(
  id TEXT PRIMARY KEY, gate_id TEXT REFERENCES gates(id), checkpoint_id TEXT REFERENCES checkpoints(id),
  claim_id TEXT REFERENCES claims(id), kind TEXT NOT NULL, status TEXT NOT NULL,
  path TEXT, content_hash TEXT, metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL,
  revision INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS handoffs(
  id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id), claim_id TEXT REFERENCES claims(id),
  kind TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', payload_json TEXT NOT NULL, created_at TEXT NOT NULL,
  revision INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS migration_warnings(
  id INTEGER PRIMARY KEY AUTOINCREMENT, entity_id TEXT, code TEXT NOT NULL, message TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, resolved_at TEXT
);
CREATE TABLE IF NOT EXISTS projection_status(
  name TEXT PRIMARY KEY, revision INTEGER NOT NULL DEFAULT 0, generated_at TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS events(
  seq INTEGER PRIMARY KEY AUTOINCREMENT, revision INTEGER NOT NULL UNIQUE, timestamp TEXT NOT NULL,
  actor_session_id TEXT REFERENCES sessions(id), entity_type TEXT NOT NULL, entity_id TEXT,
  event_type TEXT NOT NULL, payload_json TEXT NOT NULL
);
"""

MIGRATION_2 = r"""
CREATE INDEX IF NOT EXISTS idx_events_entity ON events(entity_type,entity_id,revision);
CREATE INDEX IF NOT EXISTS idx_evidence_gate ON evidence(gate_id,created_at);
"""

MIGRATION_3 = r"""
ALTER TABLE lock_leases ADD COLUMN hostname TEXT;
ALTER TABLE lock_leases ADD COLUMN pid INTEGER;
ALTER TABLE lock_leases ADD COLUMN process_start TEXT;
ALTER TABLE lock_leases ADD COLUMN command_json TEXT;
CREATE INDEX IF NOT EXISTS idx_lock_leases_expiry ON lock_leases(state,expires_at);
"""

MIGRATION_4 = r"""
CREATE TABLE IF NOT EXISTS child_executions(
  id TEXT PRIMARY KEY,
  parent_claim_id TEXT NOT NULL REFERENCES claims(id),
  task_id TEXT NOT NULL REFERENCES tasks(id),
  objective TEXT NOT NULL,
  gates_json TEXT NOT NULL DEFAULT '[]',
  state TEXT NOT NULL,
  max_attempts INTEGER NOT NULL DEFAULT 1,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  cancel_requested INTEGER NOT NULL DEFAULT 0,
  result_json TEXT,
  created_at TEXT NOT NULL,
  started_at TEXT,
  heartbeat_at TEXT,
  completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_child_executions_parent
  ON child_executions(parent_claim_id,state,created_at);
CREATE TABLE IF NOT EXISTS child_scope_leases(
  child_execution_id TEXT NOT NULL REFERENCES child_executions(id) ON DELETE CASCADE,
  path TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'active',
  acquired_at TEXT NOT NULL,
  released_at TEXT,
  PRIMARY KEY(child_execution_id,path)
);
CREATE INDEX IF NOT EXISTS idx_child_scope_leases_active
  ON child_scope_leases(path,state);
CREATE TABLE IF NOT EXISTS child_attempts(
  id TEXT PRIMARY KEY,
  child_execution_id TEXT NOT NULL REFERENCES child_executions(id) ON DELETE CASCADE,
  attempt_number INTEGER NOT NULL,
  token_hash TEXT NOT NULL UNIQUE,
  state TEXT NOT NULL,
  created_at TEXT NOT NULL,
  heartbeat_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  completed_at TEXT,
  result_json TEXT,
  UNIQUE(child_execution_id,attempt_number)
);
CREATE INDEX IF NOT EXISTS idx_child_attempts_expiry
  ON child_attempts(state,expires_at);
"""

MIGRATION_5 = r"""
ALTER TABLE child_executions ADD COLUMN candidate_gates_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE child_executions ADD COLUMN acceptance_gates_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE child_executions ADD COLUMN result_refs_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE child_attempts ADD COLUMN result_refs_json TEXT NOT NULL DEFAULT '{}';
"""

MIGRATION_6 = r"""
ALTER TABLE child_executions ADD COLUMN access_mode TEXT NOT NULL DEFAULT 'write';
ALTER TABLE child_executions ADD COLUMN authorized_scopes_json TEXT NOT NULL DEFAULT '[]';
"""

MIGRATION_7 = r"""
ALTER TABLE claims ADD COLUMN owner_system TEXT;
ALTER TABLE claims ADD COLUMN owner_instance_id TEXT;
CREATE TABLE IF NOT EXISTS live_recovery_approvals(
  id TEXT PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE,
  repo_root TEXT NOT NULL, project_uuid TEXT NOT NULL, task_id TEXT NOT NULL,
  claim_fingerprint TEXT NOT NULL, project_revision INTEGER NOT NULL,
  requester_uid INTEGER NOT NULL, approver_identity TEXT NOT NULL, reason TEXT NOT NULL,
  prior_instance_id TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'pending', consumed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_live_recovery_approval_state
  ON live_recovery_approvals(state,expires_at);
CREATE TABLE IF NOT EXISTS live_recovery_audit(
  id TEXT PRIMARY KEY, task_id TEXT NOT NULL,
  prior_claim_fingerprint TEXT NOT NULL, new_claim_fingerprint TEXT NOT NULL,
  approver_identity TEXT NOT NULL, requester_uid INTEGER NOT NULL, reason TEXT NOT NULL,
  approved_at TEXT NOT NULL, consumed_at TEXT NOT NULL,
  prior_instance_id TEXT NOT NULL, new_instance_id TEXT NOT NULL,
  disposition TEXT NOT NULL, project_revision INTEGER NOT NULL
);
"""

MIGRATION_8 = r"""
ALTER TABLE live_recovery_approvals ADD COLUMN approval_kind TEXT NOT NULL DEFAULT 'live_claim_override';
ALTER TABLE live_recovery_approvals ADD COLUMN context_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE live_recovery_audit ADD COLUMN context_json TEXT NOT NULL DEFAULT '{}';
"""

MIGRATION_9 = r"""
ALTER TABLE tasks ADD COLUMN completion_revision INTEGER;
ALTER TABLE tasks ADD COLUMN completion_git_head TEXT;
ALTER TABLE tasks ADD COLUMN completion_commit TEXT;
CREATE TABLE IF NOT EXISTS task_completion_gates(
  task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  gate_id TEXT NOT NULL REFERENCES gates(id) ON DELETE CASCADE,
  status TEXT NOT NULL, valid INTEGER NOT NULL,
  input_fingerprint TEXT, evidence_id TEXT REFERENCES evidence(id),
  evidence_revision INTEGER, validation_git_head TEXT,
  completion_revision INTEGER NOT NULL, completion_git_head TEXT,
  provenance_json TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY(task_id,gate_id)
);
CREATE INDEX IF NOT EXISTS idx_task_completion_gates_revision
  ON task_completion_gates(task_id,completion_revision);
"""

MIGRATIONS = {
  1: MIGRATION_1, 2: MIGRATION_2, 3: MIGRATION_3, 4: MIGRATION_4,
  5: MIGRATION_5, 6: MIGRATION_6, 7: MIGRATION_7, 8: MIGRATION_8,
  9: MIGRATION_9,
}
