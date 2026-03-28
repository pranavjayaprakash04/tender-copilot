"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

// ─── Types ────────────────────────────────────────────────────────────────────

interface CompetitorInsight {
  competitor_name: string;
  estimated_bid: number | null;
  win_probability: number;
  strengths: string[];
  weaknesses: string[];
}

interface CompetitorAnalysisResponse {
  tender_id: string;
  company_id: string;
  insights: CompetitorInsight[];
  our_win_probability: number;
  recommended_price: number | null;
  analysis_lang: string;
  generated_at: string;
}

interface WinProbabilityResponse {
  tender_id: string;
  win_probability: number;
  confidence: string;
  factors: string[];
  market_avg: number | null;
  recommended_range: { min: number; max: number } | null;
}

interface MarketPriceResponse {
  category: string;
  avg_price: number;
  min_price: number;
  max_price: number;
  sample_count: number;
  last_refreshed: string;
}

interface Bid {
  id: string;
  tender_id: string;
  tender_title: string;
  organisation: string;
  status: string;
  deadline: string;
  estimated_value: number | null;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const fmt = (n: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);

const pct = (n: number) => `${(n * 100).toFixed(1)}%`;

const winColor = (p: number) => {
  if (p >= 0.7) return "#10B981";
  if (p >= 0.4) return "#F59E0B";
  return "#EF4444";
};

const confidenceBadge = (c: string) => {
  const map: Record<string, string> = { high: "#10B981", medium: "#F59E0B", low: "#EF4444" };
  return map[c?.toLowerCase()] ?? "#6B7280";
};

// ─── Win Probability Ring ─────────────────────────────────────────────────────

function WinRing({ probability }: { probability: number }) {
  const r = 54;
  const circ = 2 * Math.PI * r;
  const dash = circ * probability;
  const color = winColor(probability);

  return (
    <svg width="140" height="140" viewBox="0 0 140 140">
      <circle cx="70" cy="70" r={r} fill="none" stroke="#1E2130" strokeWidth="12" />
      <circle
        cx="70" cy="70" r={r}
        fill="none"
        stroke={color}
        strokeWidth="12"
        strokeDasharray={`${dash} ${circ}`}
        strokeLinecap="round"
        transform="rotate(-90 70 70)"
        style={{ transition: "stroke-dasharray 1s ease" }}
      />
      <text x="70" y="65" textAnchor="middle" fill={color} fontSize="22" fontWeight="700" fontFamily="'DM Sans', sans-serif">
        {(probability * 100).toFixed(0)}%
      </text>
      <text x="70" y="83" textAnchor="middle" fill="#64748B" fontSize="11" fontFamily="'DM Sans', sans-serif">
        Win Chance
      </text>
    </svg>
  );
}

// ─── Competitor Card ──────────────────────────────────────────────────────────

function CompetitorCard({ c, rank }: { c: CompetitorInsight; rank: number }) {
  const [open, setOpen] = useState(false);
  const color = winColor(c.win_probability);

  return (
    <div className="comp-card">
      <div className="comp-card-header" onClick={() => setOpen(!open)}>
        <div className="comp-rank" style={{ color }}>{rank}</div>
        <div className="comp-info">
          <span className="comp-name">{c.competitor_name}</span>
          {c.estimated_bid && (
            <span className="comp-bid">{fmt(c.estimated_bid)}</span>
          )}
        </div>
        <div className="comp-prob" style={{ color }}>
          {pct(c.win_probability)}
        </div>
        <div className="comp-bar-wrap">
          <div className="comp-bar" style={{ width: pct(c.win_probability), background: color }} />
        </div>
        <button className="comp-toggle">{open ? "▲" : "▼"}</button>
      </div>

      {open && (
        <div className="comp-details">
          <div className="comp-col">
            <div className="comp-col-title" style={{ color: "#10B981" }}>Strengths</div>
            {c.strengths.map((s, i) => (
              <div key={i} className="comp-item">
                <span className="comp-dot" style={{ background: "#10B981" }} />
                {s}
              </div>
            ))}
          </div>
          <div className="comp-col">
            <div className="comp-col-title" style={{ color: "#EF4444" }}>Weaknesses</div>
            {c.weaknesses.map((w, i) => (
              <div key={i} className="comp-item">
                <span className="comp-dot" style={{ background: "#EF4444" }} />
                {w}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function BidIntelligencePage() {
  const [selectedBidId, setSelectedBidId] = useState<string | null>(null);
  const [selectedTenderId, setSelectedTenderId] = useState<string | null>(null);
  const [bidAmount, setBidAmount] = useState<string>("");
  const [category, setCategory] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"competitors" | "winprob" | "market">("winprob");

  // Fetch bids list
  const { data: bidsData, isLoading: bidsLoading } = useQuery({
    queryKey: ["bids"],
    queryFn: () => api.bids.list(),
  });

  const bids: Bid[] = (bidsData as any)?.bids ?? bidsData ?? [];

  // Win Probability
  const winProbMutation = useMutation<WinProbabilityResponse, Error>({
    mutationFn: () =>
      api.post("/api/v1/intelligence/bid/win-probability", {
        tender_id: selectedTenderId,
        company_id: "current",
        our_bid_amount: bidAmount ? parseFloat(bidAmount) : null,
      }),
  });

  // Competitor Analysis
  const competitorMutation = useMutation<CompetitorAnalysisResponse, Error>({
    mutationFn: () =>
      api.post("/api/v1/intelligence/bid/analyze-competitors", {
        tender_id: selectedTenderId,
        company_id: "current",
        lang: "en",
      }),
  });

  // Market Price
  const { data: marketData, isLoading: marketLoading, refetch: fetchMarket } = useQuery<MarketPriceResponse>({
    queryKey: ["market-price", category],
    queryFn: () => api.get(`/api/v1/intelligence/bid/market-price/${encodeURIComponent(category)}`),
    enabled: false,
  });

  const handleSelectBid = (bid: Bid) => {
    setSelectedBidId(bid.id);
    setSelectedTenderId(bid.tender_id || bid.id);
    winProbMutation.reset();
    competitorMutation.reset();
  };

  const winProb = winProbMutation.data;
  const compData = competitorMutation.data;

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap');

        .bi-page{min-height:100vh;background:#0A0D14;color:#E2E8F0;font-family:'DM Sans',sans-serif;padding:32px 24px 64px;max-width:1280px;margin:0 auto}
        .bi-header{margin-bottom:32px}
        .bi-title{font-size:30px;font-weight:700;color:#F1F5F9;letter-spacing:-0.5px;margin:0 0 4px}
        .bi-sub{font-size:14px;color:#475569}

        .bi-layout{display:grid;grid-template-columns:320px 1fr;gap:24px;align-items:start}
        @media(max-width:900px){.bi-layout{grid-template-columns:1fr}}

        /* Bid selector */
        .bid-panel{background:#131620;border:1px solid #1E2537;border-radius:14px;overflow:hidden}
        .bid-panel-title{padding:16px 20px;font-size:13px;font-weight:600;color:#64748B;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid #1E2537}
        .bid-list{max-height:520px;overflow-y:auto}
        .bid-item{padding:14px 20px;cursor:pointer;border-bottom:1px solid #1E2537;transition:background .15s}
        .bid-item:hover{background:#1A1F2E}
        .bid-item--active{background:#1A2540;border-left:3px solid #3B82F6}
        .bid-item-title{font-size:13px;font-weight:600;color:#E2E8F0;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
        .bid-item-org{font-size:11px;color:#475569;margin-bottom:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
        .bid-item-meta{display:flex;gap:8px;align-items:center}
        .bid-status{padding:2px 8px;border-radius:20px;font-size:10px;font-weight:600}
        .bid-status--active{background:#10B98122;color:#10B981}
        .bid-status--closing_soon{background:#F59E0B22;color:#F59E0B}
        .bid-status--closed{background:#6B728022;color:#6B7280}
        .bid-value{font-size:11px;color:#94A3B8;font-family:'Space Mono',monospace}
        .bid-empty{padding:32px;text-align:center;color:#475569;font-size:13px}

        /* Intelligence panel */
        .intel-panel{background:#131620;border:1px solid #1E2537;border-radius:14px;overflow:hidden}
        .intel-empty{padding:80px 32px;text-align:center}
        .intel-empty-icon{font-size:48px;margin-bottom:16px}
        .intel-empty-title{font-size:16px;font-weight:600;color:#E2E8F0;margin-bottom:8px}
        .intel-empty-sub{font-size:13px;color:#475569}

        /* Tabs */
        .tabs{display:flex;border-bottom:1px solid #1E2537}
        .tab{flex:1;padding:14px 16px;text-align:center;font-size:13px;font-weight:500;color:#475569;cursor:pointer;transition:all .15s;border-bottom:2px solid transparent}
        .tab:hover{color:#94A3B8;background:#1A1F2E}
        .tab--active{color:#3B82F6;border-bottom-color:#3B82F6;background:#1A2540}
        .tab-body{padding:24px}

        /* Win probability */
        .win-section{display:flex;flex-direction:column;gap:24px}
        .win-top{display:flex;gap:24px;align-items:center;flex-wrap:wrap}
        .win-ring-wrap{flex-shrink:0}
        .win-meta{flex:1;min-width:200px}
        .win-conf{display:inline-block;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;margin-bottom:12px}
        .win-range{background:#1E2537;border-radius:10px;padding:16px;margin-bottom:16px}
        .win-range-title{font-size:11px;color:#475569;text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px}
        .win-range-row{display:flex;justify-content:space-between;align-items:center}
        .win-range-val{font-size:18px;font-weight:700;color:#F1F5F9;font-family:'Space Mono',monospace}
        .win-range-label{font-size:11px;color:#64748B}
        .win-factors{background:#1E2537;border-radius:10px;padding:16px}
        .win-factors-title{font-size:12px;font-weight:600;color:#94A3B8;margin-bottom:12px}
        .win-factor{display:flex;align-items:flex-start;gap:8px;margin-bottom:8px;font-size:13px;color:#CBD5E1}
        .win-factor-dot{width:6px;height:6px;border-radius:50%;background:#3B82F6;flex-shrink:0;margin-top:5px}
        .win-input-row{display:flex;gap:10px;align-items:flex-end}
        .win-input-wrap{flex:1}
        .win-label{font-size:12px;font-weight:600;color:#64748B;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
        .win-input{width:100%;padding:10px 14px;background:#0A0D14;border:1px solid #1E2537;border-radius:8px;color:#E2E8F0;font-size:14px;font-family:'Space Mono',monospace;outline:none;box-sizing:border-box}
        .win-input:focus{border-color:#3B82F6}
        .win-market-avg{font-size:12px;color:#64748B;margin-top:6px}

        /* Competitors */
        .comp-card{background:#1A1F2E;border:1px solid #1E2537;border-radius:10px;margin-bottom:10px;overflow:hidden}
        .comp-card-header{display:flex;align-items:center;gap:12px;padding:14px 16px;cursor:pointer}
        .comp-rank{font-size:20px;font-weight:700;width:28px;text-align:center;font-family:'Space Mono',monospace}
        .comp-info{flex:1;min-width:0}
        .comp-name{display:block;font-size:13px;font-weight:600;color:#E2E8F0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
        .comp-bid{display:block;font-size:11px;color:#64748B;font-family:'Space Mono',monospace;margin-top:2px}
        .comp-prob{font-size:15px;font-weight:700;font-family:'Space Mono',monospace;flex-shrink:0}
        .comp-bar-wrap{width:80px;height:4px;background:#1E2537;border-radius:2px;flex-shrink:0}
        .comp-bar{height:4px;border-radius:2px;transition:width .8s ease}
        .comp-toggle{background:none;border:none;color:#475569;cursor:pointer;font-size:12px;padding:4px}
        .comp-details{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:0 16px 16px;border-top:1px solid #1E2537;margin-top:-2px;padding-top:14px}
        .comp-col-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
        .comp-item{display:flex;align-items:flex-start;gap:6px;font-size:12px;color:#94A3B8;margin-bottom:6px;line-height:1.4}
        .comp-dot{width:5px;height:5px;border-radius:50%;flex-shrink:0;margin-top:4px}
        .our-win-banner{background:linear-gradient(135deg,#1E3A5F,#1A2540);border:1px solid #3B82F640;border-radius:10px;padding:16px 20px;margin-bottom:16px;display:flex;align-items:center;justify-content:space-between}
        .our-win-label{font-size:13px;color:#94A3B8}
        .our-win-val{font-size:28px;font-weight:700;font-family:'Space Mono',monospace}
        .our-rec-price{font-size:13px;color:#64748B;margin-top:4px}

        /* Market */
        .market-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-bottom:20px}
        .market-card{background:#1A1F2E;border:1px solid #1E2537;border-radius:10px;padding:16px;text-align:center}
        .market-card-val{font-size:22px;font-weight:700;color:#F1F5F9;font-family:'Space Mono',monospace;margin-bottom:4px}
        .market-card-label{font-size:11px;color:#475569;text-transform:uppercase;letter-spacing:.5px}
        .market-bar-section{background:#1A1F2E;border:1px solid #1E2537;border-radius:10px;padding:16px}
        .market-bar-title{font-size:12px;color:#64748B;margin-bottom:12px}
        .market-bar-track{height:8px;background:#1E2537;border-radius:4px;position:relative;margin-bottom:8px}
        .market-bar-fill{height:8px;border-radius:4px;background:linear-gradient(90deg,#3B82F6,#10B981)}
        .market-bar-labels{display:flex;justify-content:space-between;font-size:11px;color:#475569;font-family:'Space Mono',monospace}
        .market-cat-row{display:flex;gap:10px;margin-bottom:16px}
        .market-cat-input{flex:1;padding:10px 14px;background:#0A0D14;border:1px solid #1E2537;border-radius:8px;color:#E2E8F0;font-size:14px;outline:none}
        .market-cat-input:focus{border-color:#3B82F6}
        .market-sample{font-size:12px;color:#475569;margin-top:8px}

        /* Shared */
        .spinner{width:20px;height:20px;border:2px solid #1E2537;border-top-color:#3B82F6;border-radius:50%;animation:spin .7s linear infinite;display:inline-block;vertical-align:middle;margin-right:8px}
        @keyframes spin{to{transform:rotate(360deg)}}
        .error-box{background:#EF444420;border:1px solid #EF444440;border-radius:8px;padding:12px 16px;color:#FCA5A5;font-size:13px;margin-top:12px}
        .section-gap{margin-top:20px}
        .run-btn{padding:10px 20px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;border:none;background:#3B82F6;color:#fff;transition:opacity .15s}
        .run-btn:hover{opacity:.85}
        .run-btn:disabled{opacity:.4;cursor:not-allowed}
      `}</style>

      <div className="bi-page">
        <div className="bi-header">
          <h1 className="bi-title">Bid Intelligence</h1>
          <p className="bi-sub">AI-powered competitor analysis, win probability, and market pricing for your bids</p>
        </div>

        <div className="bi-layout">
          {/* ── Bid Selector ── */}
          <div className="bid-panel">
            <div className="bid-panel-title">Select a Bid</div>
            <div className="bid-list">
              {bidsLoading ? (
                <div className="bid-empty"><span className="spinner" />Loading bids…</div>
              ) : bids.length === 0 ? (
                <div className="bid-empty">No bids found. Create a bid from a tender first.</div>
              ) : (
                bids.map((bid) => (
                  <div
                    key={bid.id}
                    className={`bid-item${selectedBidId === bid.id ? " bid-item--active" : ""}`}
                    onClick={() => handleSelectBid(bid)}
                  >
                    <div className="bid-item-title">{bid.tender_title || "Untitled Tender"}</div>
                    <div className="bid-item-org">{bid.organisation || "—"}</div>
                    <div className="bid-item-meta">
                      <span className={`bid-status bid-status--${bid.status}`}>
                        {bid.status?.replace("_", " ")}
                      </span>
                      {bid.estimated_value && (
                        <span className="bid-value">{fmt(bid.estimated_value)}</span>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* ── Intelligence Panel ── */}
          <div className="intel-panel">
            {!selectedTenderId ? (
              <div className="intel-empty">
                <div className="intel-empty-icon">🎯</div>
                <div className="intel-empty-title">Select a bid to analyse</div>
                <div className="intel-empty-sub">Choose a bid from the left to run AI intelligence analysis</div>
              </div>
            ) : (
              <>
                <div className="tabs">
                  {([
                    { key: "winprob", label: "Win Probability" },
                    { key: "competitors", label: "Competitor Analysis" },
                    { key: "market", label: "Market Price" },
                  ] as const).map((t) => (
                    <div
                      key={t.key}
                      className={`tab${activeTab === t.key ? " tab--active" : ""}`}
                      onClick={() => setActiveTab(t.key)}
                    >
                      {t.label}
                    </div>
                  ))}
                </div>

                <div className="tab-body">

                  {/* ── Win Probability Tab ── */}
                  {activeTab === "winprob" && (
                    <div className="win-section">
                      <div className="win-input-row">
                        <div className="win-input-wrap">
                          <div className="win-label">Your Bid Amount (₹) — Optional</div>
                          <input
                            className="win-input"
                            type="number"
                            placeholder="e.g. 5000000"
                            value={bidAmount}
                            onChange={(e) => setBidAmount(e.target.value)}
                          />
                          {winProb?.market_avg && (
                            <div className="win-market-avg">
                              Market avg: {fmt(winProb.market_avg)}
                            </div>
                          )}
                        </div>
                        <button
                          className="run-btn"
                          disabled={winProbMutation.isPending}
                          onClick={() => winProbMutation.mutate()}
                        >
                          {winProbMutation.isPending ? <><span className="spinner" />Analysing…</> : "Analyse"}
                        </button>
                      </div>

                      {winProbMutation.isError && (
                        <div className="error-box">Analysis failed. Please try again.</div>
                      )}

                      {winProb && (
                        <>
                          <div className="win-top">
                            <div className="win-ring-wrap">
                              <WinRing probability={winProb.win_probability} />
                            </div>
                            <div className="win-meta">
                              <span
                                className="win-conf"
                                style={{
                                  background: confidenceBadge(winProb.confidence) + "22",
                                  color: confidenceBadge(winProb.confidence),
                                }}
                              >
                                {winProb.confidence?.toUpperCase()} CONFIDENCE
                              </span>

                              {winProb.recommended_range && (
                                <div className="win-range">
                                  <div className="win-range-title">Recommended Bid Range</div>
                                  <div className="win-range-row">
                                    <div>
                                      <div className="win-range-val">{fmt(winProb.recommended_range.min)}</div>
                                      <div className="win-range-label">Minimum</div>
                                    </div>
                                    <div style={{ color: "#1E2537", fontSize: 20 }}>→</div>
                                    <div>
                                      <div className="win-range-val">{fmt(winProb.recommended_range.max)}</div>
                                      <div className="win-range-label">Maximum</div>
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>

                          {winProb.factors?.length > 0 && (
                            <div className="win-factors">
                              <div className="win-factors-title">Key Factors</div>
                              {winProb.factors.map((f, i) => (
                                <div key={i} className="win-factor">
                                  <span className="win-factor-dot" />
                                  {f}
                                </div>
                              ))}
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  )}

                  {/* ── Competitor Analysis Tab ── */}
                  {activeTab === "competitors" && (
                    <div>
                      {compData && (
                        <div className="our-win-banner">
                          <div>
                            <div className="our-win-label">Our Win Probability</div>
                            {compData.recommended_price && (
                              <div className="our-rec-price">
                                Recommended price: {fmt(compData.recommended_price)}
                              </div>
                            )}
                          </div>
                          <div
                            className="our-win-val"
                            style={{ color: winColor(compData.our_win_probability) }}
                          >
                            {pct(compData.our_win_probability)}
                          </div>
                        </div>
                      )}

                      <button
                        className="run-btn"
                        disabled={competitorMutation.isPending}
                        onClick={() => competitorMutation.mutate()}
                        style={{ marginBottom: 16 }}
                      >
                        {competitorMutation.isPending
                          ? <><span className="spinner" />Analysing competitors…</>
                          : compData ? "Re-analyse" : "Analyse Competitors"}
                      </button>

                      {competitorMutation.isError && (
                        <div className="error-box">Analysis failed. Please try again.</div>
                      )}

                      {compData?.insights?.map((c, i) => (
                        <CompetitorCard key={i} c={c} rank={i + 1} />
                      ))}

                      {compData && compData.insights.length === 0 && (
                        <div style={{ textAlign: "center", padding: "32px", color: "#475569" }}>
                          No competitor data available for this tender.
                        </div>
                      )}
                    </div>
                  )}

                  {/* ── Market Price Tab ── */}
                  {activeTab === "market" && (
                    <div>
                      <div className="market-cat-row">
                        <input
                          className="market-cat-input"
                          placeholder="Enter category (e.g. civil works, IT equipment)"
                          value={category}
                          onChange={(e) => setCategory(e.target.value)}
                        />
                        <button
                          className="run-btn"
                          disabled={!category || marketLoading}
                          onClick={() => fetchMarket()}
                        >
                          {marketLoading ? <><span className="spinner" />Fetching…</> : "Get Price"}
                        </button>
                      </div>

                      {marketData && (
                        <>
                          <div className="market-grid">
                            <div className="market-card">
                              <div className="market-card-val">{fmt(marketData.avg_price)}</div>
                              <div className="market-card-label">Average Price</div>
                            </div>
                            <div className="market-card">
                              <div className="market-card-val" style={{ color: "#10B981" }}>
                                {fmt(marketData.min_price)}
                              </div>
                              <div className="market-card-label">Minimum (L1)</div>
                            </div>
                            <div className="market-card">
                              <div className="market-card-val" style={{ color: "#EF4444" }}>
                                {fmt(marketData.max_price)}
                              </div>
                              <div className="market-card-label">Maximum</div>
                            </div>
                            <div className="market-card">
                              <div className="market-card-val" style={{ color: "#F59E0B" }}>
                                {marketData.sample_count}
                              </div>
                              <div className="market-card-label">Tenders Sampled</div>
                            </div>
                          </div>

                          <div className="market-bar-section">
                            <div className="market-bar-title">Price Range Distribution</div>
                            <div className="market-bar-track">
                              <div
                                className="market-bar-fill"
                                style={{
                                  width: `${((marketData.avg_price - marketData.min_price) / (marketData.max_price - marketData.min_price)) * 100}%`,
                                }}
                              />
                            </div>
                            <div className="market-bar-labels">
                              <span>{fmt(marketData.min_price)}</span>
                              <span>Avg: {fmt(marketData.avg_price)}</span>
                              <span>{fmt(marketData.max_price)}</span>
                            </div>
                            <div className="market-sample">
                              Based on {marketData.sample_count} tenders ·
                              Last updated {new Date(marketData.last_refreshed).toLocaleDateString("en-IN")}
                            </div>
                          </div>
                        </>
                      )}
                    </div>
                  )}

                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
