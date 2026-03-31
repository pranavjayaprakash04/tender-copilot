from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

import structlog
from pydantic import BaseModel

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


# ─── Groq Output Schemas ───────────────────────────────────────────────────────

class _ChecklistItemRaw(BaseModel):
    id: str = "doc_0"
    name: str = "Unknown Document"
    description: str = ""
    required: bool = True
    in_vault: bool = False
    status: Literal["have", "missing", "unknown"] = "missing"
    notes: str | None = None


class _ChecklistGroqResponse(BaseModel):
    checklist: list[_ChecklistItemRaw] = []


class _ExplainGroqResponse(BaseModel):
    summary: str = ""
    key_requirements: list[str] = []
    eligibility: list[str] = []
    red_flags: list[str] = []


# ─── Service ───────────────────────────────────────────────────────────────────

class TenderIntelligenceService:
    def __init__(
        self,
        document_repo: TenderDocumentRepository,
        chunk_repo: DocumentChunkRepository,
        groq_client: GroqClient,
    ) -> None:
        self._document_repo = document_repo
        self._chunk_repo = chunk_repo
        self._groq = groq_client

    async def explain_tender(self, tender_id: UUID, lang: str, company_id: UUID) -> TenderExplainResponse:
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
            summary=explanation.summary,
            key_requirements=explanation.key_requirements,
            eligibility=explanation.eligibility,
            red_flags=explanation.red_flags,
            lang=lang,
        )

    async def _generate_explanation_with_ai(self, text: str, lang: str) -> _ExplainGroqResponse:
        system_prompt = "You are a tender expert. Explain tender documents in simple, clear language."
        user_prompt = f"""Explain this tender document in {lang}:

{text[:5000]}

Return JSON with these fields: summary (string), key_requirements (array of strings), eligibility (array of strings), red_flags (array of strings)."""
        try:
            result = await self._groq.complete(
                model=GroqModel.PRIMARY,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=_ExplainGroqResponse,
                trace_id=f"explain-tender-{datetime.utcnow().isoformat()}",
                temperature=0.3,
            )
            logger.info("tender_explained", lang=lang)
            return result
        except Exception as e:
            logger.error("tender_explanation_failed", error=str(e))
            raise

    # ─── Document Checklist ────────────────────────────────────────────────────

    async def generate_document_checklist(
        self, request: DocumentChecklistRequest, company_id: UUID
    ) -> DocumentChecklistResponse:
        vault_doc_names: list[str] = []

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
        self, request: DocumentChecklistRequest, vault_doc_names: list[str]
    ) -> list[ChecklistItem]:
        system_prompt = (
            "You are an Indian government tender expert. "
            "Generate a precise list of documents required to bid on a tender. "
            "Return ONLY valid JSON."
        )
        user_prompt = f"""Generate a document checklist for this tender:

Tender: {request.tender_title}
Category: {request.tender_category or "General"}
Estimated Value: {request.estimated_value or "Not specified"}
Location: {request.tender_location or "India"}
Description: {(request.description or "")[:1000]}

Return JSON with a "checklist" array of 8-12 items. Each item must have:
- id (string like "doc_1")
- name (document name)
- description (what this document is)
- required (true/false)
- in_vault (false)
- status ("missing")
- notes (optional tip or null)"""

        import traceback
        try:
            logger.info("calling_groq_checklist", tender_id=request.tender_id)
            result = await self._groq.complete(
                model=GroqModel.FAST,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=_ChecklistGroqResponse,
                trace_id=f"checklist-{request.tender_id}",
                temperature=0.2,
            )
            logger.info("groq_checklist_done", count=len(result.checklist))
            if result.checklist:
                return [
                    ChecklistItem(
                        id=item.id,
                        name=item.name,
                        description=item.description,
                        required=item.required,
                        in_vault=item.in_vault,
                        status=item.status,
                        notes=item.notes,
                    )
                    for item in result.checklist
                ]
        except Exception as e:
            logger.error("checklist_generation_failed", error=str(e), tb=traceback.format_exc())

        # Fallback defaults
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
                in_vault=False,
                status="missing",
                notes=None,
            )
            for i, (name, desc) in enumerate(defaults)
        ]
