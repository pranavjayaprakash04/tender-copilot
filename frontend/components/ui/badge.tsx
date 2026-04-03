"use client";
import React from "react";

const VARIANTS: Record<string, { background: string; color: string; border: string }> = {
  default:     { background: "#1d1d1f", color: "#fff", border: "transparent" },
  success:     { background: "#10B98122", color: "#059669", border: "#10B98140" },
  warning:     { background: "#F59E0B22", color: "#B45309", border: "#F59E0B40" },
  danger:      { background: "#EF444422", color: "#DC2626", border: "#EF444440" },
  outline:     { background: "transparent", color: "#374151", border: "#D1D5DB" },
  info:        { background: "#3B82F622", color: "#1D4ED8", border: "#3B82F640" },
};

interface BadgeProps {
  children: React.ReactNode;
  variant?: keyof typeof VARIANTS;
  className?: string;
  style?: React.CSSProperties;
}

export function Badge({ children, variant = "default", className, style }: BadgeProps) {
  const v = VARIANTS[variant] ?? VARIANTS.default;
  return (
    <span
      className={className}
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 10px",
        borderRadius: 9999,
        fontSize: 12,
        fontWeight: 600,
        letterSpacing: "0.01em",
        background: v.background,
        color: v.color,
        border: `1px solid ${v.border}`,
        ...style,
      }}
    >
      {children}
    </span>
  );
}

export default Badge;
