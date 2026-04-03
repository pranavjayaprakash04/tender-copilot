import { Tilt } from "@/components/ui/tilt";
import { Orbs } from "@/components/ui/orbs";
import { Eyebrow } from "@/components/ui/eyebrow";
import { MessageLoading } from "@/components/ui/message-loading";
import { Typewriter } from "@/components/ui/typewriter-text";
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "@/components/ui/tooltip";
export function CopilotSection() {
  const risks = [
    { tag: "🔴 Section 7.2 — Penalty", desc: "Excessive penalty clause: 10% per day delay exceeds industry norm of 2-3%" },
    { tag: "🟠 Section 12 — Timeline", desc: "Delivery timeline of 7 days for custom fabrication is unrealistic for MSMEs" },
    { tag: "🔴 Section 18 — EMD", desc: "EMD amount of ₹5L exceeds GeM limit of ₹2L for this tender value" }
  ];
  return (
    <section id="copilot" style={{ background: "#000", padding: "120px 24px", position: "relative", overflow: "hidden" }}>
      <Orbs count={3} />
      <div style={{ maxWidth: 1000, margin: "0 auto", position: "relative", zIndex: 1 }}>
        <Eyebrow>AI COPILOT</Eyebrow>
        <h2 style={{ fontSize: "clamp(36px, 5vw, 56px)", fontWeight: 800, color: "#fff", letterSpacing: "-0.03em", marginBottom: 64, textAlign: "center" }}>Your AI tender expert. Always on.</h2>
        <Tilt>
          <div style={{
            background: "rgba(255,255,255,0.05)", backdropFilter: "blur(20px) saturate(180%)",
            border: "1px solid rgba(255,255,255,0.1)", borderRadius: 20,
            padding: 32, maxWidth: 800, margin: "0 auto"
          }}>
            <div style={{ display: "flex", gap: 12, marginBottom: 24 }}>
              <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#FF5F57" }} />
              <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#FFBD2E" }} />
              <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#28CA42" }} />
            </div>
            <div style={{ marginBottom: 24 }}>
              <div style={{ background: "#FF9F0A", color: "#fff", padding: "12px 16px", borderRadius: 16, maxWidth: "70%", marginLeft: "auto", marginBottom: 12 }}>
                Analyse this NIT and flag risky clauses for my textile business.
              </div>
              <div style={{ display: "flex", justifyContent: "flex-start", alignItems: "center", gap: 8 }}>
                <MessageLoading />
              </div>
              <div style={{ background: "rgba(255,255,255,0.1)", color: "#fff", padding: "12px 16px", borderRadius: 16, maxWidth: "90%", marginBottom: 12 }}>
                <Typewriter text="I found 3 high-risk clauses in Section 7.2 (penalty terms), Section 12 (delivery timeline unrealistic for SMEs), and Section 18 (EMD amount exceeds GeM norms). Here is a full breakdown..." speed={30} cursor="▊" />
              </div>
            </div>
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              <TooltipProvider>
                {risks.map((risk, i) => (
                  <Tooltip key={i}>
                    <TooltipTrigger>
                      <div style={{
                        background: risk.tag.startsWith("🔴") ? "rgba(255,59,48,0.1)" : "rgba(255,159,10,0.1)",
                        border: risk.tag.startsWith("🔴") ? "1px solid rgba(255,59,48,0.3)" : "1px solid rgba(255,159,10,0.3)",
                        borderRadius: 8, padding: "6px 12px", fontSize: 12, fontWeight: 500,
                        color: risk.tag.startsWith("🔴") ? "#FF3B30" : "#FF9F0A", cursor: "default"
                      }}>
                        {risk.tag}
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>{risk.desc}</TooltipContent>
                  </Tooltip>
                ))}
              </TooltipProvider>
            </div>
          </div>
        </Tilt>
      </div>
    </section>
  );
}
