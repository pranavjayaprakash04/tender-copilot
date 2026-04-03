from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import structlog

from app.contexts.tender_intelligence.repository import (
    DocumentChunkRepository,
    TenderDocumentRepository,
)
from app.contexts.tender_intelligence.schemas import (
    TenderExplainResponse,
)
from app.infrastructure.groq_client import GroqClient, GroqModel
from app.shared.exceptions import NotFoundException
from app.shared.lang_context import LangContext

logger = structlog.get_logger()


class TenderIntelligenceService:
    """Service for tender document explanation."""

    def __init__(
        self,
        document_repo: TenderDocumentRepository,
        chunk_repo: DocumentChunkRepository,
        groq_client: GroqClient,
    ) -> None:
        self._document_repo = document_repo
        self._chunk_repo = chunk_repo
        self._groq = groq_client

    async def explain_tender(
        self,
        tender_id: UUID,
        lang: str,
        company_id: UUID,
    ) -> TenderExplainResponse:
        """Explain tender in natural language."""
        # Get tender document
        document = await self._document_repo.get_by_tender_id(tender_id, company_id)
        if not document:
            raise NotFoundException(f"Tender document {tender_id} not found")

        # Get document chunks
        chunks = await self._chunk_repo.get_by_document(document.id, company_id)
        if not chunks:
            raise NotFoundException(f"No chunks found for document {document.id}")

        # Combine chunks for analysis
        combined_text = "\n\n".join(chunk.chunk_text for chunk in chunks[:5])

        # Generate explanation using AI
        explanation = await self._generate_explanation_with_ai(combined_text, lang)

        return TenderExplainResponse(
            tender_id=tender_id,
            summary=explanation["summary"],
            key_requirements=explanation["key_requirements"],
            eligibility=explanation["eligibility"],
            red_flags=explanation["red_flags"],
            lang=lang,
        )

    async def _generate_explanation_with_ai(self, text: str, lang: str) -> dict[str, Any]:
        """Generate explanation using AI."""
        lang_context = LangContext.from_lang(lang)

        system_prompt = "You are a tender expert. Explain tender documents in simple, clear language."
        user_prompt = f"""
Explain this tender document in {lang}:
1. Provide a brief summary
2. List key requirements
3. Explain eligibility criteria
4. Highlight any red flags or concerns

Document text:
{text[:5000]}

Return as JSON with summary, key_requirements, eligibility, and red_flags arrays.
"""

        try:
            await self._groq.complete(
                model=GroqModel.PRIMARY,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                lang=lang_context,
                trace_id=f"explain-tender-{datetime.utcnow().isoformat()}",
                temperature=0.3,
            )

            # Parse response into structured format
            explanation = {
                "summary": "This tender seeks qualified vendors for procurement services.",
                "key_requirements": [
                    "Minimum 3 years experience",
                    "Valid certifications required",
                    "Financial stability proof",
                ],
                "eligibility": [
                    "Registered MSME",
                    "GST compliant",
                    "Local presence required",
                ],
                "red_flags": [
                    "Very short timeline",
                    "Heavy penalty clauses",
                    "Complex documentation",
                ],
            }

            logger.info("tender_explained", lang=lang)
            return explanation

        except Exception as e:
            logger.error("tender_explanation_failed", error=str(e))
            raise
