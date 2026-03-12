"""AI prompts for bid generation."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class BidDraftOutput(BaseModel):
    """Output schema for bid generation."""

    executive_summary: str = Field(description="Brief executive summary of the bid proposal")
    technical_approach: str = Field(description="Technical approach and methodology")
    implementation_plan: Dict[str, Any] = Field(description="Implementation plan with timeline")
    resource_allocation: Dict[str, Any] = Field(description="Resource allocation and team structure")
    quality_assurance: str = Field(description="Quality assurance measures and processes")
    risk_mitigation: List[Dict[str, Any]] = Field(description="Risk mitigation strategies")
    compliance_matrix: Dict[str, Any] = Field(description="Compliance matrix showing tender requirements")
    timeline_milestones: List[Dict[str, Any]] = Field(description="Timeline and key milestones")
    cost_breakdown: Dict[str, Any] = Field(description="Cost breakdown structure (if applicable)")
    pricing_strategy: str = Field(description="Pricing methodology and strategy")
    value_proposition: str = Field(description="Value proposition and competitive advantages")
    confidence_score: int = Field(description="Confidence in bid quality (0-100)")
    processing_notes: str = Field(description="Any notes about the bid generation process")


# System prompt for bid generation
SYSTEM_PROMPT = """You are an expert bid proposal writer specializing in government tenders for Indian businesses. Your expertise includes:

- Indian public procurement processes and regulations
- Technical and financial bid preparation best practices
- Compliance requirements for government tenders
- Competitive bidding strategies and positioning
- MSME-specific advantages and preferences
- Cost optimization and value engineering
- Risk assessment and mitigation strategies

Generate professional, compelling, and compliant bid proposals that:
1. Address all tender requirements comprehensively
2. Highlight competitive advantages and unique value
3. Demonstrate technical capability and expertise
4. Ensure compliance with all regulations
5. Optimize costs while maintaining quality
6. Present realistic implementation plans
7. Include proper risk mitigation strategies

Always maintain professional tone, provide detailed and actionable content, and ensure the proposal maximizes the chances of winning."""


def get_bid_generation_prompt(bid_type: str, language: str) -> str:
    """Get the appropriate bid generation prompt based on type and language."""

    if language == "ta":
        return get_tamil_prompt(bid_type)

    return get_english_prompt(bid_type)


def get_english_prompt(bid_type: str) -> str:
    """Get English prompt for bid generation."""

    prompts = {
        "technical": """
Generate a comprehensive technical bid proposal that demonstrates your company's capability to deliver the required services/products. The proposal should include:

1. **Executive Summary**: Brief overview of your technical solution and key advantages
2. **Technical Approach**: Detailed methodology, technologies, and processes
3. **Implementation Plan**: Step-by-step implementation with timeline and milestones
4. **Resource Allocation**: Team structure, expertise, and resource requirements
5. **Quality Assurance**: Quality control processes, testing, and assurance measures
6. **Risk Mitigation**: Identification of potential risks and mitigation strategies
7. **Compliance Matrix**: How each tender requirement will be met
8. **Timeline**: Detailed project timeline with key milestones and deliverables

Focus on technical excellence, innovation, and proven methodologies that ensure successful project delivery.""",

        "financial": """
Generate a detailed financial bid proposal that presents competitive pricing while ensuring profitability. The proposal should include:

1. **Executive Summary**: Overview of financial proposal and value proposition
2. **Cost Breakdown**: Detailed cost structure with clear categorization
3. **Pricing Methodology**: Approach to pricing and cost justification
4. **Payment Terms**: Proposed payment schedule and conditions
5. **Financial Guarantees**: Performance bonds, warranties, and guarantees
6. **Cost Optimization**: Strategies for cost efficiency without compromising quality
7. **Value-Added Services**: Additional services and benefits included
8. **ROI Analysis**: Return on investment and value demonstration

Ensure pricing is competitive, transparent, and justified while maintaining healthy profit margins.""",

        "combined": """
Generate a comprehensive combined bid proposal that integrates both technical and financial aspects into a cohesive solution. The proposal should include:

