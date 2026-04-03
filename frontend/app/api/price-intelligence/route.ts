import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    if (!body.tender_title && !body.tender_category) {
      return NextResponse.json(
        { error: "tender_title or tender_category is required" },
        { status: 400 }
      );
    }

    const valueStr = body.estimated_value
      ? `Rs ${Number(body.estimated_value).toLocaleString("en-IN")}`
      : "not specified";

    const ourBidStr = body.our_bid_amount
      ? `Rs ${Number(body.our_bid_amount).toLocaleString("en-IN")}`
      : "not provided";

    const prompt = `You are an Indian government tender pricing expert specialising in MSME procurement strategy. Analyse pricing for this tender.

TENDER DETAILS:
- Title: ${body.tender_title || "Government Tender"}
- Category: ${body.tender_category || "Works/Goods/Services"}
- Estimated Value: ${valueStr}
- Our Bid Amount: ${ourBidStr}

Provide realistic market pricing data based on:
1. Historical L1 (lowest qualifying bidder) prices in Indian government tenders
2. Category-specific pricing patterns (Works vs Goods vs Services)
3. MSME pricing competitiveness
4. Market competition levels

Return ONLY valid JSON:
{
  "tender_id": "${body.tender_id || "unknown"}",
  "category": "${body.tender_category || "General"}",
  "market_avg": number (estimated average bid in INR),
  "market_min": number (estimated L1/lowest bid in INR),
  "market_max": number (estimated highest bid in INR),
  "price_to_win_score": number between 0 and 100 (higher = better chance of winning at current price),
  "price_to_win_label": "Highly Competitive" | "Competitive" | "Moderate" | "Expensive" | "Too High",
  "optimal_price": number (recommended bid in INR),
  "our_bid_amount": ${body.our_bid_amount || null},
  "our_position_pct": ${body.our_bid_amount ? "number between 0 and 100 (percentile position vs competitors, 0=lowest)" : null},
  "bands": [
    { "label": "L1 Zone (Win Zone)", "min": number, "max": number, "color": "#10B981" },
    { "label": "Competitive Zone", "min": number, "max": number, "color": "#3B82F6" },
    { "label": "Average Zone", "min": number, "max": number, "color": "#F59E0B" },
    { "label": "Expensive Zone", "min": number, "max": number, "color": "#EF4444" }
  ],
  "trend": [
    { "label": "Q1 FY23", "avg": number, "min": number, "max": number },
    { "label": "Q2 FY23", "avg": number, "min": number, "max": number },
    { "label": "Q3 FY23", "avg": number, "min": number, "max": number },
    { "label": "Q4 FY23", "avg": number, "min": number, "max": number },
    { "label": "Q1 FY24", "avg": number, "min": number, "max": number }
  ],
  "insights": ["insight 1", "insight 2", "insight 3"]
}`;

    const apiKey = process.env.GROQ_API_KEY;
    if (!apiKey) {
      return NextResponse.json({ error: "Groq API key not configured" }, { status: 500 });
    }

    const res = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "llama-3.3-70b-versatile",
        messages: [{ role: "user", content: prompt }],
        temperature: 0.3,
        response_format: { type: "json_object" },
      }),
    });

    if (!res.ok) {
      const err = await res.text();
      return NextResponse.json({ error: "Groq API error", detail: err }, { status: 502 });
    }

    const data = await res.json();
    const content = data.choices?.[0]?.message?.content;
    if (!content) {
      return NextResponse.json({ error: "Empty response from Groq" }, { status: 502 });
    }

    try {
      return NextResponse.json(JSON.parse(content));
    } catch {
      return NextResponse.json({ error: "Failed to parse Groq response" }, { status: 502 });
    }
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Internal server error" }, { status: 500 });
  }
}
