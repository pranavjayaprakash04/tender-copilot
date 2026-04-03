import { NextRequest, NextResponse } from "next/server";

const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions";
const MODEL = "llama-3.3-70b-versatile";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const { tender, our_bid } = body;

  const systemPrompt = `You are a price intelligence analyst for Indian government tenders.
Provide market pricing insights for the tender.
Always respond with valid JSON only.`;

  const userPrompt = `Tender: ${JSON.stringify(tender)}
Our Bid: ${our_bid ?? "Not specified"}

Return JSON:
{
  "market_avg": number,
  "market_min": number,
  "market_max": number,
  "bands": [{"label": string, "min": number, "max": number, "win_rate": number}],
  "trend": "rising" | "falling" | "stable",
  "insights": [string]
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
