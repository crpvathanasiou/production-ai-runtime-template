# Agent behaviour contract

Normative reusable runtime AI/agent behaviour. Authority for this domain only. Not Cursor governance. Not a LangGraph topology. Not a Customer Support playbook.

This contract is **what should be true**. It does not mean the seeded runtime already implements it.

## Deterministic vs probabilistic responsibility

Known rules that can be expressed without a model stay **deterministic**: thresholds, allow/deny lists, schema checks, authorization, idempotency keys, and other explicit policy.

The LLM is responsible only for **probabilistic** work: interpretation, drafting, classification where rules are insufficient, and similar judgement under uncertainty.

Do not send a known rule to a model “for flexibility.”

## Structured output

When downstream code depends on structure, require **structured output** against an application-owned schema. Unstructured prose is not a contract.

Provider SDK objects are not application contracts.

## Model output is untrusted

Model output is data, not authority. It is untrusted until application validation (and authorization, where a side effect is involved) succeeds.

The model cannot:

- grant permissions;
- redefine policy;
- bypass controlled side-effect rules;
- treat its own text as a verified fact.

## Uncertainty and failure

When the model (or the application) cannot meet the contract with acceptable confidence:

- fail closed where safety/policy requires it;
- return an explicit failure/uncertainty outcome;
- do not invent facts, permissions, or completed side effects.

Silent success on incomplete or invalid output is out of contract.

## Controlled side effects

**Controlled side effects** in this contract are agent-initiated business/external actions that mutate, send, trigger, execute, persist, purchase, notify, or otherwise materially affect external or application state.

Examples conceptually include:

- writing business data;
- submitting an order;
- sending a message;
- executing an external business operation;
- invoking an authorized action/tool.

Those controlled side effects happen only through application-authorized handling of a `ToolRequest` that yields a `ToolResult` (see [`tool-execution-contract.md`](tool-execution-contract.md)).

LLM intent is not execution. High-impact or irreversible operations require policy control before any adapter runs.

Ordinary LLM inference / provider calls are a different path:

```text
LLM inference
        ↓
LLMPort
        ↓
provider adapter
```

LLM inference / provider calls are **not** `ToolRequest` executions merely because they involve network access, external egress, latency, or cost. Do not redefine every outbound adapter interaction as a `ToolRequest`.

## Human escalation (behavioural principle)

Escalate for human approval or takeover when required by:

- policy;
- material risk;
- meaningful uncertainty;
- a high-impact or irreversible action.

This is a **business/runtime behavioural principle**.

It does **not** imply that the baseline implements:

- a generic HITL runtime;
- LangGraph `interrupt()` / resume;
- checkpointing;
- a review UI;
- durable human-approval persistence.

Those remain requirement-driven and deferred until activated from the deferred-capability register with a project architecture decision.

## SURFACE DISCREPANCY

If this contract says the agent must behave in a way the current code, config, or tests do not:

```text
SURFACE DISCREPANCY
```

Do not infer implementation from this document. Do not infer approval from seeded behaviour.
