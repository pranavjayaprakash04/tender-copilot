from __future__ import annotations

from datetime import datetime
from typing import Literal
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


# ─── Category-based document templates ────────────────────────────────────────

_CATEGORY_DOCS: dict[str, list[tuple[str, str, str | None]]] = {
    "works": [
        ("GST Registration Certificate", "Valid GST registration certificate", None),
        ("PAN Card", "Company PAN card copy", None),
        ("Udyam / MSME Certificate", "MSME registration certificate if applicable", None),
        ("Contractor Registration Certificate", "Valid contractor registration with appropriate class", "Must match tender value category"),
        ("Audited Balance Sheet", "Last 3 years audited financial statements", None),
        ("Bank Solvency Certificate", "Certificate from bank confirming solvency", None),
        ("Experience Certificate", "Work completion certificates from previous similar projects", "Must show experience in similar civil works"),
        ("EMD / Bid Security", "Earnest money deposit in prescribed format", None),
        ("Performance Security", "Bank guarantee or FDR for performance security", None),
        ("Power of Attorney", "Authorisation letter for signatory", None),
    ],
    "services": [
        ("GST Registration Certificate", "Valid GST registration certificate", None),
        ("PAN Card", "Company PAN card copy", None),
        ("Udyam / MSME Certificate", "MSME registration certificate if applicable", None),
        ("Audited Balance Sheet", "Last 3 years audited financial statements", None),
        ("Bank Solvency Certificate", "Certificate from bank confirming financial capacity", None),
        ("Experience Certificate", "Certificates from previous clients for similar services", "Must demonstrate relevant service experience"),
        ("Technical Qualification Certificate", "Proof of technical qualifications and certifications", None),
        ("EMD / Bid Security", "Earnest money deposit document", None),
        ("Staff Qualification Documents", "CVs and certificates of key personnel to be deployed", None),
        ("Power of Attorney", "Authorisation letter for signatory", None),
    ],
    "goods": [
        ("GST Registration Certificate", "Valid GST registration certificate", None),
        ("PAN Card", "Company PAN card copy", None),
        ("Udyam / MSME Certificate", "MSME registration certificate if applicable", None),
        ("Manufacturer/Dealer Authorization", "Authorization from manufacturer if applicable", None),
        ("Audited Balance Sheet", "Last 3 years audited financial statements", None),
        ("Product Specifications / Brochure", "Technical specifications and product brochure", None),
        ("Sample / Test Report", "Product sample or third-party test report", "May be required for quality verification"),
        ("EMD / Bid Security", "Earnest money deposit document", None),
        ("Experience Certificate", "Supply orders from previous clients", None),
        ("Power of Attorney", "Authorisation letter for signatory", None),
    ],
    "it": [
        ("GST Registration Certificate", "Valid GST registration certificate", None),
        ("PAN Card", "Company PAN card copy", None),
        ("Udyam / MSME Certificate", "MSME registration certificate if applicable", None),
        ("ISO/CMM Certification", "ISO 9001 or CMMI certification if applicable", None),
        ("Audited Balance Sheet", "Last 3 years audited financial statements", None),
        ("Past Project Experience", "Work orders and completion certificates for similar IT projects", None),
        ("Technical Team Profiles", "CVs of key technical staff to be deployed", None),
        ("EMD / Bid Security", "Earnest money deposit document", None),
        ("OEM Authorization", "Authorization from OEM for products to be supplied", "Required if reselling hardware/software"),
        ("Power of Attorney", "Authorisation letter for signatory", None),
    ],
    "consultancy": [
        ("GST Registration Certificate", "Valid GST registration certificate", None),
        ("PAN Card", "Company PAN card copy", None),
        ("Firm Registration Certificate", "Certificate of incorporation / firm registration", None),
        ("Audited Balance Sheet", "Last 3 years audited financial statements", None),
        ("Relevant Experience Certificate", "Completion certificates for similar consultancy assignments", None),
        ("Key Personnel CVs", "Detailed CVs of team leader and key experts", "Must meet minimum qualification criteria"),
        ("Technical Proposal", "Detailed technical approach and methodology", None),
        ("Financial Proposal (BOQ)", "Itemised financial proposal / BOQ", None),
        ("EMD / Bid Security", "Earnest money deposit document", None),
        ("Power of Attorney", "Authorisation letter for signatory", None),
    ],
}

_DEFAULT_DOCS = _CATEGORY_DOCS["services"]


def _get_docs_for_category(category: str | None, title: str) -> list[tuple[str, str, str | None]]:
    if not category:
        category = ""
    cat = category.lower()
    title_lower = title.lower()

    if any(k in cat or k in title_lower for k in ["work", "civil", "construction", "road", "bridge", "building"]):
        return _CATEGORY_DOCS["works"]
    if any(k in cat or k in title_lower for k in ["it", "software", "hardware", "computer", "digital", "cyber", "network"]):
        return _CATEGORY_DOCS["it"]
    if any(k in cat or k in title_lower for k in ["consult", "advisory", "study", "survey", "design"]):
        return _CATEGORY_DOCS["consultancy"]
    if any(k in cat or k in title_lower for k in ["good", "supply", "purchase", "procurement", "equipment", "material"]):
        return _CATEGORY_DOCS["goods"]
    if "service" in cat or "service" in title_lower:
        return _CATEGORY_DOCS["services"]
    return _DEFAULT_DOCS


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
        checklist_items = self._generate_checklist_from_category(request)

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

        logger.info("checklist_generated", tender_id=request.tender_id, total=total, category=request.tender_category)

        return DocumentChecklistResponse(
            tender_id=request.tender_id,
            checklist=checklist_items,
            total=total,
            have_count=have_count,
            missing_count=missing_count,
            readiness_score=readiness_score,
            summary=summary,
        )

    def _generate_checklist_from_category(self, request: DocumentChecklistRequest) -> list[ChecklistItem]:
        docs = _get_docs_for_category(request.tender_category, request.tender_title)
        return [
            ChecklistItem(
                id=f"doc_{i}",
                name=name,
                description=desc,
                required=True,
                in_vault=False,
                status="missing",
                notes=note,
            )
            for i, (name, desc, note) in enumerate(docs)
        ]
