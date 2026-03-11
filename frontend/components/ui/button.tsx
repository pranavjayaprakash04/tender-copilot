"use client";
import React from "react";
const _bv: Record<string, { background: string; color: string; border: string; shadow: string }> = {
  default:      { background: "#1d1d1f", color: "#fff",     border: "none",                              shadow: "none" },
  destructive:  { background: "#FF3B30", color: "#fff",     border: "none",                              shadow: "none" },
  outline:      { background: "transparent", color: "#1d1d1f", border: "1.5px solid #d2d2d7",            shadow: "none" },
  secondary:    { background: "#f5f5f7", color: "#1d1d1f", border: "none",                              shadow: "none" },
  ghost:        { background: "transparent", color: "#6e6e73", border: "none",                           shadow: "none" },
  link:         { background: "transparent", color: "#FF9F0A", border: "none",                           shadow: "none" },
  accent:       { background: "linear-gradient(135deg, #e68900, #FF9F0A)", color: "#fff", border: "none", shadow: "0 4px 28px rgba(255,159,10,0.32)" },
  "outline-dark": { background: "transparent", color: "#f5f5f7", border: "1.5px solid rgba(255,255,255,0.22)", shadow: "none" },
};
const _bs: Record<string, { padding: string; fontSize: number; width?: number; height?: number }> = {
  default: { padding: "11px 22px", fontSize: 15 },
  sm:      { padding: "8px 18px",  fontSize: 13 },
  lg:      { padding: "16px 36px", fontSize: 17 },
  icon:    { padding: "10px",      fontSize: 15, width: 42, height: 42 },
};
interface ButtonProps { children: React.ReactNode; variant?: string; size?: string; onClick?: () => void; disabled?: boolean; style?: React.CSSProperties; }
export function Button({ children, variant = "default", size = "default", onClick, disabled = false, style = {} }: ButtonProps) {
  const v = _bv[variant] ?? _bv.default;
  const s = _bs[size]    ?? _bs.default;
  return (
    <button onClick={onClick} disabled={disabled}
      onMouseEnter={e => { if (!disabled) { e.currentTarget.style.filter = "brightness(0.85)"; e.currentTarget.style.transform = "scale(0.975)"; }}}
      onMouseLeave={e => { e.currentTarget.style.filter = "brightness(1)"; e.currentTarget.style.transform = "scale(1)"; }}
      style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", borderRadius: 980, fontWeight: 600, cursor: disabled ? "not-allowed" : "pointer", fontFamily: "inherit", letterSpacing: "-0.01em", whiteSpace: "nowrap", transition: "transform 0.2s ease, filter 0.2s ease", opacity: disabled ? 0.45 : 1, background: v.background, color: v.color, border: v.border, boxShadow: v.shadow, ...s, ...style }}>
      {children}
    </button>
  );
}
