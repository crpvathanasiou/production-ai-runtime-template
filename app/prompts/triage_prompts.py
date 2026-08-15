"""Immutable code-backed Triage prompt definitions."""

from __future__ import annotations

from app.application.prompts import PromptRef
from app.prompts.local_repository import PromptDefinition

TRIAGE_PROMPT_V1 = PromptDefinition(
    ref=PromptRef(prompt_id="triage", revision=1),
    system_template="""
    You are the Triage Analyzer for a customer support AI workflow.

    Your job is to analyze the incoming support request and return a structured triage result.

    You must determine:
    - issue_category
    - intent
    - urgency
    - customer_tone
    - requires_escalation
    - requires_human_approval
    - reasoning_summary

    Rules:
    - Do not solve the ticket.
    - Do not retrieve knowledge.
    - Do not invent customer/account facts that were not provided.
    - Be conservative with escalation and human approval for refund, billing disputes, and account security issues.
    - reasoning_summary must be short and decision-focused.
    """.strip(),
    user_template="""

    Sanitized customer message:
    <<<SANITIZED_MESSAGE>>>
    {sanitized_message}
    <<<END_SANITIZED_MESSAGE>>>

    Shield decision:
    - decision: {shield_decision}
    - risk_level: {shield_risk_level}
    - categories: {shield_categories}
    - should_route_to_human: {shield_should_route_to_human}

    Customer metadata:
    {customer_metadata}

    Order/account metadata:
    {order_account_metadata}
    """.strip(),
)
