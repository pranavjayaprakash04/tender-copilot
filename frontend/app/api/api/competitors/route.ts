import { NextRequest, NextResponse } from "next/server";

const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions";
const MODEL = "llama-3.3-70b-versatile";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const { tender_title, category, value, state } = body;

  const systemPrompt = `You are a government tender market intelligence expert for Indian MSMEs.
Analyze the tender and return a JSON object with competitor insights.
Always respond with valid JSON only.`;

  const userPrompt = `Tender: "${tender_title}"
Category: ${category ?? "General"}
Value: ${value ?? "Not specified"}
State: ${state ?? "India"}

Return JSON:
{
  "competitors": [{"name": string, "win_rate": number, "avg_bid": string, "strength": string}],
  "market_insights": string,
  "win_strategies": [string],
  "total_expected_bidders": number
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
