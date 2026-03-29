import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    const valueStr = body.estimated_value
      ? `Rs ${Number(body.estimated_value).toLocaleString("en-IN")}`
      : "value not specified";

    const prompt = `You are an Indian government tender expert. Analyze this tender and provide realistic competitor analysis.

Tender: ${body.title}
Category: ${body.category}
Value: ${valueStr}
Location: ${body.location}
Portal: ${(body.portal || "CPPP").toUpperCase()}

Generate 3 realistic Indian companies that typically bid on ${body.category} tenders in ${body.location}.
Use real Indian company names relevant to ${body.category}:
- For Works: L&T Construction, NCC Limited, Shapoorji Pallonji, KEC International, Tata Projects, HCC, AFCONS
- For IT/Software: TCS, Wipro, Infosys, HCL, Tech Mahindra, NIIT Technologies
- For Goods: relevant Indian suppliers and distributors
- For Services: relevant Indian service companies

Return ONLY valid JSON with no extra text:
{
  "competitors": [
    {
      "competitor_name": "string",
      "estimated_bid": number or null,
      "win_probability": number between 0 and 1,
      "strengths": ["string", "string"],
      "weaknesses": ["string", "string"]
    }
  ],
  "our_win_probability": number between 0 and 1,
  "recommended_price": number or null
}`;

    const res = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${process.env.GROQ_API_KEY}`,
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

    return NextResponse.json(JSON.parse(content));
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
