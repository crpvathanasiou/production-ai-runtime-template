Ναι. Ο πιο καθαρός τρόπος να το δεις είναι ότι ο **input_shield agent** δεν είναι “ένα prompt”.
Είναι ένα **μικρό subsystem** με ownership split μεταξύ LangGraph node και Application Operation.

## Current architecture (M1)

```text
make_input_shield_node(...)
        ↓
LangGraph input-shield node
        ↓
InputShieldOperation
        ↓
LLMPort
        ↓
AsyncOpenAIWrapper
```

**InputShieldOperation owns:**

- deterministic fail-fast invocation
- prompt builder invocation
- exact logical-prompt max-length check (combined logical prompt **strict >** `max_prompt_chars` → provider call prevented on block)
- LLM structured call via `LLMPort`
- normalization
- expected LLM-failure cautious fallback

**Node owns:**

- `GraphState`
- `request_id`
- node timing/logging
- `workflow_outcome`
- `additional_metadata` mapping

`BaseGuardrail` / `MaxPromptLengthGuardrail` / `ShieldOutputNotEmptyGuardrail` remain wrapper-level concepts where used by the adapter; they did **not** move into Application Core. Synthetic successful `guardrail_notes` are **not** a required node-metadata result after M1.

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
     ├── 2. prompt building
     │       - system prompt
     │       - user prompt
     │
     ├── 3. logical-prompt max-length policy
     │       - strict > max_prompt_chars blocks before provider call
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

     node then maps InputShieldOutcome →
             - state.shield_result
             - state.workflow_outcome
             - state.additional_metadata
```

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

Αυτό είναι το αρχείο:

* `input_shield_prompts.py`

Έχεις δύο κομμάτια:

* `build_input_shield_system_prompt()`
* `build_input_shield_user_prompt(ticket)`

### Ρόλος

Να χωρίσεις:

* **policy / behavior instructions**
* από το **runtime input**

Invocation ownership: `InputShieldOperation` (όχι το LangGraph node).

---

## 4. LLM execution layer

Path:

* `InputShieldOperation` → `LLMPort` → `AsyncOpenAIWrapper`

### Ρόλος

* Application Operation: prompt invocation, max-prompt policy, normalization/fallback
* `AsyncOpenAIWrapper`: outbound OpenAI adapter (retries, timeout, provider parsing)

Ο node **δεν** κατασκευάζει / καλεί απευθείας τον OpenAI wrapper.

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

## Layer 3 — Prompting

* system prompt
* user prompt

## Layer 4 — Application Operation + LLMPort

* `InputShieldOperation`
* provider-neutral `LLMPort`
* `AsyncOpenAIWrapper` as OpenAI adapter

## Layer 5 — Node orchestration

* `input_shield_node` (GraphState / routing / metadata)

## Layer 6 — Runtime operations

* logging
* metadata
* exceptions
* retries / timeouts (adapter)

---

# Με μία φράση

Ο **input_shield agent** “χτίζεται” από:

1. **schema contract**
2. **heuristic guardrails**
3. **prompts**
4. **InputShieldOperation + LLMPort + OpenAI adapter**
5. **node orchestration logic** (GraphState mapping)

---

# Πρακτικά, ποιο είναι το boundary του agent;

Αν το περιγράψεις σε συνέντευξη ή documentation:

> The input shield agent is a LangGraph orchestration node that invokes `InputShieldOperation`. The operation owns deterministic pre-checks, prompt invocation, exact logical-prompt max-length policy, structured LLM classification via `LLMPort`, normalization, and expected-failure fallback. The node owns GraphState mapping, `request_id`, timing/logging, and `workflow_outcome`.

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
 ├── build_input_shield_system_prompt
 └── build_input_shield_user_prompt

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
        ▼
prompt builders + max-prompt policy
        ▼
LLMPort → AsyncOpenAIWrapper
        ▼
ShieldOutput + normalization / fallback
        ▼
node maps → GraphState.shield_result
        ▼
workflow_outcome + metadata + logs
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
    |                 |-- (else) prompt builders
    |                 |-- exact logical-prompt max-length check
    |                 |-- LLMPort → AsyncOpenAIWrapper.generate_structured(...)
    |                 |-- normalize / expected-failure fallback
    |                 '-- returns --> InputShieldOutcome
    |
    |-- writes --> state.shield_result
    |-- writes --> state.workflow_outcome
    |-- writes --> state.additional_metadata
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
                 │ fail-fast / prompts / policy │
                 │ LLMPort call / normalize     │
                 └───┬──────────────────┬───────┘
                     │                  │
                     v                  v
         ┌─────────────────────┐   ┌──────────────────────────┐
         │ input_guardrails.py │   │ input_shield_prompts.py  │
         └─────────────────────┘   └───────────┬──────────────┘
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

> The input shield node reads GraphState, invokes `InputShieldOperation`, maps the outcome into `shield_result` / `workflow_outcome` / metadata, and returns. The operation owns fail-fast checks, prompts, max-prompt policy, `LLMPort` classification, and normalization/fallback.

### Component version

> The input shield agent consists of a schema contract, heuristic guardrails, prompt builders, `InputShieldOperation` behind `LLMPort`/`AsyncOpenAIWrapper`, and a LangGraph node that owns GraphState orchestration.

---

## Η ουσία

Το σημαντικό είναι να μη λες ότι:

**“Ο input shield agent είναι ένα prompt.”**
ή ότι **το node καλεί απευθείας τον OpenAI wrapper.**

Το σωστό είναι:

**“Ο input shield είναι orchestrated safety subsystem: LangGraph node για GraphState/observability, Application Operation για prompt/LLM/use-case semantics.”**
