import { AnimatedTooltipMotion } from "@/components/ui/animated-tooltip";
import { Tilt } from "@/components/ui/tilt";
import { CardSpotlight } from "@/components/ui/card-spotlight";
import { Orbs } from "@/components/ui/orbs";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { Eyebrow } from "@/components/ui/eyebrow";
export function SocialSection() {
  const stats = [
    { n: "₹2.4Cr+", l: "Tenders Won" },
    { n: "500+", l: "MSMEs" },
    { n: "94%", l: "Acceptance Rate" },
    { n: "< 2 min", l: "Per Bid" }
  ];
  const testimonials = [
    { name: "Ramesh Textiles", role: "GST Trader · Coimbatore", text: "Won 3 GeM tenders in first month. The AI bid writer saved us 4 hours per bid.", img: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=80&h=80&fit=crop&crop=face", fallback: "RT" },
    { name: "Meera Fabricators", role: "MSME · Tirupur", text: "The NIT risk detector flagged a penalty clause our lawyer missed. Worth every rupee.", img: "https://images.unsplash.com/photo-1494790108755-2616b9d7cb32?w=80&h=80&fit=crop&crop=face", fallback: "MF" },
    { name: "Arun Agencies", role: "Supplier · Chennai", text: "Tamil language support means our whole team can use it — not just me.", img: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=80&h=80&fit=crop&crop=face", fallback: "AA" },
  ];
  return (
    <section style={{ background: "#fff", padding: "120px 24px", position: "relative", overflow: "hidden" }}>
      <Orbs dark={false} count={3} />
      <div style={{ maxWidth: 1200, margin: "0 auto", position: "relative", zIndex: 1 }}>
        <Eyebrow>TRUSTED BY MSMEs ACROSS INDIA</Eyebrow>
        <h2 style={{ fontSize: "clamp(36px, 5vw, 56px)", fontWeight: 800, color: "#1d1d1f", letterSpacing: "-0.03em", marginBottom: 64, textAlign: "center" }}>500+ businesses. One decision.</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 32, marginBottom: 96 }}>
          {stats.map(stat => (
            <div key={stat.n} style={{ textAlign: "center" }}>
              <div style={{ fontSize: "clamp(32px, 4vw, 48px)", fontWeight: 800, color: "#FF9F0A", marginBottom: 8 }}>{stat.n}</div>
              <div style={{ fontSize: 16, color: "#6e6e73", fontWeight: 500 }}>{stat.l}</div>
            </div>
          ))}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: 32 }}>
          {testimonials.map(testimonial => (
            <CardSpotlight key={testimonial.name}>
              <div style={{ padding: 32 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}>
                  <Avatar>
                    <AvatarImage src={testimonial.img} alt={testimonial.name} />
                    <AvatarFallback>{testimonial.fallback}</AvatarFallback>
                  </Avatar>
                  <div>
                    <div style={{ fontSize: 16, fontWeight: 600, color: "#1d1d1f" }}>{testimonial.name}</div>
                    <div style={{ fontSize: 14, color: "#6e6e73" }}>{testimonial.role}</div>
                  </div>
                </div>
                <p style={{ fontSize: 15, color: "#1d1d1f", lineHeight: 1.6, margin: 0 }}>"{testimonial.text}"</p>
              </div>
            </CardSpotlight>
          ))}
        </div>
        <div style={{ textAlign: "center", marginTop: 64 }}>
          <AnimatedTooltipMotion />
        </div>
      </div>
    </section>
  );
}
