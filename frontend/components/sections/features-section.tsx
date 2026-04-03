import { CardSpotlight } from "@/components/ui/card-spotlight";
import { Orbs } from "@/components/ui/orbs";
import { Eyebrow } from "@/components/ui/eyebrow";
import { Tilt } from "@/components/ui/tilt";
import { Typewriter } from "@/components/ui/typewriter-text";
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "@/components/ui/tooltip";
export function FeaturesSection() {
  const features = [
    { icon: "🔍", title: "Tender Discovery", desc: "Auto-match tenders from GeM, CPPP, state portals based on your business profile.", tip: "Matches by NIC code, turnover, certifications" },
    { icon: "📄", title: "NIT / PDF Analysis", desc: "Upload any tender document. Get clause-level risk scores and red flag detection instantly.", tip: "Supports PDF, DOCX, scanned images via OCR" },
    { icon: "✍️", title: "AI Bid Writer", desc: "Generate complete bid documents in English or Tamil in under 2 minutes.", tip: "Powered by Llama 3.3 70B via Groq" },
    { icon: "⚠️", title: "Risk Detector", desc: "Penalty clauses, unrealistic timelines, non-standard EMD — all flagged before you bid.", tip: "Clause-level confidence scores included" },
    { icon: "🧠", title: "Company Memory", desc: "Save your profile once. Tender Copilot remembers your certifications, GST, and past wins.", tip: "Encrypted vault — your data stays private" },
    { icon: "💬", title: "Tender Chatbot", desc: "Ask anything about a tender in plain Tamil or English. Get instant answers.", tip: "Context-aware — knows full NIT you uploaded" },
  ];
  return (
    <section id="features" style={{ background: "#000", padding: "120px 24px", position: "relative", overflow: "hidden" }}>
      <Orbs count={3} />
      <div style={{ maxWidth: 1200, margin: "0 auto", position: "relative", zIndex: 1 }}>
        <Eyebrow>FEATURES</Eyebrow>
        <h2 style={{ fontSize: "clamp(36px, 5vw, 56px)", fontWeight: 800, color: "#fff", letterSpacing: "-0.03em", marginBottom: 64, textAlign: "center" }}>
          <Typewriter text={["win tenders.", "save time.", "reduce risk.", "scale faster."]} speed={100} delay={2000} loop={true} />
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: 32 }}>
          <TooltipProvider>
            {features.map((feature, i) => (
              <CardSpotlight key={feature.title} dark={true}>
                <div style={{ padding: 32 }}>
                  <div style={{ marginBottom: 20 }}>
                    <Tooltip>
                      <TooltipTrigger>
                        <div style={{ fontSize: 32, cursor: "default" }}>{feature.icon}</div>
                      </TooltipTrigger>
                      <TooltipContent>{feature.tip}</TooltipContent>
                    </Tooltip>
                  </div>
                  <h3 style={{ fontSize: 20, fontWeight: 700, color: "#fff", marginBottom: 12 }}>{feature.title}</h3>
                  <p style={{ fontSize: 15, color: "#86868b", lineHeight: 1.6, margin: 0 }}>{feature.desc}</p>
                </div>
              </CardSpotlight>
            ))}
          </TooltipProvider>
        </div>
      </div>
    </section>
  );
}
