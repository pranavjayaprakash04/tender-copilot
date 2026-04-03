export function FooterSection() {
  return (
    <footer style={{ background: "#f5f5f7", padding: "64px 24px 32px" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto", textAlign: "center" }}>
        <div style={{ fontSize: 24, fontWeight: 700, color: "#1d1d1f", marginBottom: 32 }}>Tender Copilot</div>
        <div style={{ display: "flex", justifyContent: "center", gap: 32, marginBottom: 32, flexWrap: "wrap" }}>
          {["Privacy Policy", "Terms of Service", "Support", "Razorpay Secured"].map(item => (
            <a key={item} href="#" style={{ color: "#6e6e73", textDecoration: "none", fontSize: 14, fontWeight: 500 }}>{item}</a>
          ))}
        </div>
        <div style={{ color: "#86868b", fontSize: 13 }}>
          © 2025 Tender Copilot · Made in Coimbatore 🇮🇳
        </div>
      </div>
    </footer>
  );
}
