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

    const bidStr = body.our_bid_amount
      ? `Rs ${Number(body.our_bid_amount).toLocaleString("en-IN")}`
      : "not provided";

    const prompt = `You are an expert in Indian government tender bidding for MSMEs. Analyse the win probability for this tender bid.

TENDER DETAILS:
- Title: ${body.tender_title || "Not specified"}
- Category: ${body.tender_category || "Not specified"}
- Estimated Value: ${valueStr}
- Location: ${body.tender_location || "Pan India"}
- Portal: ${(body.portal || "CPPP").toUpperCase()}

COMPANY DETAILS:
- Company: ${body.company_name || "MSME Company"}
- Industry: ${body.company_industry || "Not specified"}
- Our Bid Amount: ${bidStr}

Analyse based on:
1. Bid competitiveness relative to estimated value
2. Category competitiveness in Indian government tenders
3. Typical number of bidders for this category/value range
4. Geographic advantages/disadvantages
5. MSME preferences in Indian government procurement (GeM, MSME Act)

Return ONLY valid JSON:
{
  "win_probability": number between 0 and 1,
  "confidence": "high" | "medium" | "low",
  "factors": ["factor 1", "factor 2", "factor 3", "factor 4"],
  "market_avg": number or null (estimated average bid in INR),
  "recommended_range": {
    "min": number,
    "max": number,
    "optimal": number
  } or null
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
