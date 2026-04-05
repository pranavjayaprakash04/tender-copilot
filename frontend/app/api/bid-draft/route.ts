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
      ? `நீங்கள் இந்திய அரசாங்க ஒப்பந்தங்களில் நிபுணத்துவம் பெற்ற ஒரு தொழில்முறை ஒப்பந்த ஆலோசகர். MSME நிறுவனங்களுக்கு தொழில்முறை ஒப்பந்த முன்மொழிவுகளை தமிழில் எழுதுவதில் நீங்கள் திறமையானவர். JSON மட்டுமே வழங்கவும், வேறு எதுவும் வேண்டாம்.`
      : `You are an expert bid proposal writer specializing in Indian government tenders for MSMEs. You write professional, compelling, and compliant bid proposals. Return ONLY valid JSON, no markdown, no extra text.`;

    const valueStr = estimated_value
      ? `₹${Number(estimated_value).toLocaleString("en-IN")}`
      : "Not specified";
    const emdStr = emd_amount
      ? `₹${Number(emd_amount).toLocaleString("en-IN")}`
      : "Not specified";

    const userPrompt = isTamil
      ? `பின்வரும் ஒப்பந்தத்திற்கு தமிழில் ஒரு தொழில்முறை ஒப்பந்த முன்மொழிவை உருவாக்கவும்:

ஒப்பந்த தகவல்கள்:
- தலைப்பு: ${tender_title}
- வகை: ${tender_category || "குறிப்பிடப்படவில்லை"}
- விளக்கம்: ${tender_description || "விளக்கம் இல்லை"}
- மதிப்பீடு: ${valueStr}
- EMD தொகை: ${emdStr}
- இடம்: ${tender_location || "குறிப்பிடப்படவில்லை"}
- நிறுவனம்: ${procuring_entity || "குறிப்பிடப்படவில்லை"}

நிறுவன தகவல்கள்:
- பெயர்: ${company_name || "நிறுவனம்"}
- தொழில்: ${company_industry || "IT/மென்பொருள்"}
- இடம்: ${company_location || "தமிழ்நாடு"}
- திறன்கள்: ${capabilities || "மென்பொருள் மேம்பாடு, AI, Cloud"}

பின்வரும் JSON வடிவத்தில் மட்டும் பதிலளிக்கவும்:
{
  "executive_summary": "சுருக்கம் (2-3 வாக்கியங்கள்)",
  "company_overview": "நிறுவன அறிமுகம்",
  "technical_approach": "தொழில்நுட்ப அணுகுமுறை",
  "implementation_plan": "செயல்படுத்தல் திட்டம்",
  "team_structure": "குழு அமைப்பு",
  "quality_assurance": "தர உத்தரவாதம்",
  "financial_proposal": "நிதி முன்மொழிவு",
  "compliance_statement": "இணக்கத்தன்மை அறிக்கை",
  "conclusion": "முடிவுரை",
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
        max_tokens: 2000,
      }),
    });

    if (!response.ok) {
      const err = await response.text();
      return NextResponse.json({ error: `Groq error: ${err}` }, { status: 500 });
    }

    const data = await response.json();
    const text = data.choices?.[0]?.message?.content || "";

    // Parse JSON from response
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      return NextResponse.json({ error: "Invalid AI response format" }, { status: 500 });
    }

    const parsed = JSON.parse(jsonMatch[0]);
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