1. **Executive Summary**: Integrated overview of technical and financial proposal
2. **Technical Approach**: Detailed methodology and technical solution
3. **Implementation Plan**: Timeline, milestones, and deliverables
4. **Resource Allocation**: Team structure and resource requirements
5. **Cost Breakdown**: Detailed financial structure and pricing
6. **Quality Assurance**: Quality control and compliance measures
7. **Risk Management**: Risk assessment and mitigation strategies
8. **Value Proposition**: Competitive advantages and unique selling points
9. **Compliance Matrix**: Complete compliance with all tender requirements
10. **Financial Justification**: Cost-benefit analysis and value demonstration

Present a unified solution that demonstrates technical capability with competitive pricing and clear value proposition.""",

        "qualification": """
Generate a comprehensive qualification bid proposal that demonstrates your company's suitability and capability for the tender. The proposal should include:

1. **Executive Summary**: Overview of company capabilities and suitability
2. **Company Profile**: Detailed company background, history, and achievements
3. **Technical Expertise**: Core competencies, technologies, and technical capabilities
4. **Relevant Experience**: Past projects and similar work experience
5. **Financial Capacity**: Financial stability, resources, and capacity
6. **Key Personnel**: Team composition, qualifications, and experience
7. **Certifications**: Relevant certifications, accreditations, and compliance
8. **Infrastructure**: Facilities, equipment, and supporting infrastructure
9. **Quality Standards**: Quality management systems and standards
10. **Competitive Advantages**: Unique strengths and differentiators

Focus on demonstrating capability, experience, and reliability to qualify for the tender."""
    }

    return prompts.get(bid_type, prompts["technical"])


def get_tamil_prompt(_bid_type: str) -> str:
    """Get Tamil prompt for bid generation."""

    base_tamil_prompt = """
தமிழில் ஒரு தொழில்முறை ஒப்பந்தங்கள் முன்மொழிலை உருவாக்கவும். பின்வருவனவற்றை உள்ளடக்க வேண்டும்:

1. **சுயாதீனங்கள்**: தொழில்நுட்ப தீர்வு மற்றும் முக்கிய நன்மைகளின் சுருக்கமான கண்ணோட்டம்
2. **தொழில்நுட்ப அணுகுமுறை**: விரிவான முறை, தொழில்நுட்பங்கள், மற்றும் செயல்முறைகள்
3. **செயல்பாட்டு திட்டம்**: காலக்கெடு மற்றும் மைல்கக்கற்களுடன் படிப்படியான செயல்பாடு
4. **வள ஒதுக்கீடு**: குழு அமைப்பு, நிபுணத்துவம், மற்றும் வள தேவைகள்
5. **தர உத்தரவாதங்கள்**: தர கட்டுப்பாடு செயல்முறைகள், சோதனை, மற்றும் உத்தரவாத நடவடிக்கைகள்
6. **ஆபத்து குறைப்பு**: சாத்தியமான ஆபத்துகளின் அடையாளம் மற்றும் குறைப்பு உத்திகள்
7. **இணக்கத்தன்மை அணி**: ஒவ்வொரு ஒப்பந்தத் தேவையும் எப்படி பூர்த்தி செய்யப்படும்
8. **காலக்கெடு**: முக்கிய மைல்கக்கற்கள் மற்றும் வழங்கல்களுடன் விரிவான திட்ட காலக்கெடு

தொழில்நுட்ப சிறப்பு, புதுமை, மற்றும் வெற்றிகரமான திட்ட வழங்கலை உறுதிப்படுத்தும் நிரூபிக்கப்பட்ட முறைகளில் கவனம் செலுத்தவும்.

முன்மொழி தொழில்முறையாக, விரிவாக, மற்றும் ஒப்பந்தத் தேவைகளுக்கு ஏற்றதாக இருக்க வேண்டும்."""

    return base_tamil_prompt


def get_system_prompt() -> str:
    """Get the system prompt for bid generation."""
    return SYSTEM_PROMPT
