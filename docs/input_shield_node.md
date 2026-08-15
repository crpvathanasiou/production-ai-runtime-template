Ναι. Ο πιο καθαρός τρόπος να το δεις είναι ότι ο **input_shield agent** δεν είναι “ένα prompt”.
Είναι ένα **μικρό subsystem** με ownership split μεταξύ LangGraph node και Application Operation.

## Current architecture (M2)

```text
make_input_shield_node(...)
        ↓
LangGraph input-shield node
        ↓
InputShieldOperation
        ↓
PromptRepository.resolve(input-shield@1)
        ↓
ResolvedPrompt
        ↓
LLMPort
        ↓
AsyncOpenAIWrapper
```

**InputShieldOperation owns:**

- deterministic fail-fast invocation
- explicit `PromptRef` resolution via `PromptRepository`
- exact logical-prompt max-length check (combined logical prompt **strict >** `max_prompt_chars` → provider call prevented on block)
- LLM structured call via `LLMPort`
- normalization
- expected LLM-failure cautious fallback
- `PromptIdentity` on outcomes where a prompt was resolved

**Node owns:**

- `GraphState`
- `request_id`
- node timing/logging
- `workflow_outcome`
- `additional_metadata` mapping (copies safe prompt identity when present; does **not** resolve prompts)

`BaseGuardrail` / `MaxPromptLengthGuardrail` / `ShieldOutputNotEmptyGuardrail` remain wrapper-level concepts where used by the adapter; they did **not** move into Application Core. Synthetic successful `guardrail_notes` are **not** a required node-metadata result.

## Σχηματικά

```text
Incoming Ticket
     │
     ▼
[ input_shield_node ]          ← GraphState / request_id / logging / workflow_outcome
     │
     ▼
[ InputShieldOperation ]       ← application use-case semantics
     │
     ├── 1. local heuristic checks
     │       - empty / vague input
     │       - obvious privacy risk
     │       - obvious prompt injection
     │
     ├── 2. prompt resolution (only if fail-fast did not decide)
     │       - PromptRepository.resolve(input-shield@1)
     │       - ResolvedPrompt (system + user; content_hash of static definition)
     │
     ├── 3. logical-prompt max-length policy
     │       - strict > max_prompt_chars blocks before provider call
     │       - prompt identity still present (prompt was resolved)
     │
     ├── 4. LLMPort → AsyncOpenAIWrapper
     │       - strict structured call
     │       - timeout / retries
     │
     ├── 5. schema enforcement
     │       - ShieldOutput
     │
     └── 6. normalization / expected-failure fallback
             - fix inconsistent model outputs
             - harden decisions
             - prompt identity present on LLM success and handled llm_failure_fallback

     node then maps InputShieldOutcome →
             - state.shield_result
             - state.workflow_outcome
             - state.additional_metadata
               (safe prompt_id / prompt_revision / prompt_content_hash when identity exists)
```

Prompt identity semantics:

* heuristic_fail_fast → no prompt resolved → no prompt identity
* prompt_length_block → prompt resolved → identity present
* llm success → identity present
* handled llm_failure_fallback → identity present

---

# Τα components του input_shield agent

## 1. State input

Ο agent παίρνει από το graph state κυρίως:

* `request_id`
* `initial_ticket`

Αυτό είναι το operational context του **node** (όχι του Application Core).

---

## 2. Deterministic pre-checks

Αυτό είναι το αρχείο:

* `input_guardrails.py`

Εδώ έχεις φθηνά, γρήγορα checks πριν πας σε LLM:

* `normalize_whitespace`
* `sanitize_message`
* `matches_any_pattern`
* `collect_categories`
* `is_non_actionable`
* `build_fail_fast_shield_output`

### Ρόλος

Να κάνεις:

* fail fast
* economy
* obvious blocking
* predictable handling για απλά cases

Αυτό είναι το πρώτο protective ring — invoked από `InputShieldOperation`.

---

## 3. Prompt layer

Immutable code-backed V1 definition:

* `input_shield_prompts.py` → `INPUT_SHIELD_PROMPT_V1` (`input-shield@1`)
* one revision owns the complete system template + user template bundle
* resolved through application-owned `PromptRepository` (`LocalPromptRepository` in composition)

`content_hash` identifies the stored static templates, not runtime customer/domain values.

### Ρόλος

Να χωρίσεις:

* **policy / behavior instructions** (immutable revision)
* από το **runtime input** (variables supplied by the Application Operation)

Resolution ownership: `InputShieldOperation` via `PromptRepository` (όχι το LangGraph node).

---

## 4. LLM execution layer

Path:

* `InputShieldOperation` → `PromptRepository` → `ResolvedPrompt` → `LLMPort` → `AsyncOpenAIWrapper`

