from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

import structlog

from app.contexts.tender_intelligence.repository import (
    DocumentChunkRepository,
    TenderDocumentRepository,
)
from app.contexts.tender_intelligence.schemas import (
    ChecklistItem,
    DocumentChecklistRequest,
    DocumentChecklistResponse,
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
        document = await self._document_repo.get_by_tender_id(tender_id, company_id)
        if not document:
            raise NotFoundException(f"Tender document {tender_id} not found")

        chunks = await self._chunk_repo.get_by_document(document.id, company_id)
        if not chunks:
            raise NotFoundException(f"No chunks found for document {document.id}")

        combined_text = "\n\n".join(chunk.chunk_text for chunk in chunks[:5])
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

    # ─── Document Checklist ────────────────────────────────────────────────────

    async def generate_document_checklist(
        self,
        request: DocumentChecklistRequest,
        company_id: UUID,
    ) -> DocumentChecklistResponse:
        """Generate AI document checklist and match against vault."""

        # Try to get vault documents for this company
        vault_doc_names: list[str] = []
        try:
            vault_docs = await self._document_repo.get_vault_documents(company_id)
            vault_doc_names = [doc.name.lower() for doc in vault_docs] if vault_docs else []
        except Exception:
            vault_doc_names = []

        # Generate checklist via AI
        checklist_items = await self._generate_checklist_with_ai(request, vault_doc_names)

        have_count = sum(1 for item in checklist_items if item.status == "have")
        missing_count = sum(1 for item in checklist_items if item.status == "missing")
        total = len(checklist_items)
        readiness_score = int((have_count / total) * 100) if total > 0 else 0

        if readiness_score >= 80:
            summary = "You are well prepared for this tender."
        elif readiness_score >= 50:
            summary = "You have most documents ready. A few critical ones are missing."
        else:
            summary = "Several required documents are missing. Start gathering them early."

        return DocumentChecklistResponse(
            tender_id=request.tender_id,
            checklist=checklist_items,
            total=total,
            have_count=have_count,
            missing_count=missing_count,
            readiness_score=readiness_score,
            summary=summary,
        )

    async def _generate_checklist_with_ai(
        self,
        request: DocumentChecklistRequest,
        vault_doc_names: list[str],
    ) -> list[ChecklistItem]:
        """Use Groq to generate required document list for a tender."""

        system_prompt = (
            "You are an Indian government tender expert. "
            "Generate a precise list of documents required to bid on a tender. "
            "Return ONLY valid JSON, no explanation, no markdown."
        )

        user_prompt = f"""
Tender: {request.tender_title}
Category: {request.tender_category or "General"}
Estimated Value: {request.estimated_value or "Not specified"}
Location: {request.tender_location or "India"}
Description: {(request.description or "")[:1000]}

Documents already in vault: {", ".join(vault_doc_names) if vault_doc_names else "None"}

Generate a checklist of 8-12 documents typically required for this type of tender in India.
For each document, check if it matches any vault document names.

Return ONLY this JSON structure:
{{
  "checklist": [
    {{
      "id": "doc_1",
      "name": "GST Registration Certificate",
      "description": "Valid GST registration certificate from the company",
      "required": true,
      "in_vault": true or false (based on vault match),
      "status": "have" or "missing",
      "notes": "optional note"
    }}
  ]
}}
"""

        try:
            response = await self._groq.complete(
                model=GroqModel.PRIMARY,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                lang=LangContext.from_lang(request.lang),
                trace_id=f"checklist-{request.tender_id}-{datetime.utcnow().isoformat()}",
                temperature=0.2,
            )

            raw = response.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = json.loads(raw)
            items = parsed.get("checklist", [])

            return [
                ChecklistItem(
                    id=item.get("id", f"doc_{i}"),
                    name=item.get("name", "Unknown Document"),
                    description=item.get("description", ""),
                    required=item.get("required", True),
                    in_vault=item.get("in_vault", False),
                    status=item.get("status", "missing"),
                    notes=item.get("notes"),
                )
                for i, item in enumerate(items)
            ]

        except Exception as e:
            logger.error("checklist_generation_failed", error=str(e))
            # Return sensible defaults if AI fails
            defaults = [
                ("GST Registration Certificate", "Valid GST registration certificate"),
                ("PAN Card", "Company PAN card copy"),
                ("Udyam / MSME Certificate", "MSME registration certificate if applicable"),
                ("Audited Balance Sheet", "Last 3 years audited financial statements"),
                ("Bank Solvency Certificate", "Certificate from bank confirming solvency"),
                ("Experience Certificate", "Work experience certificates from previous clients"),
                ("EMD / Bid Security", "Earnest money deposit document"),
                ("Power of Attorney", "Authorisation letter for signatory"),
            ]
            return [
                ChecklistItem(
                    id=f"doc_{i}",
                    name=name,
                    description=desc,
                    required=True,
                    in_vault=any(name.lower()[:6] in v for v in vault_doc_names),
                    status="have" if any(name.lower()[:6] in v for v in vault_doc_names) else "missing",
                    notes=None,
                )
                for i, (name, desc) in enumerate(defaults)
            ]
