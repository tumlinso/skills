# Computed Status, Leases, and Cleanup

Lifecycle values include `planned`, `in_progress`, `blocked`, `review`, `done`, `superseded`, `cancelled`, legacy `stale`, and recovery-only `attention_required`.

Execution state is computed: `ready`, `claimed`, `closed`, `inactive`, dependency/barrier/scope/resource blocked, `orphaned`, or `attention_required`. Markdown execution labels are compatibility projections, not input.

Claims default to a two-hour renewable lease. Expired clean scopes can return to ready; dirty scopes are quarantined. Legacy freshness review remains separate: planned/in-progress/stale use 3 days and blocked uses 7 days.

Cleanup is explicit-only. `todo cleanup` reports safety and never deletes v2 durable state. Legacy `cleanup_todos.py` retains its existing explicit cleanup behavior only in repositories not bootstrapped to v2.
