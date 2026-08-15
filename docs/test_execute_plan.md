# execute_plan tests (current semantics)

Node tests fake `ResponseDraftingOperation` (not the OpenAI wrapper) for drafting paths.
Successful drafting outcomes carry `PromptIdentity`; the node copies safe identity fields into metadata.
Retrieval / human-review behavioural regressions remain intact.

Covers:

1. **Mocked retrieval success** — RAG-ready seam:
   retrieval step populates `retrieved_documents` and completes.
2. **Current inert entrypoint** — explicit retrieval returning `[]` fails the
   retrieval step with `"Retrieval returned no documents."` and sets
   `workflow_outcome = needs_human_review`. A cautious draft may still be created.
3. **Grounded drafting** — with `state.retrieved_documents`, response result is
   `"Drafted grounded customer response."`
4. **No-retrieval drafting** — with empty retrieved evidence and
   `related_documents = []`, result is
   `"Drafted customer response without retrieved context."`
5. **Drafting failure recovery** — failed response step + pending human step →
   `needs_human_review`
