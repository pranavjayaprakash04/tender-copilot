"use client";
import { useState } from "react";
export function TooltipProvider({ children }: { children: React.ReactNode }) { return <>{children}</>; }
export function Tooltip({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const kids = (Array.isArray(children) ? children : [children]).filter(Boolean) as React.ReactElement[];
  return (
    <div style={{ position: "relative", display: "inline-flex" }} onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      {kids.map((child, i) => {
        if (child.type === TooltipContent) return open ? <child.type key={`tc-${i}`} {...child.props} /> : null;
        return <child.type key={`tt-${i}`} {...child.props} />;
      })}
    </div>
  );
}
export function TooltipTrigger({ children, style = {} }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <div style={{ display: "inline-flex", cursor: "default", ...style }}>{children}</div>;
}
export function TooltipContent({ children, side = "top", sideOffset = 4 }: { children: React.ReactNode; side?: string; sideOffset?: number }) {
  const posStyle = side === "top" ? { bottom: `calc(100% + ${sideOffset + 4}px)`, top: "auto" as const } : { top: `calc(100% + ${sideOffset + 4}px)`, bottom: "auto" as const };
  return (
    <div style={{ position: "absolute", left: "50%", transform: "translateX(-50%)", ...posStyle, background: "#1d1d1f", borderRadius: 8, padding: "6px 12px", fontSize: 12, color: "#fff", whiteSpace: "nowrap", zIndex: 9999, pointerEvents: "none", boxShadow: "0 8px 32px rgba(0,0,0,0.22)", animation: "ttIn 0.15s ease both" }}>
      {children}
    </div>
  );
}
