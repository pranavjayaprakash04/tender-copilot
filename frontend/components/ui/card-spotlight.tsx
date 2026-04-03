"use client";
import { useRef } from "react";
interface CardProps { children: React.ReactNode; dark?: boolean; style?: React.CSSProperties; }
export function CardSpotlight({ children, dark = false, style = {} }: CardProps) {
  const ref  = useRef<HTMLDivElement>(null);
  const spot = useRef<HTMLDivElement>(null);
  const onMove = (e: React.MouseEvent) => {
    if (!ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width;
    const y = (e.clientY - r.top)  / r.height;
    ref.current.style.transform = `perspective(900px) rotateX(${(y-0.5)*-13}deg) rotateY(${(x-0.5)*13}deg) translateZ(14px) scale(1.012)`;
    ref.current.style.boxShadow = dark ? "0 36px 90px rgba(0,0,0,0.55)" : "0 16px 48px rgba(0,0,0,0.11)";
    if (spot.current) {
      spot.current.style.opacity = "1";
      spot.current.style.background = `radial-gradient(circle at ${x*100}% ${y*100}%, ${dark ? "rgba(255,255,255,0.08)" : "rgba(255,255,255,0.6)"} 0%, transparent 65%)`;
    }
  };
  const onLeave = () => {
    if (!ref.current) return;
    ref.current.style.transform = "perspective(900px) rotateX(0) rotateY(0) translateZ(0) scale(1)";
    ref.current.style.boxShadow = dark ? "0 24px 60px rgba(0,0,0,0.42)" : "0 2px 16px rgba(0,0,0,0.06)";
    if (spot.current) spot.current.style.opacity = "0";
  };
  return (
    <div ref={ref} onMouseMove={onMove} onMouseLeave={onLeave} style={{
      background: dark ? "rgba(255,255,255,0.04)" : "#ffffff",
      border: `1px solid ${dark ? "rgba(255,255,255,0.10)" : "rgba(0,0,0,0.08)"}`,
      borderRadius: 20, boxShadow: dark ? "0 24px 60px rgba(0,0,0,0.42)" : "0 2px 16px rgba(0,0,0,0.06)",
      transition: "transform 0.2s cubic-bezier(0.23,1,0.32,1), box-shadow 0.2s ease",
      transformStyle: "preserve-3d", position: "relative", overflow: "hidden", ...style,
    }}>
      <div ref={spot} style={{ position: "absolute", inset: 0, opacity: 0, transition: "opacity 0.22s", pointerEvents: "none", zIndex: 2, borderRadius: 20 }} />
      <div style={{ position: "relative", zIndex: 1 }}>{children}</div>
    </div>
  );
}
