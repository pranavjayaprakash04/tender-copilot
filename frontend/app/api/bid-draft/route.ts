import { NextRequest, NextResponse } from "next/server";

export const runtime = "edge";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const {
      tender_title,
      tender_category,
      tender_description,
      estimated_value,
      emd_amount,
      tender_location,
      procuring_entity,
      company_name,
      company_industry,
      company_location,
      capabilities,
      bid_type = "technical",
      language = "en",
    } = body;

    if (!tender_title) {
      return NextResponse.json({ error: "tender_title is required" }, { status: 400 });
    }

    const isTamil = language === "ta";

    const systemPrompt = isTamil
      ? `You are a Tamil bid proposal expert. You MUST respond with ONLY a valid JSON object. No markdown code blocks. No text before or after the JSON. The JSON values must be complete Tamil sentences. Never truncate.`
      : `You are an expert bid proposal writer specializing in Indian government tenders for MSMEs. You write professional, compelling, and compliant bid proposals. Return ONLY valid JSON, no markdown, no extra text.`;

    const valueStr = estimated_value
      ? `₹${Number(estimated_value).toLocaleString("en-IN")}`
      : "Not specified";
    const emdStr = emd_amount
      ? `₹${Number(emd_amount).toLocaleString("en-IN")}`
      : "Not specified";

    const userPrompt = isTamil
      ? `Respond with ONLY a JSON object. No markdown. No explanation. Keep each value to 1-2 short sentences maximum.

Tender: ${tender_title}
Company: ${company_name || "Our Company"}, ${company_industry || "IT"}, ${company_location || "Coimbatore"}

JSON format (short Tamil sentences only):
{
"executive_summary": "1-2 sentences in Tamil",
"company_overview": "1-2 sentences in Tamil",
"technical_approach": "1-2 sentences in Tamil",
"implementation_plan": "1-2 sentences in Tamil",
"team_structure": "1-2 sentences in Tamil",
"quality_assurance": "1-2 sentences in Tamil",
"financial_proposal": "1-2 sentences in Tamil",
"compliance_statement": "1-2 sentences in Tamil",
"conclusion": "1-2 sentences in Tamil",
"language": "ta"
}`
      : `Generate a professional ${bid_type} bid proposal for the following tender:

TENDER DETAILS:
- Title: ${tender_title}
- Category: ${tender_category || "Not specified"}
- Description: ${tender_description || "No description provided"}
- Estimated Value: ${valueStr}
- EMD Amount: ${emdStr}
- Location: ${tender_location || "Not specified"}
- Procuring Entity: ${procuring_entity || "Not specified"}

COMPANY DETAILS:
- Name: ${company_name || "Our Company"}
- Industry: ${company_industry || "IT/Software"}
- Location: ${company_location || "India"}
- Capabilities: ${capabilities || "Software development, AI, Cloud"}

Return ONLY this JSON structure:
{
  "executive_summary": "2-3 sentence compelling summary",
  "company_overview": "Brief company introduction highlighting relevant experience",
  "technical_approach": "Detailed technical methodology for this specific tender",
  "implementation_plan": "Phased implementation with realistic timeline",
  "team_structure": "Key team roles and their qualifications",
  "quality_assurance": "QA processes and compliance measures",
  "financial_proposal": "Pricing strategy and cost justification",
  "compliance_statement": "Declaration of compliance with tender requirements",
  "conclusion": "Strong closing statement",
  "language": "en"
}`;

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
          { role: "user", content: userPrompt },
        ],
        temperature: 0.7,
        max_tokens: 4000,
      }),
    });

    if (!response.ok) {
      const err = await response.text();
      return NextResponse.json({ error: `Groq error: ${err}` }, { status: 500 });
    }

    const data = await response.json();
    const text = data.choices?.[0]?.message?.content || "";

    // Parse JSON from response — try multiple strategies
    let parsed: any = null;

    // Strategy 1: direct JSON match
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      try { parsed = JSON.parse(jsonMatch[0]); } catch {}
    }

    // Strategy 2: strip markdown fences
    if (!parsed) {
      const stripped = text.replace(/```json|```/g, "").trim();
      try { parsed = JSON.parse(stripped); } catch {}
    }

    // Strategy 3: build response from plain text sections
    if (!parsed) {
      parsed = {
        executive_summary: text.slice(0, 300) || "AI generated summary",
        company_overview: "Professional company with relevant expertise",
        technical_approach: text.slice(300, 700) || "Comprehensive technical approach",
        implementation_plan: "Phased implementation over agreed timeline",
        team_structure: "Experienced team with domain expertise",
        quality_assurance: "ISO-standard quality processes",
        financial_proposal: "Competitive pricing as per market rates",
        compliance_statement: "Full compliance with tender requirements",
        conclusion: text.slice(-200) || "We are confident in delivering excellence",
        language: language,
      };
    }
    return NextResponse.json({
      ...parsed,
      tender_title,
      bid_type,
      generated_at: new Date().toISOString(),
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message || "Internal error" }, { status: 500 });
  }
}
