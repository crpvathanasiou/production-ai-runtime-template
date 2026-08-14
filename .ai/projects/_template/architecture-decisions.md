# Architecture decisions

**Purpose: APPROVED PROJECT-SPECIFIC TECHNICAL CHOICES**

A project decision may **specialize** the template. It must **not** silently override template invariants ([`../../architecture/architecture-rules.md`](../../architecture/architecture-rules.md)).

A genuine deviation requires:

```text
real requirement
        ↓
explicit deviation
        ↓
architecture review
        ↓
rationale / trade-off
        ↓
scoped project decision (this file)
```

Deferred capabilities stay deferred until a decision here plus an explicit milestone activates them ([`../../architecture/deferred-capabilities.md`](../../architecture/deferred-capabilities.md)). Presence of a seed library (LangGraph, Redis, LangSmith) is not an activation.

Next approved action: [`.ai/handoff.md`](../../handoff.md).

---

Copy the block below per decision.

```text
## Decision

### Status
proposed | accepted | superseded | rejected

### Context

### Options considered

### Rationale

### Trade-offs

### Consequences

### Affected template / deferred capability
(none | name the capability and whether this activates it)

### Explicit deviation
(none | which invariant/contract is specialized, and the scoped exception)
```
