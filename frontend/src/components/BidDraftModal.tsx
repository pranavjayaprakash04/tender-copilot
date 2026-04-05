"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

interface BidDraftModalProps {
  tender: {
    id: string;
    title: string;
    category?: string | null;
    description?: string | null;
    estimated_value?: number | null;
    emd_amount?: number | null;
    state?: string | null;
    procuring_entity?: string;
  };
  profile: any;
  onClose: () => void;
}

interface BidDraft {
  executive_summary: string;
  company_overview: string;
  technical_approach: string;
  implementation_plan: string;
  team_structure: string;
  quality_assurance: string;
  financial_proposal: string;
  compliance_statement: string;
  conclusion: string;
  language: string;
  tender_title: string;
  bid_type: string;
  generated_at: string;
}

const SECTIONS = [
  { key: "executive_summary",    label: "Executive Summary",      ta: "சுருக்கம்" },
  { key: "company_overview",     label: "Company Overview",       ta: "நிறுவன அறிமுகம்" },
  { key: "technical_approach",   label: "Technical Approach",     ta: "தொழில்நுட்ப அணுகுமுறை" },
  { key: "implementation_plan",  label: "Implementation Plan",    ta: "செயல்படுத்தல் திட்டம்" },
  { key: "team_structure",       label: "Team Structure",         ta: "குழு அமைப்பு" },
  { key: "quality_assurance",    label: "Quality Assurance",      ta: "தர உத்தரவாதம்" },
  { key: "financial_proposal",   label: "Financial Proposal",     ta: "நிதி முன்மொழிவு" },
  { key: "compliance_statement", label: "Compliance Statement",   ta: "இணக்கத்தன்மை" },
  { key: "conclusion",           label: "Conclusion",             ta: "முடிவுரை" },
];

