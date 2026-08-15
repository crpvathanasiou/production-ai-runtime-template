# 1. High-level graph flow

START
  │
  ▼
input_shield_node
  │
  ├── if shield_result.decision == "block" --------------------------► finalize_node
  │
  ├── if shield_result.decision == "needs_clarification" ------------► finalize_node
  │
  └── otherwise ------------------------------------------------------► triage_node
                                                                          │
                                                                          ▼
                                                                     planner_node
                                                                          │
                                                                          ├── if no plan ----------► finalize_node
                                                                          │
                                                                          └── otherwise -----------► execute_plan_node
                                                                                                         │
                                                                                                         ▼
                                                                                                    guardrails_node
                                                                                                         │
                                                                                                         ├── if not is_safe --------------------► human_review_node
                                                                                                         │
                                                                                                         ├── if triage requires human ----------► human_review_node
                                                                                                         │
                                                                                                         ├── if shield flagged human -----------► human_review_node
                                                                                                         │
                                                                                                         └── otherwise ------------------------► finalize_node
                                                                                                                                                  │
                                                                                                                                                  ▼
                                                                                                                                                 END


----------------------------------------------------------------------------------------------------------
# 2. Με τις εσωτερικές συναρτήσεις ανά node

Current LLM ownership (M2):

```text
input_shield_node
  → InputShieldOperation
  → PromptRepository.resolve(input-shield@1)
  → ResolvedPrompt
  → LLMPort
  → AsyncOpenAIWrapper

triage_node
  → TriageOperation
  → PromptRepository.resolve(triage@1)
  → ResolvedPrompt
  → LLMPort
  → AsyncOpenAIWrapper

planner_node
  → PlannerOperation
  → PromptRepository.resolve(planner@1)
  → ResolvedPrompt
  → LLMPort
  → AsyncOpenAIWrapper

execute_plan_node response step
  → ResponseDraftingOperation
  → PromptRepository.resolve(response-drafting@1)
  → ResolvedPrompt
  → LLMPort
  → AsyncOpenAIWrapper
```

GraphState mutations and workflow routing remain on the node/orchestration side.
Retrieval PlanStep execution remains in execute_plan (current seeded placement).
ResponseDraftingOperation owns drafting generation only — not PlanStep orchestration.
Application Operations own PromptRef resolution; nodes copy safe prompt identity
(`prompt_id`, `prompt_revision`, `prompt_content_hash`) into `additional_metadata`
when an operation outcome exists. Raw prompt content is not placed in metadata.

START
  │
  ▼
input_shield_node(state)
  │
  ├─ InputShieldOperation.execute(...)
  │    ├─ build_fail_fast_shield_output(ticket)
  │    ├─ (else) PromptRepository.resolve(input-shield@1) → ResolvedPrompt
  │    ├─ exact logical-prompt length check
  │    ├─ LLMPort → AsyncOpenAIWrapper.generate_structured(...)
  │    └─ normalization / expected-failure fallback
  └─ node writes:
       - state.shield_result
       - state.workflow_outcome
       - state.additional_metadata["input_shield"]
         (safe prompt identity when a prompt was resolved)

  │
  ▼
route_after_input_shield(state)
  │
  ├─ "block" --------------------------► finalize_node(state)
  ├─ "needs_clarification" ------------► finalize_node(state)
  └─ otherwise ------------------------► triage_node(state)


triage_node(state)
  │
  ├─ TriageOperation.execute(...)
  │    ├─ PromptRepository.resolve(triage@1) → ResolvedPrompt
  │    └─ LLMPort → AsyncOpenAIWrapper.generate_structured(...)
  └─ node writes:
       - state.triage_result
       - state.workflow_outcome
       - state.additional_metadata["triage"]
         (safe prompt identity on successful outcome)

  │
  ▼
planner_node(state)
  │
  ├─ PlannerOperation.execute(...)
  │    ├─ PromptRepository.resolve(planner@1) → ResolvedPrompt
  │    ├─ LLMPort → AsyncOpenAIWrapper.generate_structured(...)
  │    ├─ normalization
  │    └─ fallback plan [σε recoverable failure]
  └─ node writes:
       - state.agent_state.plan
       - state.agent_state.current_step_id
       - state.workflow_outcome
       - state.additional_metadata["planner"]
         (safe prompt identity on normal and handled fallback outcomes)

  │
  ▼
route_after_planner(state)
  │
  ├─ if no plan ----------------------► finalize_node(state)
  └─ otherwise -----------------------► execute_plan_node(state)


