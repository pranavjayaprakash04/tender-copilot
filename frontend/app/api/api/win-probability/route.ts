import { NextRequest, NextResponse } from "next/server";

const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions";
const MODEL = "llama-3.3-70b-versatile";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const { tender, bid_amount, company } = body;

  const systemPrompt = `You are a win probability analyst for Indian government tenders.
Predict bid win probability based on market data.
Always respond with valid JSON only.`;

  const userPrompt = `Tender: ${JSON.stringify(tender)}
Our Bid Amount: ${bid_amount ?? "Not specified"}
Company: ${JSON.stringify(company ?? {})}

Return JSON:
{
  "win_probability": number (0-100),
  "confidence": "low" | "medium" | "high",
  "factors": [{"factor": string, "impact": "positive" | "negative", "weight": number}],
  "market_avg": number,
  "recommended_range": {"min": number, "max": number}
}`;

  const groqRes = await fetch(GROQ_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${process.env.GROQ_API_KEY}`,
    },
    body: JSON.stringify({
      model: MODEL,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
      response_format: { type: "json_object" },
      temperature: 0.3,
    }),
  });

  if (!groqRes.ok) {
    return NextResponse.json(
      { error: "AI service unavailable" },
      { status: 502 }
    );
  }

  const data = await groqRes.json();
  const content = data.choices?.[0]?.message?.content ?? "{}";

  return NextResponse.json(JSON.parse(content));
}
