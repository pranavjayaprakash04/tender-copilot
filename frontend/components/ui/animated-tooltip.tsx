"use client";
import { useState } from "react";
type Item = { id: number; name: string; designation: string; image: string; };
function TooltipItem({ item }: { item: Item }) {
  const [visible, setVisible] = useState(false);
  const [offset, setOffset] = useState(0);
  const handleMove = (e: React.MouseEvent<HTMLImageElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    setOffset(e.clientX - r.left - r.width / 2);
  };
  const tX  = (offset / 80) * 40;
  const rot = (offset / 80) * 18;
  return (
    <div style={{ position: "relative", display: "inline-block", margin: "0 -5px", zIndex: visible ? 20 : 1 }}>
      {visible && (
        <div style={{ position: "absolute", bottom: "calc(100% + 14px)", left: "50%", transform: `translateX(calc(-50% + ${tX}px)) rotate(${rot}deg)`, background: "#1d1d1f", borderRadius: 10, padding: "8px 14px", pointerEvents: "none", whiteSpace: "nowrap", zIndex: 300, boxShadow: "0 20px 60px rgba(0,0,0,0.28)", transition: "transform 0.1s ease" }}>
          <p style={{ color: "#f5f5f7", fontSize: 13, fontWeight: 600, margin: 0 }}>{item.name}</p>
          <p style={{ color: "#86868b", fontSize: 11, margin: "2px 0 0" }}>{item.designation}</p>
        </div>
      )}
      <img src={item.image} alt={item.name} width={44} height={44}
        onMouseEnter={e => { setVisible(true); e.currentTarget.style.transform = "scale(1.22) translateY(-5px)"; e.currentTarget.style.zIndex = "50"; }}
        onMouseMove={handleMove}
        onMouseLeave={e => { setVisible(false); e.currentTarget.style.transform = "scale(1) translateY(0)"; e.currentTarget.style.zIndex = "1"; }}
        style={{ width: 44, height: 44, borderRadius: "50%", objectFit: "cover", objectPosition: "top", border: "2.5px solid rgba(255,255,255,0.9)", cursor: "default", transition: "transform 0.35s cubic-bezier(0.34,1.56,0.64,1)", display: "block", position: "relative", zIndex: 1 }}
      />
    </div>
  );
}
export function AnimatedTooltipMotion() {
  const items: Item[] = [
    { id: 1, name: "Aarav Mehta",    designation: "AI Researcher",         image: "https://images.shadcnspace.com/assets/profiles/user-1.jpg" },
    { id: 2, name: "Sofia Martinez", designation: "Cloud Architect",       image: "https://images.shadcnspace.com/assets/profiles/user-2.jpg" },
    { id: 3, name: "Kenji Tanaka",   designation: "Cybersecurity Analyst", image: "https://images.shadcnspace.com/assets/profiles/user-3.jpg" },
    { id: 4, name: "Amelia Rossi",   designation: "UX Strategist",         image: "https://images.shadcnspace.com/assets/profiles/user-4.jpg" },
  ];
  return (
    <div style={{ display: "flex", alignItems: "center", paddingLeft: 6 }}>
      {items.map(item => <TooltipItem key={item.id} item={item} />)}
    </div>
  );
}
