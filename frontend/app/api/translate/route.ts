import { NextRequest, NextResponse } from "next/server";

export const runtime = "edge";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { text, target_language = "ta" } = body;

    if (!text) {
      return NextResponse.json({ error: "text is required" }, { status: 400 });
    }

    const systemPrompt = target_language === "ta"
      ? `You are a Tamil translator specializing in government and business terminology. Translate the given text to Tamil naturally and professionally. Return ONLY the translated text, nothing else.`
      : `You are an English translator. Translate the given Tamil text to English naturally. Return ONLY the translated text, nothing else.`;

    const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${process.env.GROQ_API_KEY}`,
      },
      body: JSON.stringify({
        model: "llama-3.3-70b-versatile",
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: `Translate this to ${target_language === "ta" ? "Tamil" : "English"}:\n\n${text}` },
        ],
        temperature: 0.3,
        max_tokens: 1000,
      }),
    });

    if (!response.ok) {
      return NextResponse.json({ error: "Translation failed" }, { status: 500 });
    }

    const data = await response.json();
    const translated = data.choices?.[0]?.message?.content || text;

    return NextResponse.json({ translated, source: text, language: target_language });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