execute_plan_node(state)
  │
  ├─ loops through state.agent_state.plan
  │
  ├─ for retrieval step (current seeded placement):
  │    ├─ _build_retrieval_query(state, step)
  │    ├─ _execute_retrieval_step(state, step)
  │    │    └─ retrieve_relevant_documents(...)
  │    └─ _mark_step_completed(...) / _mark_step_failed(...)
  │
  ├─ for response step:
  │    ├─ _execute_response_step(state, step)
  │    │    ├─ ResponseDraftingOperation.execute(...)
  │    │    │    ├─ PromptRepository.resolve(response-drafting@1) → ResolvedPrompt
  │    │    │    └─ LLMPort → AsyncOpenAIWrapper.generate_structured(...)
  │    │    └─ node maps draft into state.response_draft
  │    └─ _mark_step_completed(...) / _mark_step_failed(...)
  │
  ├─ for human step:
  │    └─ _mark_step_pending(step)
  │
  ├─ _get_next_pending_step_id(updated_plan)
  └─ writes:
       - state.retrieved_documents
       - state.response_draft
       - state.agent_state.plan (updated statuses)
       - state.agent_state.current_step_id
       - state.workflow_outcome
       - state.additional_metadata["execute_plan"]
       - state.additional_metadata["response_drafting"]
         (safe prompt identity when drafting outcome exists)

  │
  ▼
guardrails_node(state)
  │
  ├─ validate_response_draft(state)
  ├─ summarize_guardrail_issues(issues)
  └─ writes:
       - state.is_safe
       - state.safety_feedback
       - state.workflow_outcome
       - state.additional_metadata["guardrails"]

  │
  ▼
route_after_guardrails(state)
  │
  ├─ if workflow_outcome == needs_human_review -----► human_review_node(state)
  ├─ if not state.is_safe --------------------------► human_review_node(state)
  ├─ if state.triage_result.requires_human_approval ► human_review_node(state)
  ├─ if state.shield_result.should_route_to_human --► human_review_node(state)
  └─ otherwise ------------------------------------► finalize_node(state)


human_review_node(state)
  │
  ├─ reads:
  │    - state.response_draft
  │    - state.safety_feedback
  │    - state.agent_state.plan
  │
  └─ writes:
       - state.human_approved
       - state.human_comments
       - state.workflow_outcome

  │
  ▼
finalize_node(state)
  │
  └─ prepares final outcome / terminal state

  │
  ▼
END


-------------------------------------------------------------------------------------------------------------
# 3. Plan → Act → Validate → Human Review mapping

PLAN
  ├─ triage_node
  └─ planner_node

ACT
  └─ execute_plan_node
       ├─ retrieval-shaped step (success if docs returned; fail if explicit retrieval returns none)
       └─ response drafting step (grounded with evidence; cautious without)

VALIDATE
  └─ guardrails_node
       └─ provenance validated against state.retrieved_documents

HUMAN-IN-THE-LOOP
  └─ human_review_node
       └─ also triggered by upstream workflow_outcome = needs_human_review

FINALIZE
  └─ finalize_node

--------------------------------------------------------------------------------------------------------
# 4. Το πιο σύντομο diagram 

input_shield_node → InputShieldOperation → PromptRepository → ResolvedPrompt → LLMPort → AsyncOpenAIWrapper
   ↓
triage_node → TriageOperation → PromptRepository → ResolvedPrompt → LLMPort → AsyncOpenAIWrapper
   ↓
planner_node → PlannerOperation → PromptRepository → ResolvedPrompt → LLMPort → AsyncOpenAIWrapper
   ↓
execute_plan_node
   ├─ _execute_retrieval_step()   (current seeded placement)
   └─ _execute_response_step() → ResponseDraftingOperation → PromptRepository → ResolvedPrompt → LLMPort → AsyncOpenAIWrapper
   ↓
guardrails_node
   ↓
human_review_node (if needed)
   ↓
finalize_node

-----------------------------------------------------------
# LLM friendly

input_shield_node
  -> triage_node
  -> planner_node
  -> execute_plan_node
      -> _execute_retrieval_step()
      -> _execute_response_step() via ResponseDraftingOperation
  -> guardrails_node
  -> human_review_node (if needed)
  -> finalize_node

1. input_shield_node validates the incoming ticket via InputShieldOperation
2. triage_node classifies the case via TriageOperation
3. planner_node produces the execution plan via PlannerOperation
4. execute_plan_node executes retrieval-shaped and drafting steps
   - retrieval returning docs → completed
   - explicit retrieval returning none → failed + needs_human_review
   - pending human PlanStep remains pending → needs_human_review
   - response drafting generation is delegated to ResponseDraftingOperation
5. guardrails validates provenance against retrieved evidence
6. route_after_guardrails preserves upstream needs_human_review
7. human_review_node treats upstream needs_human_review as review_required
8. finalize_node closes the run
