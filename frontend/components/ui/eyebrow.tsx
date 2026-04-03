interface EyebrowProps { children: React.ReactNode; }
export function Eyebrow({ children }: EyebrowProps) {
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 8, background: "rgba(255,159,10,0.14)", border: "1px solid rgba(255,159,10,0.3)", borderRadius: 999, padding: "6px 16px", marginBottom: 24 }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#FF9F0A", display: "inline-block", boxShadow: "0 0 7px #FF9F0A" }} />
      <span style={{ color: "#FF9F0A", fontSize: 11, fontWeight: 600, letterSpacing: "0.1em" }}>{children}</span>
    </div>
  );
}
