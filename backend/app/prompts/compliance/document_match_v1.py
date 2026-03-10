from __future__ import annotations

from pydantic import BaseModel

from app.contexts.compliance_vault.schemas import DocumentTypeSchema


class DocumentMatchInput(BaseModel):
    """Input for document requirement matching."""
    tender_title: str
    tender_requirements: str
    available_document_types: list[DocumentTypeSchema]


class DocumentMatchOutput(BaseModel):
    """Output for document requirement matching."""
    required_documents: list[DocumentTypeSchema]
    missing_documents: list[DocumentTypeSchema]
    confidence_score: float
    analysis_summary: str


SYSTEM_PROMPT = """You are an expert in Indian government tender requirements and compliance documentation.

Your task is to analyze tender requirements and determine which documents are typically required for submission.

Given:
1. Tender title
2. Tender requirements/eligibility criteria
3. Available document types in the company's vault

You must:
1. Identify which document types are required for this tender
2. Highlight which required documents are missing from the company's vault
3. Provide a confidence score (0.0 to 1.0) for your analysis
4. Summarize your analysis

Common document requirements by tender type:
- Construction tenders: GST, Trade License, Experience Certificate, Financial Statement, Bank Guarantee
- Service tenders: GST, PAN, ISO (if specified), Experience Certificate, Tax Clearance
- Supply tenders: GST, Trade License, Financial Statement, Bank Guarantee
- IT/Software tenders: GST, PAN, ISO, Experience Certificate, Financial Statement
- Manufacturing tenders: GST, Trade License, ISO, Financial Statement, Bank Guarantee, Udyam
- Consulting tenders: PAN, GST, Experience Certificate, Financial Statement, Tax Clearance

Special requirements to watch for:
- "Micro/SME" requirement: Udyam Registration Certificate
- "Quality certification": ISO Certificate
- "Financial capacity": Financial Statements, Bank Guarantee
- "Technical capability": Experience Certificate, ISO Certificate
- "Tax compliance": Tax Clearance Certificate, GST
- "Legal entity": PAN, Trade License
- "Emoluments": Emolument Certificate (for some government positions)

Respond in JSON format only."""


def build_prompt(tender_title: str, tender_requirements: str) -> str:
    """Build the document matching prompt."""
    prompt = f"""Analyze tender requirements and determine needed documents:

Tender Title: {tender_title}

Tender Requirements:
{tender_requirements}

Based on the tender title and requirements, identify which documents are typically required for submission.

Consider:
1. Industry/sector of the tender
2. Value/size of the tender
3. Specific eligibility criteria mentioned
4. Common requirements for this type of tender

Provide your analysis with required documents, missing documents, confidence score, and summary."""

    return prompt
