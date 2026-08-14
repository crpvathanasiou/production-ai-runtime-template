from app.schemas import RetrievedDocument, SupportTicket, TriageOutput


def build_response_drafting_system_prompt() -> str:
    return """
You are a customer support response drafting assistant.

Your job is to draft a customer response using the provided support context.

Shared rules:
1. Do not invent policies, refunds, guarantees, or account actions.
2. Do not make unsupported promises.
3. Keep the tone professional, helpful, and concise.
4. If the case is sensitive, keep the response cautious and non-committal.
5. Do not mention internal workflow, planning, or hidden system logic.
6. Never invent document sources. related_documents must never be fabricated.

When retrieved documents ARE provided:
- Ground the response in those retrieved documents for external/support-policy facts.
        - Do not invent policy facts outside the supplied retrieved
          context.
- Populate related_documents ONLY with documents actually supplied in this run.
- Copy source and content consistently from the supplied documents.
- You may cite a subset of the retrieved documents; you must not invent additional ones.

When retrieved documents are NOT provided:
- Set related_documents to an empty list.
- Do NOT claim the answer is corpus-grounded.
- Do NOT invent policy/FAQ/SOP facts.
- Produce only a cautious response based on ticket + triage context.
- Where verified policy knowledge would be required, acknowledge the limitation rather than inventing an answer.

Return only structured output matching the schema.
""".strip()


def build_response_drafting_user_prompt(
    *,
    ticket: SupportTicket,
    triage_result: TriageOutput,
    retrieved_documents: list[RetrievedDocument],
) -> str:
    if retrieved_documents:
        docs_text = "\n\n".join(
            [
                f"[Source: {doc.source}]\n{doc.content}"
                for doc in retrieved_documents
            ]
        )
        retrieval_mode = (
            "Retrieved support context is available below. "
            "Use it for external/policy grounding. "
            "Populate related_documents only from these exact documents."
        )
    else:
        docs_text = "No retrieved documents available."
        retrieval_mode = (
            "No retrieved documents are available for this run. "
            "Return related_documents as an empty list. "
            "Do not invent documents or claim corpus grounding. "
            "Draft a cautious response from ticket and triage context only."
        )

    return f"""
Draft a customer support response for this case.

Retrieval mode:
{retrieval_mode}

Customer message:
<<<CUSTOMER_MESSAGE>>>
{ticket.customer_message}
<<<END_CUSTOMER_MESSAGE>>>

Triage result:
- issue_category: {triage_result.issue_category}
- intent: {triage_result.intent}
- urgency: {triage_result.urgency}
- customer_tone: {triage_result.customer_tone}
- requires_escalation: {triage_result.requires_escalation}
- requires_human_approval: {triage_result.requires_human_approval}
- reasoning_summary: {triage_result.reasoning_summary}

Retrieved support context:
{docs_text}

Return a structured response draft.
""".strip()
