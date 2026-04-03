import { Tilt } from "@/components/ui/tilt";
import { Orbs } from "@/components/ui/orbs";
import { Eyebrow } from "@/components/ui/eyebrow";
import { Button } from "@/components/ui/button";
import { Typewriter } from "@/components/ui/typewriter-text";
import { AnimatedTooltipMotion } from "@/components/ui/animated-tooltip";
export function PricingSection() {
  const features = [
    "Unlimited tender discovery",
    "PDF / NIT clause analysis", 
    "AI bid generation — English + Tamil",
    "Risk & red-flag detector",
    "Persistent company memory",
    "Tender-specific AI chatbot",
    "WhatsApp alerts for new tenders"
  ];
  return (
    <section id="pricing" style={{ background: "#000", padding: "120px 24px", position: "relative", overflow: "hidden" }}>
      <Orbs count={3} />
      <div style={{ maxWidth: 800, margin: "0 auto", position: "relative", zIndex: 1, textAlign: "center" }}>
        <Eyebrow>PRICING</Eyebrow>
        <h2 style={{ fontSize: "clamp(36px, 5vw, 56px)", fontWeight: 800, color: "#fff", letterSpacing: "-0.03em", marginBottom: 64 }}>Simple. MSME-first.</h2>
        <Tilt>
          <div style={{
            background: "rgba(255,255,255,0.05)", backdropFilter: "blur(20px) saturate(180%)",
            border: "1px solid rgba(255,255,255,0.1)", borderRadius: 20,
            padding: 48, position: "relative", overflow: "hidden"
          }}>
            <div style={{ height: 4, background: "linear-gradient(90deg, #e68900, #FF9F0A)", position: "absolute", top: 0, left: 0, right: 0 }} />
            <div style={{ fontSize: 64, fontWeight: 800, color: "#FF9F0A", marginBottom: 16 }}>₹499</div>
            <div style={{ fontSize: 18, color: "#86868b", marginBottom: 48 }}>per month</div>
            <div style={{ textAlign: "left", marginBottom: 48 }}>
              {features.map(feature => (
                <div key={feature} style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
                  <span style={{ color: "#FF9F0A", fontSize: 16 }}>✦</span>
                  <span style={{ color: "#fff", fontSize: 15 }}>{feature}</span>
                </div>
              ))}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 16, alignItems: "center" }}>
              <Button variant="accent" size="lg" onClick={() => window.location.href = "/register"}>
                Start free 7-day trial
              </Button>
              <div style={{ fontSize: 14, color: "#86868b" }}>No credit card required</div>
              <Button variant="secondary" onClick={() => window.location.href = "/contact-sales"}>
                Contact sales →
              </Button>
            </div>
          </div>
        </Tilt>
        <div style={{ marginTop: 64 }}>
          <Typewriter text={[
            "MSMEs across Coimbatore trust Tender Copilot.",
            "Win your first tender this week.",
            "Built for Coimbatore MSME belt.",
            "GeM + CPPP + State portals, all in one."
          ]} speed={80} delay={3000} loop={true} />
        </div>
        <div style={{ marginTop: 32 }}>
          <AnimatedTooltipMotion />
        </div>
      </div>
    </section>
  );
}
