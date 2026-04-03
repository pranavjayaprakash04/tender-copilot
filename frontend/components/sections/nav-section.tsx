"use client";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
const T = { text: "#1d1d1f", bg: "rgba(255,255,255,0.8)", border: "rgba(0,0,0,0.1)" };
const L = { text: "#f5f5f7", bg: "rgba(0,0,0,0.7)", border: "rgba(255,255,255,0.1)" };
export function NavSection() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  const theme = scrolled ? T : L;
  return (
    <nav style={{
      position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
      background: theme.bg, backdropFilter: "blur(20px) saturate(180%)",
      borderBottom: `1px solid ${theme.border}`, transition: "all 0.3s ease"
    }}>
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "16px 24px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ fontSize: 22, fontWeight: 700, color: theme.text, letterSpacing: "-0.02em" }}>Tender Copilot</div>
        <div style={{ display: "flex", gap: 32, alignItems: "center" }}>
          {["Features", "Copilot", "Pricing"].map(item => (
            <a key={item} href={`#${item.toLowerCase()}`} style={{ color: theme.text, textDecoration: "none", fontSize: 15, fontWeight: 500 }}>{item}</a>
          ))}
          <Button variant="accent" size="sm" onClick={() => window.location.href = "/register"}>Get Started</Button>
        </div>
      </div>
    </nav>
  );
}