### Ρόλος

* Application Operation: PromptRef resolution, max-prompt policy, normalization/fallback, PromptIdentity
* `LLMPort`: receives only rendered `system_prompt` / `prompt` / `response_schema` (prompt-lifecycle neutral)
* `AsyncOpenAIWrapper`: outbound OpenAI adapter (retries, timeout, provider parsing)

Ο node **δεν** κατασκευάζει / καλεί απευθείας τον OpenAI wrapper και **δεν** κάνει prompt resolution.

---

## 5. Structured schema contract

Αυτό είναι το:

* `ShieldOutput` στο `schemas.py`

### Ρόλος

Να ορίζει το contract του agent:

* `decision`
* `risk_level`
* `categories`
* `sanitized_message`
* `should_route_to_human`
* `clarification_question`
* `reasoning`

Αυτό είναι το output surface του agent προς το υπόλοιπο graph.

---

## 6. Output hardening / normalization

Normalization / hardening ζει μέσα στο `InputShieldOperation`.

### Ρόλος

Να μη δεχτείς άκριτα το model output.

Παραδείγματα:

* αν υπάρχει `privacy_risk`, δεν πρέπει να καταλήγει σε `allow`
* αν υπάρχει `prompt_injection`, το `allow` γίνεται `allow_with_flag`
* αν υπάρχει `non_actionable`, δεν θες απλό `allow`

Αυτό είναι ουσιαστικά το δεύτερο protective ring.

---

## 7. Node orchestration logic

Αυτό είναι η factory / node:

* `make_input_shield_node(...)` → LangGraph `input_shield_node(state)`

### Ρόλος

Να συντονίσει GraphState mapping και observability.

Η σειρά είναι περίπου:

```text
read state
→ invoke InputShieldOperation
→ map InputShieldOutcome into GraphState
→ log + attach metadata
→ return state
```

---

## 8. Logging / observability layer

Μέσα στο **node** χρησιμοποιείς:

* `request_id`
* `logger`
* `additional_metadata`

### Ρόλος

Να κρατάς:

* start / end events
* latency
* model_name (label from composition)
* decision
* error_type

Αυτό είναι το operational layer του orchestration adapter.

---

## 9. Error handling layer

Με exceptions όπως:

* `GuardrailBlockedError`
* `ModelOutputParsingError`
* `UpstreamServiceError`

### Ρόλος

Expected LLM-failure cautious fallback is owned by `InputShieldOperation`.
Το node maps το outcome στο `workflow_outcome` / metadata.

---

# Αν το δεις σαν layered design

## Layer 1 — Domain contract

* `SupportTicket`
* `ShieldOutput`

## Layer 2 — Local safety logic

* regex / heuristics / sanitization

## Layer 3 — Prompt identity / resolution

* immutable `PromptDefinition` (`input-shield@1`)
* `PromptRepository` → `ResolvedPrompt`

## Layer 4 — Application Operation + LLMPort

* `InputShieldOperation`
* provider-neutral `LLMPort`
* `AsyncOpenAIWrapper` as OpenAI adapter

## Layer 5 — Node orchestration

* `input_shield_node` (GraphState / routing / metadata)

## Layer 6 — Runtime operations

* logging
* metadata (safe prompt identity when present)
* exceptions
* retries / timeouts (adapter)

---

# Με μία φράση

Ο **input_shield agent** “χτίζεται” από:

1. **schema contract**
2. **heuristic guardrails**
3. **immutable PromptDefinition + PromptRepository**
4. **InputShieldOperation + LLMPort + OpenAI adapter**
5. **node orchestration logic** (GraphState mapping)

---

# Πρακτικά, ποιο είναι το boundary του agent;

Αν το περιγράψεις σε συνέντευξη ή documentation:

> The input shield agent is a LangGraph orchestration node that invokes `InputShieldOperation`. The operation owns deterministic pre-checks, immutable PromptRef resolution, exact logical-prompt max-length policy, structured LLM classification via `LLMPort`, normalization, and expected-failure fallback. The node owns GraphState mapping, `request_id`, timing/logging, `workflow_outcome`, and safe prompt-identity metadata when an outcome carries identity.

Αυτό είναι πολύ σωστή περιγραφή.

---

# Mini diagram με αρχεία

