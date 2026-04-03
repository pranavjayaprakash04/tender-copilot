from __future__ import annotations

from pydantic import BaseModel

from app.contexts.tender_discovery.schemas import TenderCategory, TenderPriority


class ClassificationInput(BaseModel):
    """Input for tender classification."""
    title: str
    description: str
    procuring_entity: str
    estimated_value: float | None = None


class ClassificationOutput(BaseModel):
    """Output for tender classification."""
    category: TenderCategory
    subcategory: str | None
    priority: TenderPriority
    confidence: float
    reasoning: str


SYSTEM_PROMPT = """You are an expert in Indian government tender classification and procurement analysis.

Your task is to classify tenders into appropriate categories, determine their priority, and provide reasoning.

Categories available:
- construction: Building, infrastructure, roads, bridges, civil works
- services: Consulting, maintenance, professional services, IT services
- supply: Goods, equipment, materials, supplies procurement
- it_software: Software development, IT infrastructure, digital services
- manufacturing: Industrial equipment, machinery, production
- consulting: Advisory, research, feasibility studies
- healthcare: Medical equipment, hospital services, pharmaceuticals
- education: Educational services, training, e-learning
- transportation: Vehicles, logistics, transport services
- energy: Power, renewable energy, electrical equipment
- telecom: Communication equipment, network services
- agriculture: Farming equipment, agricultural services
- defense: Military equipment, defense services
- other: Miscellaneous or unclear categories

Priority levels:
- critical: High value (>10 crore), urgent deadline, strategic importance
- high: Medium-high value (1-10 crore), important projects
- medium: Standard value (10 lakh-1 crore), routine tenders
- low: Low value (<10 lakh), simple requirements

Classification guidelines:
1. Look for keywords in title and description
2. Consider the procuring entity type (Central/State/PSU)
3. Factor in estimated value for priority
4. Consider typical requirements for each category
5. Provide clear reasoning for classification

Common category indicators:
- Construction: "civil work", "building", "road", "bridge", "infrastructure"
- Services: "consulting", "maintenance", "manpower", "professional services"
- Supply: "procurement", "purchase", "supply", "equipment", "materials"
- IT: "software", "website", "application", "digital", "IT infrastructure"
- Manufacturing: "machinery", "plant", "equipment", "production"
- Healthcare: "medical", "hospital", "pharmaceutical", "health"
- Education: "training", "education", "learning", "academic"

Respond in JSON format only."""


def build_prompt(title: str, description: str, procuring_entity: str, estimated_value: float | None = None) -> str:
    """Build the classification prompt."""
    prompt = f"""Classify this Indian government tender:

Title: {title}

Description: {description}

Procuring Entity: {procuring_entity}"""

    if estimated_value:
        prompt += f"\n\nEstimated Value: ₹{estimated_value:,.2f}"

    prompt += """

Based on the title, description, procuring entity, and value, classify this tender into:
1. Appropriate category
2. Subcategory (if applicable)
3. Priority level
4. Confidence in classification (0.0 to 1.0)
5. Brief reasoning for your classification

Consider the nature of work, typical requirements, and value ranges for Indian government tenders."""

    return prompt
