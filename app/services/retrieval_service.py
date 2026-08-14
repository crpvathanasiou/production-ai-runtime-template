from __future__ import annotations

from typing import List

from app.schemas import RetrievedDocument


def retrieve_relevant_documents(
    *,
    query: str,
    max_documents: int = 3,
) -> List[RetrievedDocument]:
    """
    Seeded retrieval entrypoint / extension seam for the example workflow.

    Preserves the workflow call site so planner → query → retrieval → drafting
    orchestration remains intact.

    Current template state:
    - no repository-level knowledge corpus is shipped;
    - no retrieval backend is active;
    - this function returns no documents.

    A later approved project/milestone may supply a real retrieval source here.
    RAG / vector retrieval remains deferred.
    """
    _ = (query, max_documents)
    return []