```text
schemas.py
 ├── SupportTicket
 └── ShieldOutput

input_guardrails.py
 ├── sanitize_message
 ├── collect_categories
 ├── is_non_actionable
 └── build_fail_fast_shield_output

input_shield_prompts.py
 └── INPUT_SHIELD_PROMPT_V1  (immutable PromptDefinition, input-shield@1)

app/application/prompts/
 ├── PromptRef / PromptIdentity / ResolvedPrompt
 └── PromptRepository

app/prompts/local_repository.py
 └── LocalPromptRepository

app/application/input_shield.py
 └── InputShieldOperation

app/application/ports/llm.py
 └── LLMPort

openai_wrapper.py
 └── AsyncOpenAIWrapper (OpenAI adapter behind LLMPort)

app/nodes/input_shield.py
 ├── make_input_shield_node(...)
 └── async input_shield_node(state)  # GraphState / metadata / workflow_outcome
```

---

# Και σε flow μορφή

```text
GraphState.initial_ticket
        │
        ▼
input_shield_node
        │
        ▼
InputShieldOperation
        │
        ├── early return if obvious fail-fast case
        │      (no prompt resolution / no identity)
        ▼
PromptRepository.resolve(input-shield@1) → ResolvedPrompt
        ▼
exact logical-prompt max-length policy
        ▼
LLMPort → AsyncOpenAIWrapper
        ▼
ShieldOutput + normalization / fallback (+ PromptIdentity)
        ▼
node maps → GraphState.shield_result
        ▼
workflow_outcome + metadata (+ safe prompt identity) + logs
```

-------------------------------------------------------------------


## Sequence diagram

Δείχνει **τη ροή εκτέλεσης** βήμα-βήμα.

```text
Client / API / graph runner
    |
    v
Graph Execution
    |
    v
input_shield_node(state)
    |
    |-- reads --> state.request_id
    |-- reads --> state.initial_ticket
    |
    |-- invokes --> InputShieldOperation.execute(...)
    |                 |
    |                 |-- build_fail_fast_shield_output(ticket)
    |                 |-- (else) PromptRepository.resolve(input-shield@1)
    |                 |-- exact logical-prompt max-length check
    |                 |-- LLMPort → AsyncOpenAIWrapper.generate_structured(...)
    |                 |-- normalize / expected-failure fallback
    |                 '-- returns --> InputShieldOutcome (+ PromptIdentity when resolved)
    |
    |-- writes --> state.shield_result
    |-- writes --> state.workflow_outcome
    |-- writes --> state.additional_metadata  (safe prompt identity when present)
    '-- returns --> updated state
```

---

## Component diagram

Δείχνει **ποια μέρη συνεργάζονται** και ποιος είναι ο ρόλος του καθενός.

```text
                    ┌──────────────────────┐
                    │      GraphState       │
                    │----------------------│
                    │ request_id           │
                    │ initial_ticket       │
                    │ shield_result        │
                    │ workflow_outcome     │
                    │ additional_metadata  │
                    └──────────┬───────────┘
                               │
                               │ input
                               v
                 ┌──────────────────────────────┐
                 │      input_shield_node       │
                 │------------------------------│
                 │ GraphState mapping           │
                 │ logs lifecycle               │
                 │ workflow_outcome             │
                 └──────────────┬───────────────┘
                                │
                                v
                 ┌──────────────────────────────┐
                 │    InputShieldOperation      │
                 │------------------------------│
                 │ fail-fast / PromptRef resolve│
                 │ max-prompt / LLMPort / norm  │
                 └───┬──────────────────┬───────┘
                     │                  │
                     v                  v
         ┌─────────────────────┐   ┌──────────────────────────┐
         │ input_guardrails.py │   │ PromptRepository         │
         └─────────────────────┘   │ → ResolvedPrompt         │
                                   │ (input-shield@1)         │
                                   └───────────┬──────────────┘
                                               │
                                               v
                                    ┌──────────────────────────┐
                                    │ LLMPort                  │
                                    │ → AsyncOpenAIWrapper     │
                                    │ → OpenAI API             │
                                    └──────────────────────────┘
```

---

## Interview-ready condensed version

### Sequence version

> The input shield node reads GraphState, invokes `InputShieldOperation`, maps the outcome into `shield_result` / `workflow_outcome` / metadata (including safe prompt identity when present), and returns. The operation owns fail-fast checks, immutable PromptRef resolution, max-prompt policy, `LLMPort` classification, and normalization/fallback.

### Component version

> The input shield agent consists of a schema contract, heuristic guardrails, an immutable V1 PromptDefinition resolved through `PromptRepository`, `InputShieldOperation` behind `LLMPort`/`AsyncOpenAIWrapper`, and a LangGraph node that owns GraphState orchestration.

---

## Η ουσία

Το σημαντικό είναι να μη λες ότι:

**“Ο input shield agent είναι ένα prompt.”**
ή ότι **το node καλεί απευθείας τον OpenAI wrapper.**

Το σωστό είναι:

**“Ο input shield είναι orchestrated safety subsystem: LangGraph node για GraphState/observability, Application Operation για prompt/LLM/use-case semantics.”**
