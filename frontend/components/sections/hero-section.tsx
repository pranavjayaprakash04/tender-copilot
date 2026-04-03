"use client";
import { HeroCanvas } from "@/components/three/hero-canvas";
import { Orbs } from "@/components/ui/orbs";
import { Tilt } from "@/components/ui/tilt";
import { Typewriter } from "@/components/ui/typewriter-text";
import { Button } from "@/components/ui/button";
import { Eyebrow } from "@/components/ui/eyebrow";
export function HeroSection() {
  return (
    <section style={{ position: "relative", minHeight: "100vh", background: "#000", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
      <HeroCanvas />
      <Orbs count={4} />
      <div style={{ position: "relative", zIndex: 10, textAlign: "center", maxWidth: 900, padding: "0 24px" }}>
        <Eyebrow>AI-POWERED · BUILT FOR INDIAN MSMEs</Eyebrow>
        <h1 style={{ fontSize: "clamp(48px, 8vw, 96px)", fontWeight: 800, color: "#fff", letterSpacing: "-0.04em", lineHeight: 1.1, marginBottom: 32 }}>
          Win government tenders. <Typewriter text={["AI writes bid.", "Zero guesswork.", "₹499 / month.", "GeM ready.", "Tamil & English."]} speed={78} deleteSpeed={40} delay={1900} loop={true} />
        </h1>
        <p style={{ fontSize: "clamp(18px, 2.5vw, 24px)", color: "#86868b", lineHeight: 1.6, marginBottom: 48, maxWidth: 640, margin: "0 auto 48px" }}>
          Tender Copilot discovers tenders, analyses every clause, flags risks, and writes winning bid documents — in under 2 minutes.
        </p>
        <div style={{ display: "flex", gap: 20, justifyContent: "center", flexWrap: "wrap" }}>
          <Tilt>
            <Button variant="accent" size="lg" onClick={() => window.location.href = "/register"}>Start free trial</Button>
          </Tilt>
          <Tilt>
            <Button variant="outline-dark" size="lg" onClick={() => window.location.href = "#copilot"}>Watch demo →</Button>
          </Tilt>
        </div>
      </div>
      <div style={{ position: "absolute", bottom: 32, left: "50%", transform: "translateX(-50%)", animation: "scrollGrow 2s ease-in-out infinite" }}>
        <div style={{ width: 2, height: 32, background: "linear-gradient(to bottom, #FF9F0A, transparent)", borderRadius: 1 }} />
      </div>
    </section>
  );
}
