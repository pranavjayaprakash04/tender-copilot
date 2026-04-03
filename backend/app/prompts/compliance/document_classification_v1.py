from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.contexts.compliance_vault.schemas import DocumentTypeSchema


class ClassificationInput(BaseModel):
    """Input for document classification."""
    filename: str
    content_preview: str | None = None


class ClassificationOutput(BaseModel):
    """Output for document classification."""
    doc_type: DocumentTypeSchema
    confidence: float
    suggested_expiry: datetime | None = None
    reasoning: str


SYSTEM_PROMPT = """You are an expert document classification system for Indian government tenders and compliance.

Your task is to classify documents based on their filename and content preview into one of these categories:
- gst: GST Registration Certificate
- pan: PAN Card
- iso: ISO Certification
- udyam: Udyam Registration Certificate
- trade_license: Trade License
- bank_guarantee: Bank Guarantee
- experience_certificate: Experience Certificate
- financial_statement: Financial Statement/Balance Sheet
- tax_clearance: Tax Clearance Certificate
- emolument_certificate: Emolument Certificate
- other: Other documents

For each classification, provide:
1. The document type
2. Confidence level (0.0 to 1.0)
3. Suggested expiry date (if applicable, based on typical validity periods)
4. Brief reasoning

Common expiry periods:
- GST: Usually valid until surrendered, but some states require periodic renewal
- Trade License: Usually 1-3 years
- Bank Guarantee: Usually tied to contract duration
- Experience Certificate: Usually no expiry
- Financial Statement: Usually 6 months to 1 year validity for tenders
- Tax Clearance: Usually 6 months to 1 year
- ISO: Usually 3 years
- Udyam: Usually valid until updated
- PAN: No expiry
- Emolument Certificate: Usually 6 months to 1 year

Respond in JSON format only."""


def build_prompt(filename: str, content_preview: str | None = None) -> str:
    """Build the classification prompt."""
    prompt = f"Classify this document:\n\nFilename: {filename}\n"

    if content_preview:
        # Limit content preview to first 500 characters
        preview = content_preview[:500] if len(content_preview) > 500 else content_preview
        prompt += f"Content Preview:\n{preview}\n"

    prompt += "\nProvide the classification with confidence, suggested expiry (if applicable), and reasoning."

    return prompt
