"use client";

interface LoadingSpinnerProps {
  fullScreen?: boolean;
  message?: string;
}

// Inline SVG spinning hexagon — no logo-icon.png needed
function SpinningHexagon() {
  return (
    <div style={{ position: "relative", width: 52, height: 52 }}>
      {/* Spinning ring */}
      <svg
        width="52"
        height="52"
        viewBox="0 0 52 52"
        fill="none"
        style={{ animation: "spin 1.2s linear infinite", position: "absolute", top: 0, left: 0 }}
      >
        <circle cx="26" cy="26" r="22" stroke="#3B82F6" strokeWidth="3" strokeDasharray="100 40" strokeLinecap="round" opacity="0.6"/>
        <style>{`@keyframes spin { to { transform: rotate(360deg); transform-origin: 26px 26px; } }`}</style>
      </svg>
      {/* Static hexagon in center */}
      <svg
        width="52"
        height="52"
        viewBox="0 0 48 48"
        fill="none"
        style={{ position: "absolute", top: 0, left: 0 }}
      >
        <polygon points="24,6 40,15 40,33 24,42 8,33 8,15" fill="#0F172A" stroke="#3B82F6" strokeWidth="1.5"/>
        <path d="M20 28 L28 21" stroke="#3B82F6" strokeWidth="1.8" strokeLinecap="round"/>
        <path d="M25 21 L28 21 L28 24" stroke="#3B82F6" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    </div>
  );
}

export default function LoadingSpinner({ fullScreen = false, message = "Loading..." }: LoadingSpinnerProps) {
  if (fullScreen) {
    return (
      <div
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(255,255,255,0.85)",
          backdropFilter: "blur(4px)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 9999,
          gap: 16,
        }}
      >
        <SpinningHexagon />
        <p style={{ fontSize: 13, color: "#64748B", fontWeight: 500 }}>{message}</p>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12, padding: 32 }}>
      <SpinningHexagon />
      <p style={{ fontSize: 13, color: "#64748B" }}>{message}</p>
    </div>
  );
}
