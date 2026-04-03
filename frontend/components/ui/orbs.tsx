interface OrbsProps { dark?: boolean; count?: number; }
export function Orbs({ dark = true, count = 3 }: OrbsProps) {
  const dColors = ["rgba(255,159,10,0.07)","rgba(255,159,10,0.04)","rgba(255,255,255,0.02)","rgba(230,137,0,0.05)"];
  const lColors = ["rgba(255,159,10,0.05)","rgba(255,159,10,0.03)","rgba(0,0,0,0.015)","rgba(255,159,10,0.04)"];
  const colors  = dark ? dColors : lColors;
  const defs    = [
    { x: "8%",  y: "12%", s: 400, d: "9s",  delay: "0s"   },
    { x: "70%", y: "52%", s: 300, d: "13s", delay: "2.2s" },
    { x: "46%", y: "4%", s: 480, d: "16s", delay: "4.5s" },
    { x: "16%", y: "76%", s: 240, d: "10s", delay: "1.1s" },
  ];
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none", zIndex: 0 }}>
      {defs.slice(0, count).map((o, i) => (
        <div key={i} style={{
          position: "absolute", borderRadius: "50%", width: o.s, height: o.s,
          left: o.x, top: o.y, background: colors[i], filter: "blur(100px)",
          animation: `orbDrift ${o.d} ease-in-out ${o.delay} infinite alternate`,
        }} />
      ))}
    </div>
  );
}
