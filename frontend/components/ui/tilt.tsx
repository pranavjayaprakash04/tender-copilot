"use client";
import { useRef, useCallback } from "react";
interface TiltProps { children: React.ReactNode; deg?: number; z?: number; scale?: number; style?: React.CSSProperties; }
export function Tilt({ children, deg = 16, z = 12, scale = 1.015, style = {} }: TiltProps) {
  const ref = useRef<HTMLDivElement>(null);
  const onMove = useCallback((e: React.MouseEvent) => {
    if (!ref.current) return;
    const r  = ref.current.getBoundingClientRect();
    const rx = ((e.clientY - r.top)  / r.height - 0.5) * -deg;
    const ry = ((e.clientX - r.left) / r.width  - 0.5) *  deg;
    ref.current.style.transform = `perspective(900px) rotateX(${rx}deg) rotateY(${ry}deg) translateZ(${z}px) scale(${scale})`;
  }, [deg, z, scale]);
  const onLeave = useCallback(() => {
    if (!ref.current) return;
    ref.current.style.transform = "perspective(900px) rotateX(0deg) rotateY(0deg) translateZ(0) scale(1)";
  }, []);
  return (
    <div ref={ref} onMouseMove={onMove} onMouseLeave={onLeave}
      style={{ transition: "transform 0.18s cubic-bezier(0.23,1,0.32,1)", transformStyle: "preserve-3d", ...style }}>
      {children}
    </div>
  );
}
