import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    const prompt = `You are an Indian government tender eligibility expert. Check if a company is eligible to bid on this tender.

TENDER DETAILS:
- Title: ${body.tender_title}
- Category: ${body.tender_category}
- Estimated Value: ${body.estimated_value ? "Rs " + Number(body.estimated_value).toLocaleString("en-IN") : "Not specified"}
- Location: ${body.tender_location}
- Portal: ${(body.portal || "CPPP").toUpperCase()}
- Requirements: ${body.requirements || "Standard government tender requirements apply"}

COMPANY PROFILE:
- Name: ${body.company_name}
- Industry: ${body.company_industry}
- Location: ${body.company_location}
- GSTIN: ${body.gstin || "Not provided"}
- Udyam Number: ${body.udyam_number || "Not provided"}
- Turnover Range: ${body.turnover_range || "Not specified"}
- Capabilities: ${body.capabilities || "Not specified"}

Analyze eligibility based on:
1. Industry/category match
2. Geographic eligibility
3. Financial capacity (turnover vs tender value)
4. Registration requirements (GST, Udyam/MSME)
5. Technical capability match

Return ONLY valid JSON:
{
  "eligible": true or false,
  "score": number between 0 and 100,
  "verdict": "Highly Eligible" | "Likely Eligible" | "Marginally Eligible" | "Not Eligible",
  "criteria": [
    {
      "name": "string",
      "status": "pass" | "fail" | "warning",
      "detail": "string explaining why"
    }
  ],
  "missing_documents": ["string"],
  "recommendations": ["string"],
  "summary": "2-3 sentence overall assessment"
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

    return NextResponse.json(JSON.parse(content));
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
