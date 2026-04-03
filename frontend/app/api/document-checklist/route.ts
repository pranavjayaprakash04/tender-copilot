import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    if (!body.tender_id && !body.tender_title) {
      return NextResponse.json(
        { error: "tender_id or tender_title is required" },
        { status: 400 }
      );
    }

    const valueStr = body.estimated_value
      ? `Rs ${Number(body.estimated_value).toLocaleString("en-IN")}`
      : "not specified";

    const prompt = `You are an Indian government tender documentation expert. Generate a compliance document checklist for this tender.

TENDER DETAILS:
- Title: ${body.tender_title || "Government Tender"}
- Category: ${body.tender_category || "Works/Goods/Services"}
- Estimated Value: ${valueStr}
- Location: ${body.tender_location || "Pan India"}
- Description: ${body.description || "Standard government procurement"}

Generate a realistic document checklist based on common Indian government tender requirements.
Consider GFR 2017 rules, CVC guidelines, and GeM/CPPP requirements.

Include documents like:
- GST Registration Certificate
- PAN Card
- Udyam/MSME Registration (if applicable)
- Company Registration Certificate
- Income Tax Returns (last 3 years)
- Audited Balance Sheet
- Work Experience Certificates
- Bank Solvency Certificate
- EMD/Bid Security
- Technical specifications compliance
- Quality certifications (ISO, BIS if relevant)

Return ONLY valid JSON:
{
  "tender_id": "${body.tender_id || "unknown"}",
  "checklist": [
    {
      "id": "string (unique id)",
      "name": "string (document name)",
      "type": "mandatory" | "optional",
      "status": "missing",
      "in_vault": false,
      "notes": "string or null (what to include)"
    }
  ],
  "total": number,
  "have_count": 0,
  "missing_count": number,
  "readiness_score": 0,
  "summary": "2-3 sentence summary of key documentation requirements"
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
        temperature: 0.2,
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
      const parsed = JSON.parse(content);
      // Ensure total and missing_count are consistent
      if (parsed.checklist && Array.isArray(parsed.checklist)) {
        parsed.total = parsed.checklist.length;
        parsed.missing_count = parsed.checklist.filter((i: any) => i.status === "missing").length;
        parsed.have_count = parsed.total - parsed.missing_count;
        parsed.readiness_score = Math.round((parsed.have_count / parsed.total) * 100) || 0;
      }
      return NextResponse.json(parsed);
    } catch {
      return NextResponse.json({ error: "Failed to parse Groq response" }, { status: 502 });
    }
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Internal server error" }, { status: 500 });
  }
}
