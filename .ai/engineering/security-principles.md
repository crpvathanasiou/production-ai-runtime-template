# Security principles

Reusable, framework/provider-neutral security policy for this template. Not a compliance manual. Not an IAM architecture.

Project-specific threat modelling, OWASP analysis, IAM, compliance mapping, regulatory controls, and data-residency architecture remain **requirement-driven** (record them under `.ai/projects/<project>/architecture-decisions.md` when justified).

## Trust boundaries

Untrusted by default:

- user input;
- model output;
- retrieved content;
- tool output;
- external API content.

```text
instructions inside untrusted content
        ≠
application authority
```

Prompt injection is a **trust-boundary / untrusted-content** problem, not a special LLM feature. Retrieved content, tool output, and user content must not silently redefine application or system policy.

## Least privilege and secure defaults

Grant the minimum capability needed for the approved use case. Default deny for controlled side effects. Least privilege applies to both provider adapters and tool / external-system access. Optional infrastructure (Redis, extra providers, brokers) is not a privilege expansion “for production completeness.”

## Secrets and credentials

Credentials are configuration / secret-management / adapter concerns.

Do **not** place credentials in:

- application contracts;
- prompts;
- source code;
- logs.

## PII / sensitive-data minimization

Collect, log, and retain the minimum. Observability must not become a dump of raw user or model payloads ([`../operations/observability-strategy.md`](../operations/observability-strategy.md)).

## External egress

External egress is a deliberate trust/security-boundary decision. Outbound network access is not implied by model text.

LLM inference and controlled business/external tool actions are different mechanisms.

```text
LLM inference
        ↓
application-facing LLMPort
        ↓
provider adapter
```

LLM provider calls remain behind the provider-neutral LLM boundary. An LLM invocation is **not** automatically a `ToolRequest` / tool-execution operation. Network egress, latency, or model cost alone does not make an LLM call a tool side effect.

```text
controlled business / external tool action
        ↓
ToolRequest
        ↓
validation
        ↓
policy / authorization
        ↓
execution through ToolAdapter
        ↓
result validation
        ↓
ToolResult
```

Controlled external actions, tools, and side effects follow the controlled-tool contract where applicable ([`../contracts/tool-execution-contract.md`](../contracts/tool-execution-contract.md)). Authorization semantics remain application-owned. Tool and external outputs remain untrusted.

## Dependency and container hygiene

Stay on the approved stack ([`engineering-principles.md`](engineering-principles.md)). Do not add dependencies or images without an approved milestone. Do not copy another repository’s toolchain as a silent replacement.

## Authentication vs authorization

```text
authentication ≠ authorization
```

**Authentication** establishes identity (who is this caller?).

**Authorization** determines whether an action is permitted.

Application policy owns authorization semantics. **LLMs cannot grant permissions.** A registered tool is not an authorized tool.

## Hidden reasoning is not telemetry

Hidden model reasoning / chain-of-thought **must not** be persisted or logged as an observability requirement. Decision visibility (policy result, reason code) is not hidden reasoning. See [`../operations/observability-strategy.md`](../operations/observability-strategy.md).

## SURFACE DISCREPANCY

If a project environment, log config, or seeded path places secrets in prompts/logs, or treats model output as policy:

```text
SURFACE DISCREPANCY
```
