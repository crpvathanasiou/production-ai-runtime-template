# Controlled tool-execution contract

Normative reusable side-effect contract. `ToolRequest` and `ToolResult` are **application-owned contracts**, not ports.

This contract is **what should be true**. It does not implement tool runtime.

## Contracts

```text
Application Contracts
├── ToolRequest
└── ToolResult
```

The LLM cannot perform side effects by itself. Model output may *propose* work; only an authorized `ToolRequest` may execute.

## Required flow

```text
ToolRequest
        ↓
request / schema validation
        ↓
policy / authorization
        ↓
idempotency when required
        ↓
execution
        ↓
output / result validation
        ↓
ToolResult
```

Skip no step because the model “already decided.”

## Distinct checks

```text
validation ≠ authorization

registered / available tool
    ≠ caller automatically authorized

model intent
    ≠ permission

tool / external output
    = untrusted input
```

**Validation** asks: is this a well-formed `ToolRequest` for a known tool schema?

**Authorization** asks: may this caller, in this `ExecutionContext`, perform this tool with these arguments, under application policy?

A tool that exists in a catalog is not therefore permitted. LLMs cannot grant permission.

After execution, **result validation** checks that `ToolResult` matches the expected schema. Valid shape still does not make the payload trusted content (see [`../engineering/security-principles.md`](../engineering/security-principles.md)).

## Idempotency

Idempotency is **requirement-driven**, especially for repeatable side effects (payments, tickets, mutations, notifications). Persistent idempotency runtime is **DEFER**.

When required, the application supplies an idempotency key *before* execution, not after a duplicate has already landed.

## Database tool vs application persistence

```text
Database exposed as an agent/tool capability
        ↓
ToolAdapter boundary
        ↓
Controlled tool execution policy
```

versus:

```text
Application/domain persistence
        ↓
Persistence Port
        ↓
Persistence Adapter / database driver
```

A database is not an LLM/tool interface merely because the application stores data there. Keep both capabilities deferred until separately justified.

## Deferred (not implied by this contract)

Presence of `ToolRequest` / `ToolResult` is **not** permission to implement:

- generic `ControlledToolExecutor`
- MCP tool adapter
- REST tool adapter
- DB tool adapter
- persistent idempotency runtime

See [`../architecture/deferred-capabilities.md`](../architecture/deferred-capabilities.md). Activation requires a real requirement, a project architecture decision, and an explicit milestone.

## SURFACE DISCREPANCY

Current seed: `execute_plan` contains retrieval-shaped orchestration through the seeded retrieval entrypoint, which currently has no active retrieval source, plus response drafting inside the node.

```text
SURFACE DISCREPANCY
```

if this document is treated as implemented runtime.
