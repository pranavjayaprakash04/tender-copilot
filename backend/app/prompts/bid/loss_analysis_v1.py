from __future__ import annotations

from pydantic import BaseModel


class AnalysisOutput(BaseModel):
    """Output for bid loss analysis."""
    analysis_summary: str
    key_factors: list[str]
    recommendations: list[str]
    competitor_insights: dict | None
    pricing_insights: dict | None
    technical_insights: dict | None
    confidence: float


SYSTEM_PROMPT = """You are an expert bid analyst specializing in government tender analysis for Indian MSMEs.

Your task is to analyze bid losses and provide actionable insights to improve future bid success rates.

Analysis Guidelines:
1. Identify the primary reasons for bid loss
2. Compare our bid with winning bid (if available)
3. Analyze pricing competitiveness
4. Review technical compliance issues
5. Assess competitor strengths and weaknesses
6. Provide specific, actionable recommendations

Key Areas to Analyze:
- Pricing Strategy: Was our bid too high/low? What was the winning bid amount?
- Technical Compliance: Did we meet all requirements? Any gaps?
- Experience & Capabilities: Did we demonstrate sufficient experience?
- Documentation: Were all documents complete and properly formatted?
- Timeline: Did we submit on time? Any delays?
- Competition: Who won? What are their strengths?

Provide insights in a structured format with confidence scoring (0.0 to 1.0).

Focus on practical recommendations that can be implemented in future bids."""


def build_prompt(
    title: str,
    description: str,
    bid_amount: float,
    loss_reason: str | None,
    loss_reason_details: str | None,
    winning_bidder: str | None,
    winning_amount: float | None,
    competitor_count: int | None,
    our_ranking: int | None,
    evaluation_feedback: str | None,
    include_competitor_analysis: bool,
    include_pricing_analysis: bool,
    include_technical_analysis: bool
) -> str:
    """Build the loss analysis prompt."""
    prompt = f"""Analyze this lost bid and provide insights for improvement:

Bid Details:
- Title: {title}
- Description: {description}
- Our Bid Amount: ₹{bid_amount:,.2f}

Loss Information:"""

    if loss_reason:
        prompt += f"\n- Loss Reason: {loss_reason}"

    if loss_reason_details:
        prompt += f"\n- Loss Details: {loss_reason_details}"

    if winning_bidder:
        prompt += f"\n- Winning Bidder: {winning_bidder}"

    if winning_amount:
        prompt += f"\n- Winning Amount: ₹{winning_amount:,.2f}"
        price_diff = winning_amount - bid_amount
        price_diff_pct = (price_diff / bid_amount * 100) if bid_amount > 0 else 0
        prompt += f"\n- Price Difference: ₹{price_diff:,.2f} ({price_diff_pct:+.1f}%)"

    if competitor_count:
        prompt += f"\n- Number of Competitors: {competitor_count}"

    if our_ranking:
        prompt += f"\n- Our Ranking: {our_ranking} out of {competitor_count or 'unknown'}"

    if evaluation_feedback:
        prompt += f"\n- Evaluation Feedback: {evaluation_feedback}"

    prompt += f"""

Analysis Requirements:
- Include competitor analysis: {include_competitor_analysis}
- Include pricing analysis: {include_pricing_analysis}
- Include technical analysis: {include_technical_analysis}

Please provide:
1. Analysis Summary: Brief overview of why we lost
2. Key Factors: Main reasons for the loss (3-5 points)
3. Recommendations: Actionable improvements for future bids (3-5 points)
4. Detailed insights for the requested analysis areas
5. Confidence score in your analysis (0.0 to 1.0)

Focus on practical, implementable recommendations that can improve our win rate in future government tenders."""

    return prompt
