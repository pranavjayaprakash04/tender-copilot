from uuid import UUID

from celery import shared_task

from app.infrastructure.groq_client import GroqClient
from app.shared.logger import get_logger

from .repository import TenderMatchingRepository

logger = get_logger()


@shared_task(bind=True, name="generate_company_embedding_task")
def generate_company_embedding_task(self, company_id: str) -> None:  # noqa: ARG001
    """Generate embedding for company profile."""
    try:
        repository = TenderMatchingRepository()
        groq_client = GroqClient()

        # Fetch company profile
        profile = repository.get_company_profile(UUID(company_id))
        if not profile:
            logger.error(f"Company profile not found: {company_id}")
            return

        # Generate embedding text from profile
        embedding_text = _build_company_embedding_text(profile)

        # Generate embedding using Groq
        embedding = groq_client.generate_embedding(embedding_text)

        # Store embedding
        repository.store_company_embedding(UUID(company_id), embedding)

        logger.info(f"Generated embedding for company: {company_id}")

    except Exception as e:
        logger.error(f"Failed to generate company embedding: {e}", exc_info=True)
        raise


@shared_task(bind=True, name="match_tenders_for_company_task")
def match_tenders_for_company_task(self, company_id: str) -> None:  # noqa: ARG001
    """Match tenders for company using similarity search."""
    try:
        repository = TenderMatchingRepository()

        # Fetch company embedding
        company_embedding = repository.get_company_embedding(UUID(company_id))
        if not company_embedding:
            logger.warning(f"No embedding found for company: {company_id}")
            return

        # Run similarity search
        matches = repository.similarity_search_tenders(
            company_embedding, limit=20
        )

        # Store matches
        repository.store_tender_matches(UUID(company_id), matches)

        logger.info(f"Found {len(matches)} tender matches for company: {company_id}")

    except Exception as e:
        logger.error(f"Failed to match tenders for company: {e}", exc_info=True)
        raise


@shared_task(bind=True, name="batch_embed_new_tenders_task")
def batch_embed_new_tenders_task(self) -> None:  # noqa: ARG001
    """Generate embeddings for tenders without embeddings (Celery beat task)."""
    try:
        repository = TenderMatchingRepository()
        groq_client = GroqClient()

        # Find tenders without embeddings
        tenders = repository.get_tenders_without_embeddings(limit=10)

        for tender in tenders:
            try:
                # Generate embedding text from tender
                embedding_text = _build_tender_embedding_text(tender)

                # Generate embedding using Groq
                embedding = groq_client.generate_embedding(embedding_text)

                # Store embedding
                repository.store_tender_embedding(tender.id, embedding)

                logger.info(f"Generated embedding for tender: {tender.id}")

            except Exception as e:
                logger.error(f"Failed to embed tender {tender.id}: {e}")
                continue

        logger.info(f"Processed {len(tenders)} tenders for embedding")

    except Exception as e:
        logger.error(f"Failed to batch embed tenders: {e}", exc_info=True)
        raise


def _build_company_embedding_text(profile) -> str:
    """Build text for company embedding generation."""
    parts = [
        f"Company: {profile.name}",
        f"State: {profile.state}",
        f"Categories: {', '.join(profile.categories)}",
    ]

    if profile.capabilities:
        parts.append(f"Capabilities: {profile.capabilities}")

    if profile.turnover_range:
        parts.append(f"Turnover: {profile.turnover_range}")

    return " ".join(parts)


def _build_tender_embedding_text(tender) -> str:
    """Build text for tender embedding generation."""
    parts = [
        f"Title: {tender.title}",
        f"Organization: {tender.organization}",
        f"Category: {tender.category}",
        f"State: {tender.state}",
    ]

    if tender.description:
        parts.append(f"Description: {tender.description}")

    if tender.requirements:
        parts.append(f"Requirements: {tender.requirements}")

    return " ".join(parts)
