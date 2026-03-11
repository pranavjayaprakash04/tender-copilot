"use client";
import { useState } from "react";
interface AvatarProps { children: React.ReactNode; style?: React.CSSProperties; }
export function Avatar({ children, style = {} }: AvatarProps) {
  return (
    <div style={{ position: "relative", flexShrink: 0, borderRadius: "50%", overflow: "hidden", width: 40, height: 40, display: "flex", alignItems: "center", justifyContent: "center", ...style }}>
      {children}
    </div>
  );
}
interface AvatarImageProps { src: string; alt: string; style?: React.CSSProperties; }
export function AvatarImage({ src, alt, style = {} }: AvatarImageProps) {
  const [failed, setFailed] = useState(false);
  if (failed) return null;
  return (
    <img src={src} alt={alt} onError={() => setFailed(true)}
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", borderRadius: "50%", ...style }} />
  );
}
interface AvatarFallbackProps { children: React.ReactNode; style?: React.CSSProperties; }
export function AvatarFallback({ children, style = {} }: AvatarFallbackProps) {
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", borderRadius: "50%", background: "#f5f5f7", color: "#1d1d1f", fontSize: 11, fontWeight: 700, letterSpacing: "0.02em", ...style }}>
      {children}
    </div>
  );
}
