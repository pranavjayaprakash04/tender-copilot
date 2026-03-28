import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const body = await req.json();

  const prompt = `You are an Indian government tender expert. Analyze this tender and provide realistic competitor analysis.

Tender: ${body.title}
Category: ${body.category}
Value: ${body.estimated_value ? "Rs " + body.estimated_value : "not specified"}
Location: ${body.location}

Generate 3 realistic Indian company competitors for ${body.category} tenders.
Return ONLY valid JSON:
{"competitors":[{"competitor_name":"string","estimated_bid":number,"win_probability":number,"strengths":["string"],"weaknesses":["string"]}],"our_win_probability":number,"recommended_price":number}`;

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

  const data = await res.json();
  const content = data.choices?.[0]?.message?.content;
  return NextResponse.json(JSON.parse(content));
}