export default function BidDraftModal({ tender, profile, onClose }: BidDraftModalProps) {
  const [bidType, setBidType] = useState<"technical" | "financial" | "combined">("technical");
  const [language, setLanguage] = useState<"en" | "ta">("en");
  const [activeSection, setActiveSection] = useState(0);
  const isTamil = language === "ta";

  const mutation = useMutation<BidDraft, Error>({
    mutationFn: async () => {
      const res = await fetch("/api/bid-draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tender_title: tender.title,
          tender_category: tender.category,
          tender_description: tender.description,
          estimated_value: tender.estimated_value,
          emd_amount: tender.emd_amount,
          tender_location: tender.state,
          procuring_entity: tender.procuring_entity,
          company_name: profile?.name,
          company_industry: profile?.industry,
          company_location: profile?.location,
          capabilities: profile?.capabilities_text,
          bid_type: bidType,
          language,
        }),
      });
      if (!res.ok) throw new Error("Bid draft generation failed");
      return res.json();
    },
  });

  const data = mutation.data;

  const copyToClipboard = () => {
    if (!data) return;
    const text = SECTIONS.map(s => {
      const label = isTamil ? s.ta : s.label;
      return `${label}\n${"=".repeat(label.length)}\n${(data as any)[s.key]}\n`;
    }).join("\n");
    navigator.clipboard.writeText(text);
  };

  const downloadDraft = () => {
    if (!data) return;
    const text = [
      `BID PROPOSAL`,
      `Tender: ${data.tender_title}`,
      `Generated: ${new Date(data.generated_at).toLocaleDateString("en-IN")}`,
      `Language: ${isTamil ? "Tamil" : "English"}`,
      "",
      ...SECTIONS.map(s => {
        const label = isTamil ? s.ta : s.label;
        return `${label}\n${"=".repeat(40)}\n${(data as any)[s.key]}\n`;
      }),
    ].join("\n");

    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `bid-draft-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-3xl max-h-[90vh] overflow-hidden rounded-2xl shadow-2xl flex flex-col"
        style={{ background: "#0A0E1A", border: "1px solid #1E2537" }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#1E2537]">
          <div>
            <h2 className="text-white font-bold text-lg">📝 {isTamil ? "ஒப்பந்த வரைவு உருவாக்கி" : "AI Bid Drafter"}</h2>
            <p className="text-gray-500 text-xs mt-0.5 line-clamp-1">{tender.title}</p>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 text-xl">✕</button>
        </div>

        {/* Controls */}
        {!data && (
          <div className="px-6 py-5 border-b border-[#1E2537]">
            <div className="flex gap-4 flex-wrap">
              <div>
                <label className="text-xs text-gray-500 block mb-2">{isTamil ? "ஒப்பந்த வகை" : "Bid Type"}</label>
                <div className="flex gap-2">
                  {["technical", "financial", "combined"].map(t => (
                    <button key={t} onClick={() => setBidType(t as any)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${bidType === t ? "bg-blue-600 border-blue-600 text-white" : "border-[#1E2537] text-gray-400 hover:border-gray-500"}`}>
                      {t.charAt(0).toUpperCase() + t.slice(1)}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-500 block mb-2">Language / மொழி</label>
                <div className="flex gap-2">
                  <button onClick={() => setLanguage("en")}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${language === "en" ? "bg-indigo-600 border-indigo-600 text-white" : "border-[#1E2537] text-gray-400 hover:border-gray-500"}`}>
                    English
                  </button>
                  <button onClick={() => setLanguage("ta")}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${language === "ta" ? "bg-indigo-600 border-indigo-600 text-white" : "border-[#1E2537] text-gray-400 hover:border-gray-500"}`}>
                    தமிழ்
                  </button>
                </div>
              </div>
            </div>

            <button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
              className="mt-5 w-full py-3 rounded-xl font-semibold text-sm transition-all"
              style={{ background: mutation.isPending ? "#1E2537" : "linear-gradient(135deg, #3B82F6, #6366F1)", color: "#fff" }}
            >
              {mutation.isPending
                ? (isTamil ? "⏳ உருவாக்கப்படுகிறது..." : "⏳ Generating bid draft...")
                : (isTamil ? "🚀 ஒப்பந்த வரைவு உருவாக்கு" : "🚀 Generate Bid Draft")}
            </button>

            {mutation.isError && (
              <div className="mt-3 p-3 rounded-lg text-red-400 text-sm" style={{ background: "#EF444420", border: "1px solid #EF444440" }}>
                {isTamil ? "தோல்வி. மீண்டும் முயற்சிக்கவும்." : "Generation failed. Please try again."}
              </div>
            )}

            {!data && !mutation.isPending && (
              <p className="text-center text-gray-600 text-xs mt-4">
                {isTamil
                  ? "AI உங்கள் நிறுவன சுயவிவரத்தை பயன்படுத்தி ஒரு தொழில்முறை ஒப்பந்த முன்மொழிவை உருவாக்கும்"
                  : "AI will use your company profile to generate a professional bid proposal tailored to this tender"}
              </p>
            )}
          </div>
        )}

        {/* Generated Content */}
        {data && (
          <>
            {/* Action bar */}
            <div className="px-6 py-3 border-b border-[#1E2537] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500" />
                <span className="text-green-400 text-xs font-medium">
                  {isTamil ? "வரைவு தயார்!" : "Draft ready!"}
                </span>
              </div>
              <div className="flex gap-2">
                <button onClick={copyToClipboard}
                  className="px-3 py-1.5 rounded-lg text-xs border border-[#1E2537] text-gray-400 hover:text-white hover:border-gray-500 transition-colors">
                  📋 {isTamil ? "நகலெடு" : "Copy"}
                </button>
                <button onClick={downloadDraft}
                  className="px-3 py-1.5 rounded-lg text-xs border border-[#1E2537] text-gray-400 hover:text-white hover:border-gray-500 transition-colors">
                  ⬇ {isTamil ? "பதிவிறக்கு" : "Download"}
                </button>
                <button onClick={() => mutation.reset()}
                  className="px-3 py-1.5 rounded-lg text-xs bg-blue-600 text-white hover:bg-blue-700 transition-colors">
                  🔄 {isTamil ? "மீண்டும்" : "Regenerate"}
                </button>
              </div>
            </div>

            {/* Section tabs */}
            <div className="flex gap-1 px-6 py-3 border-b border-[#1E2537] overflow-x-auto">
              {SECTIONS.map((s, i) => (
                <button key={s.key} onClick={() => setActiveSection(i)}
                  className={`px-2 py-1 rounded text-xs font-medium whitespace-nowrap transition-colors flex-shrink-0 ${activeSection === i ? "bg-[#1E2537] text-white" : "text-gray-500 hover:text-gray-300"}`}>
                  {isTamil ? s.ta : s.label}
                </button>
              ))}
            </div>

            {/* Section content */}
            <div className="flex-1 overflow-y-auto px-6 py-5">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">
                {isTamil ? SECTIONS[activeSection].ta : SECTIONS[activeSection].label}
              </h3>
              <p className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
                {(data as any)[SECTIONS[activeSection].key]}
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
