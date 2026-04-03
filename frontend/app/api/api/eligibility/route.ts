import { NextRequest, NextResponse } from "next/server";

const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions";
const MODEL = "llama-3.3-70b-versatile";

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const { tender, company } = body;

  const systemPrompt = `You are a government tender eligibility expert for Indian MSMEs.
Assess whether the company meets tender requirements.
Always respond with valid JSON only.`;

  const userPrompt = `Tender: ${JSON.stringify(tender)}
Company Profile: ${JSON.stringify(company)}

Return JSON:
{
  "eligible": boolean,
  "score": number (0-100),
  "reasons": [string],
  "missing_requirements": [string],
  "recommendations": [string]
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
      temperature: 0.2,
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
