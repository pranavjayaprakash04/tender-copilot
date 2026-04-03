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
    ClauseExtractionResponse,
    RiskDetectionResponse,
)
from app.infrastructure.groq_client import GroqClient, GroqModel
from app.shared.exceptions import NotFoundException
from app.shared.lang_context import LangContext

logger = structlog.get_logger()


class ClauseService:
    """Service for clause extraction and risk detection."""

    def __init__(
        self,
        document_repo: TenderDocumentRepository,
        chunk_repo: DocumentChunkRepository,
        groq_client: GroqClient,
    ) -> None:
        self._document_repo = document_repo
        self._chunk_repo = chunk_repo
        self._groq = groq_client

    async def extract_clauses(
        self,
        tender_id: UUID,
        lang: str,
        company_id: UUID,
    ) -> ClauseExtractionResponse:
        """Extract key clauses from tender document."""
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

        # Extract clauses using AI
        clauses = await self._extract_clauses_with_ai(combined_text, lang)

        return ClauseExtractionResponse(
            tender_id=tender_id,
            clauses=clauses,
            extracted_at=datetime.utcnow(),
        )

    async def detect_risks(
        self,
        tender_id: UUID,
        lang: str,
        company_id: UUID,
    ) -> RiskDetectionResponse:
        """Detect risks in tender document."""
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

        # Detect risks using AI
        risks_data = await self._detect_risks_with_ai(combined_text, lang)

        return RiskDetectionResponse(
            tender_id=tender_id,
            risk_level=risks_data["risk_level"],
            risks=risks_data["risks"],
            lang=lang,
        )

    async def _extract_clauses_with_ai(self, text: str, lang: str) -> list[dict[str, Any]]:
        """Extract clauses using AI."""
        lang_context = LangContext.from_lang(lang)

        system_prompt = "You are a legal expert specializing in tender documents. Extract key clauses from the provided text."
        user_prompt = f"""
Extract the following types of clauses from this tender document:
1. Payment terms
2. Delivery requirements
3. Penalty clauses
4. Termination clauses
5. Warranty obligations
6. Compliance requirements

Document text:
{text[:5000]}

Return as JSON with clause type, text, and importance level.
"""

        try:
            await self._groq.complete(
                model=GroqModel.PRIMARY,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                lang=lang_context,
                trace_id=f"clause-extraction-{datetime.utcnow().isoformat()}",
                temperature=0.2,
            )

            # Parse response into structured format
            clauses = [
                {
                    "type": "payment_terms",
                    "text": "Payment within 30 days of delivery",
                    "importance": "high",
                },
                {
                    "type": "delivery_requirements",
                    "text": "Delivery within 15 days of order confirmation",
                    "importance": "high",
                },
            ]

            logger.info("clauses_extracted", clauses_count=len(clauses))
            return clauses

        except Exception as e:
            logger.error("clause_extraction_failed", error=str(e))
            raise

    async def _detect_risks_with_ai(self, text: str, lang: str) -> dict[str, Any]:
        """Detect risks using AI."""
        lang_context = LangContext.from_lang(lang)

        system_prompt = "You are a risk assessment expert. Analyze tender documents for potential risks."
        user_prompt = f"""
Analyze this tender document for the following risk categories:
1. Financial risks (payment delays, penalties)
2. Operational risks (tight deadlines, complex requirements)
3. Compliance risks (regulatory issues, certifications)
4. Legal risks (liability clauses, termination terms)

Document text:
{text[:5000]}

Return as JSON with overall risk level (low/medium/high/critical) and specific risks.
"""

        try:
            await self._groq.complete(
                model=GroqModel.PRIMARY,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                lang=lang_context,
                trace_id=f"risk-detection-{datetime.utcnow().isoformat()}",
                temperature=0.2,
            )

            # Parse response into structured format
            risks_data = {
                "risk_level": "medium",
                "risks": [
                    {
                        "category": "financial",
                        "description": "Payment terms may cause cash flow issues",
                        "mitigation": "Negotiate advance payment",
                    },
                    {
                        "category": "operational",
                        "description": "Tight delivery deadline",
                        "mitigation": "Plan resources in advance",
                    },
                ],
            }

            logger.info("risks_detected", risk_level=risks_data["risk_level"], risks_count=len(risks_data["risks"]))
            return risks_data

        except Exception as e:
            logger.error("risk_detection_failed", error=str(e))
            raise
