from __future__ import annotations

import re
import tempfile
from datetime import datetime
from typing import dict
from uuid import UUID

import pdfplumber
import structlog

from app.contexts.tender_intelligence.models import (
    DocumentChunk,
    DocumentType,
    ProcessingStatus,
    TenderDocument,
    TenderIntelligenceReport,
)
from app.contexts.tender_intelligence.repository import (
    DocumentChunkRepository,
    TenderDocumentRepository,
    TenderIntelligenceReportRepository,
)
from app.contexts.tender_intelligence.schemas import (
    TenderIntelligenceReportCreate,
)
from app.infrastructure.groq_client import GroqClient, GroqModel
from app.infrastructure.storage import StorageClient
from app.prompts.tender.tender_analysis_v1 import (
    TenderAnalysisOutput,
    get_system_prompt,
    get_tender_analysis_prompt,
)
from app.shared.exceptions import ValidationException
from app.shared.lang_context import LangContext

logger = structlog.get_logger()


class TenderIntelligenceService:
    """Service for tender document processing and AI analysis."""

    def __init__(
        self,
        document_repo: TenderDocumentRepository,
        chunk_repo: DocumentChunkRepository,
        report_repo: TenderIntelligenceReportRepository,
        groq_client: GroqClient,
        storage_client: StorageClient
    ) -> None:
        self._document_repo = document_repo
        self._chunk_repo = chunk_repo
        self._report_repo = report_repo
        self._groq = groq_client
        self._storage = storage_client

    async def process_document(
        self,
        document_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> TenderDocument:
        """Process a tender document with PDF parsing and AI analysis."""
        document = await self._document_repo.get_by_id(document_id, company_id)

        # Update status to processing
        await self._document_repo.update_status(
            document_id, ProcessingStatus.PROCESSING, trace_id
        )

        try:
            # Extract text from PDF
            extracted_text = await self._extract_pdf_text(document.file_path)

            # Create document chunks
            chunks = await self._create_document_chunks(document_id, extracted_text)

            # Generate AI analysis
            analysis = await self._generate_ai_analysis(
                document, chunks, LangContext.from_lang("en"), trace_id
            )

            # Update document with results
            updated_document = await self._document_repo.update_with_analysis(
                document_id, extracted_text, analysis, trace_id
            )

            logger.info(
                "document_processed_successfully",
                trace_id=trace_id,
                document_id=document_id,
                text_length=len(extracted_text),
                chunks_created=len(chunks),
                confidence_score=analysis.get("confidence_score")
            )

            return updated_document

        except Exception as e:
            # Update status to failed
            await self._document_repo.update_with_error(
                document_id, str(e), trace_id
            )

            logger.error(
                "document_processing_failed",
                trace_id=trace_id,
                document_id=document_id,
                error=str(e)
            )

            raise

    async def _extract_pdf_text(self, storage_path: str) -> str:
        """Extract text from PDF using storage wrapper and temp file."""
        temp_file_path = None
        try:
            # Download file bytes from storage
            file_bytes = await self._storage.download_file(storage_path)

            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(file_bytes)
                temp_file_path = temp_file.name

            # Extract text using pdfplumber
            text_content = []

            with pdfplumber.open(temp_file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Extract text from page
                    page_text = page.extract_text()

                    if page_text.strip():
                        # Clean up text
                        cleaned_text = self._clean_text(page_text)
                        text_content.append(f"--- Page {page_num + 1} ---\n{cleaned_text}")

            return "\n\n".join(text_content)

        except Exception as e:
            logger.error("pdf_extraction_failed", storage_path=storage_path, error=str(e))
            raise ValidationException(f"Failed to extract text from PDF: {e}")
        finally:
            # Clean up temporary file
            if temp_file_path:
                import os
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    logger.warning("temp_file_cleanup_failed", temp_file_path=temp_file_path, error=str(e))

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove special characters that might cause issues
        text = re.sub(r'[^\w\s\.\,\-\:\;\(\)\[\]\{\}\/\@\#\$\%\&\*\+\=\?\!\|\\]', '', text)

        # Fix line breaks
        text = re.sub(r'\.\s+', '.\n', text)
        text = re.sub(r'\:\s+', ':\n', text)

        return text.strip()

    async def _create_document_chunks(
        self,
        document_id: UUID,
        text: str
    ) -> list[DocumentChunk]:
        """Create document chunks for embedding and search."""
        chunks = []

        # Split text into manageable chunks (approximately 500 words)
        words = text.split()
        chunk_size = 500
        overlap = 50  # Overlap between chunks for context

        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            chunk_text = ' '.join(chunk_words)

            # Skip very short chunks
            if len(chunk_words) < 50:
                continue

            chunk = await self._chunk_repo.create({
                "document_id": document_id,
                "chunk_text": chunk_text,
                "chunk_type": "text",
                "chunk_index": i // (chunk_size - overlap),
                "word_count": len(chunk_words)
            })

            chunks.append(chunk)

        return chunks

    async def _generate_ai_analysis(
        self,
        document: TenderDocument,
        chunks: list[DocumentChunk],
        lang: LangContext,
        trace_id: str | None = None
    ) -> dict:
        """Generate AI analysis using Groq."""
        # Combine chunks for analysis (limit to prevent token overflow)
        combined_text = "\n\n".join(
            chunk.chunk_text for chunk in chunks[:10]  # Limit to first 10 chunks
        )

        # Get appropriate prompt based on language
        prompt = get_tender_analysis_prompt(lang.lang_code)
        system_prompt = get_system_prompt()

        # Create user prompt with document content
        user_prompt = f"""
Document Type: {document.document_type}
Filename: {document.original_filename}
Language: {lang.lang_code}

Document Content:
{combined_text[:8000]}  # Limit to prevent token overflow

{prompt}
"""

        try:
            start_time = datetime.utcnow()

            # Call Groq for analysis
            result = await self._groq.complete(
                model=GroqModel.PRIMARY,  # Use llama-3.3-70b-versatile for quality intelligence analysis
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=TenderAnalysisOutput,
                lang=lang,
                trace_id=trace_id or f"analysis-{document.id}",
                company_id=str(document.company_id),
                temperature=0.3
            )

            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Convert to dict for storage
            analysis_dict = result.model_dump()
            analysis_dict["processing_time_ms"] = int(processing_time)

            logger.info(
                "ai_analysis_completed",
                trace_id=trace_id,
                document_id=document.id,
                confidence_score=analysis_dict.get("confidence_score"),
                processing_time_ms=processing_time
            )

            return analysis_dict

        except Exception as e:
            logger.error(
                "ai_analysis_failed",
                trace_id=trace_id,
                document_id=document.id,
                error=str(e)
            )
            raise

    async def generate_intelligence_report(
        self,
        tender_id: UUID,
        company_id: UUID,
        report_type: str = "summary",
        language: str = "en",
        trace_id: str | None = None
    ) -> TenderIntelligenceReport:
        """Generate comprehensive intelligence report for a tender."""
        # Get all processed documents for the tender
        documents = await self._document_repo.get_by_tender(tender_id, company_id)

        if not documents:
            raise ValidationException("No processed documents found for this tender")

        # Combine analysis from all documents
        combined_analysis = await self._combine_document_analyses(documents, language, trace_id)

        # Create intelligence report
        report_data = TenderIntelligenceReportCreate(
            tender_id=tender_id,
            report_type=report_type,
            language=language,
            ai_model="llama-3.3-70b-versatile",
            ai_prompt_version="v1",
            processing_time_ms=combined_analysis["total_processing_time"],
            confidence_score=combined_analysis["average_confidence"],
            executive_summary=combined_analysis["executive_summary"],
            key_findings=combined_analysis["key_findings"],
            risk_assessment=combined_analysis["risk_assessment"],
            recommendations=combined_analysis["recommendations"],
            source_document_ids=[doc.id for doc in documents],
            total_documents_analyzed=len(documents),
            total_pages_processed=sum(doc.page_count or 0 for doc in documents),
            completeness_score=combined_analysis["completeness_score"],
            accuracy_score=combined_analysis["accuracy_score"],
            relevance_score=combined_analysis["relevance_score"]
        )

        report = await self._report_repo.create(report_data)

        logger.info(
            "intelligence_report_generated",
            trace_id=trace_id,
            tender_id=tender_id,
            report_type=report_type,
            language=language,
            documents_analyzed=len(documents)
        )

        return report

    async def _combine_document_analyses(
        self,
        documents: list[TenderDocument],
        language: str,
        trace_id: str | None = None
    ) -> dict:
        """Combine analyses from multiple documents."""
        combined_analysis = {
            "executive_summary": "",
            "key_findings": {},
            "risk_assessment": {},
            "recommendations": {},
            "total_processing_time": 0,
            "average_confidence": 0,
            "completeness_score": 85,
            "accuracy_score": 90,
            "relevance_score": 88
        }

        total_confidence = 0
        processing_times = []

        for doc in documents:
            if doc.ai_summary:
                if not combined_analysis["executive_summary"]:
                    combined_analysis["executive_summary"] = doc.ai_summary
                else:
                    combined_analysis["executive_summary"] += f"\n\n{doc.ai_summary}"

            # Combine key requirements
            if doc.ai_key_requirements:
                for key, value in doc.ai_key_requirements.items():
                    if key not in combined_analysis["key_findings"]:
                        combined_analysis["key_findings"][key] = value

            # Combine risk factors
            if doc.ai_risk_factors:
                for risk in doc.ai_risk_factors:
                    if "risks" not in combined_analysis["risk_assessment"]:
                        combined_analysis["risk_assessment"]["risks"] = []
                    combined_analysis["risk_assessment"]["risks"].append(risk)

            # Combine recommendations
            if doc.ai_recommendations:
                for rec in doc.ai_recommendations:
                    if "actions" not in combined_analysis["recommendations"]:
                        combined_analysis["recommendations"]["actions"] = []
                    combined_analysis["recommendations"]["actions"].append(rec)

            if doc.ai_confidence_score:
                total_confidence += doc.ai_confidence_score

            if doc.ai_processing_time:
                processing_times.append(doc.ai_processing_time)

        # Calculate averages
        if documents:
            combined_analysis["average_confidence"] = total_confidence / len(documents)
            combined_analysis["total_processing_time"] = sum(processing_times)

        return combined_analysis

    async def search_documents(
        self,
        company_id: UUID,
        query: str,
        document_type: DocumentType | None = None,
        language: str | None = None,
        trace_id: str | None = None
    ) -> list[TenderDocument]:
        """Search documents by content and metadata."""
        filters = {}
        if document_type:
            filters["document_type"] = document_type
        if language:
            filters["language_detected"] = language

        documents, total = await self._document_repo.search(
            company_id, query, filters, trace_id
        )

        logger.info(
            "documents_searched",
            trace_id=trace_id,
            company_id=company_id,
            query=query,
            results_count=len(documents),
            total_results=total
        )

        return documents

    async def get_document_chunks(
        self,
        document_id: UUID,
        company_id: UUID,
        trace_id: str | None = None
    ) -> list[DocumentChunk]:
        """Get all chunks for a document."""
        chunks = await self._chunk_repo.get_by_document(document_id, company_id)

        logger.info(
            "document_chunks_retrieved",
            trace_id=trace_id,
            document_id=document_id,
            chunks_count=len(chunks)
        )

        return chunks

    async def retry_failed_processing(
        self,
        company_id: UUID,
        trace_id: str | None = None
    ) -> list[TenderDocument]:
        """Retry processing of failed documents."""
        failed_documents = await self._document_repo.get_retryable(company_id)

        retried = []
        for document in failed_documents:
            try:
                await self.process_document(document.id, company_id, trace_id)
                retried.append(document)
            except Exception as e:
                logger.error(
                    "document_retry_failed",
                    trace_id=trace_id,
                    document_id=document.id,
                    error=str(e)
                )

        logger.info(
            "failed_documents_retried",
            trace_id=trace_id,
            company_id=company_id,
            retried_count=len(retried),
            total_failed=len(failed_documents)
        )

        return retried
