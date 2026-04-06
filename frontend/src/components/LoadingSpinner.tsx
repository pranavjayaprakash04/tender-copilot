"use client";

interface LoadingSpinnerProps {
  fullScreen?: boolean;
  message?: string;
}

export default function LoadingSpinner({ fullScreen = false, message }: LoadingSpinnerProps) {
  const content = (
    <div className="flex flex-col items-center justify-center gap-4">
      {/* Spinning ring around logo icon */}
      <div style={{ position: "relative", width: 64, height: 64 }}>
        {/* Outer spinning ring */}
        <svg
          width="64" height="64" viewBox="0 0 64 64"
          style={{ position: "absolute", top: 0, left: 0, animation: "tc-spin 1.2s linear infinite" }}
        >
          <style>{`@keyframes tc-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
          <circle cx="32" cy="32" r="28" fill="none" stroke="#1E3A6E" strokeWidth="3"/>
          <path d="M32 4 A28 28 0 0 1 60 32" fill="none" stroke="#1E5EFF" strokeWidth="3" strokeLinecap="round"/>
          {/* Teal dot on arc tip */}
          <circle cx="60" cy="32" r="3" fill="#00C6B3"/>
        </svg>
        {/* Logo icon in center */}
        <img
          src="/logo-icon.png"
          alt="Loading"
          style={{ position: "absolute", top: 10, left: 10, width: 44, height: 44, borderRadius: 8 }}
        />
      </div>
      {message && (
        <p style={{ color: "#7B9CC8", fontSize: 13, fontFamily: "system-ui, sans-serif" }}>{message}</p>
      )}
    </div>
  );

  if (fullScreen) {
    return (
      <div style={{
        position: "fixed", inset: 0, zIndex: 9999,
        background: "#020B18",
        display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        {content}
      </div>
    );
  }

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "3rem 0" }}>
      {content}
    </div>
  );
}
