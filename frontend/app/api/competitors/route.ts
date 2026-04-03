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
      : "value not specified";

    const prompt = `You are an Indian government tender expert. Analyse this tender and provide realistic competitor analysis for MSMEs bidding in India.

Tender: ${body.tender_title || "Government Tender"}
Category: ${body.tender_category || "Works/Goods/Services"}
Value: ${valueStr}
Location: ${body.tender_location || "Pan India"}
Portal: ${(body.portal || "CPPP").toUpperCase()}

Generate 3-4 realistic Indian companies that typically bid on ${body.tender_category || "government"} tenders in ${body.tender_location || "India"}.
Use real Indian company names relevant to the category:
- For Works/Construction: L&T Construction, NCC Limited, Shapoorji Pallonji, KEC International, Tata Projects, HCC, AFCONS Infrastructure
- For IT/Software/Digital: TCS, Wipro, Infosys, HCL Technologies, Tech Mahindra, NIIT Technologies, Mastech
- For Goods/Supply: relevant Indian manufacturers, distributors, and MSME suppliers
- For Services/Consulting: relevant Indian service companies and consulting firms
- For Healthcare: Fortis, Apollo, Max Healthcare, Narayana Health

Also provide market insights, win strategies for MSMEs, and expected bidder count.

Return ONLY valid JSON with no extra text:
{
  "competitors": [
    {
      "name": "string (company name)",
      "estimated_bid": number or null (in INR),
      "win_probability": number between 0 and 1,
      "strengths": ["string", "string"],
      "weaknesses": ["string", "string"]
    }
  ],
  "market_insights": "string (2-3 sentences about market dynamics for this category)",
  "win_strategies": ["strategy 1 for MSMEs", "strategy 2", "strategy 3"],
  "total_expected_bidders": number
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
        temperature: 0.7,
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
