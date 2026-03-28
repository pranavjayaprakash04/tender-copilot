"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface TenderDetail {
  id: string;
  tender_id: string;
  title: string;
  procuring_entity: string;
  state: string | null;
  category: string | null;
  estimated_value: number | null;
  bid_submission_deadline: string | null;
  published_date: string | null;
  description: string | null;
  source_url: string | null;
  status: string | null;
  emd_amount: number | null;
  processing_fee: number | null;
}

interface WinProbabilityResponse {
  tender_id: string;
  win_probability: number;
  confidence: string;
  factors: string[];
  market_avg: number | null;
  recommended_range: { min: number; max: number } | null;
}

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

interface MarketPriceResponse {
  category: string;
  avg_price: number;
  min_price: number;
  max_price: number;
  sample_count: number;
  last_refreshed: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const fmt = (n: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);

const pct = (n: number) => `${(n * 100).toFixed(1)}%`;

const winColor = (p: number) => p >= 0.7 ? "#10B981" : p >= 0.4 ? "#F59E0B" : "#EF4444";

// ─── Win Probability Ring ─────────────────────────────────────────────────────

function WinRing({ probability }: { probability: number }) {
  const r = 44;
  const circ = 2 * Math.PI * r;
  const dash = circ * probability;
  const color = winColor(probability);
  return (
    <svg width="110" height="110" viewBox="0 0 110 110">
      <circle cx="55" cy="55" r={r} fill="none" stroke="#E5E7EB" strokeWidth="10" />
      <circle cx="55" cy="55" r={r} fill="none" stroke={color} strokeWidth="10"
        strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
        transform="rotate(-90 55 55)" style={{ transition: "stroke-dasharray 1s ease" }} />
      <text x="55" y="51" textAnchor="middle" fill={color} fontSize="18" fontWeight="700" fontFamily="sans-serif">
        {(probability * 100).toFixed(0)}%
      </text>
      <text x="55" y="66" textAnchor="middle" fill="#6B7280" fontSize="10" fontFamily="sans-serif">
        Win Chance
      </text>
    </svg>
  );
}

// ─── Intelligence Panel ───────────────────────────────────────────────────────

function IntelligencePanel({ tender }: { tender: TenderDetail }) {
  const [activeTab, setActiveTab] = useState<"winprob" | "competitors" | "market">("winprob");
  const [bidAmount, setBidAmount] = useState("");
  const [openComp, setOpenComp] = useState<number | null>(null);

  const tenderId = tender.tender_id || tender.id;

  const winProbMutation = useMutation<WinProbabilityResponse, Error>({
    mutationFn: () =>
      api.post("/api/v1/intelligence/bid/win-probability", {
        tender_id: tenderId,
        company_id: "current",
        our_bid_amount: bidAmount ? parseFloat(bidAmount) : null,
      }),
  });

  const competitorMutation = useMutation<CompetitorAnalysisResponse, Error>({
    mutationFn: () =>
      api.post("/api/v1/intelligence/bid/analyze-competitors", {
        tender_id: tenderId,
        company_id: "current",
        lang: "en",
      }),
  });

  const category = tender.category || "";
  const { data: marketData, isLoading: marketLoading, refetch: fetchMarket } = useQuery<MarketPriceResponse>({
    queryKey: ["market-price", category],
    queryFn: () => api.get(`/api/v1/intelligence/bid/market-price/${encodeURIComponent(category)}`),
    enabled: false,
  });

  const winProb = winProbMutation.data;
  const compData = competitorMutation.data;

  return (
    <>
      <style>{`
        .intel-wrap{background:#0F1117;border-radius:12px;overflow:hidden;margin-top:24px;border:1px solid #1E2537}
        .intel-top{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid #1E2537}
        .intel-title{font-size:15px;font-weight:700;color:#F1F5F9;display:flex;align-items:center;gap:8px}
        .intel-badge{background:#3B82F620;color:#3B82F6;font-size:10px;font-weight:600;padding:2px 8px;border-radius:20px;text-transform:uppercase;letter-spacing:.5px}
        .i-tabs{display:flex;border-bottom:1px solid #1E2537}
        .i-tab{flex:1;padding:12px 8px;text-align:center;font-size:12px;font-weight:500;color:#475569;cursor:pointer;transition:all .15s;border-bottom:2px solid transparent}
        .i-tab:hover{color:#94A3B8;background:#1A1F2E}
        .i-tab--active{color:#3B82F6;border-bottom-color:#3B82F6;background:#1A2540}
        .i-body{padding:20px}
        .i-row{display:flex;gap:10px;align-items:flex-end;margin-bottom:16px}
        .i-input{flex:1;padding:9px 12px;background:#1A1F2E;border:1px solid #1E2537;border-radius:8px;color:#E2E8F0;font-size:13px;outline:none}
        .i-input:focus{border-color:#3B82F6}
        .i-btn{padding:9px 18px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;border:none;background:#3B82F6;color:#fff;white-space:nowrap;transition:opacity .15s}
        .i-btn:hover{opacity:.85}
        .i-btn:disabled{opacity:.4;cursor:not-allowed}
        .i-btn--outline{background:transparent;border:1px solid #1E2537;color:#94A3B8}
        .i-btn--outline:hover{border-color:#3B82F6;color:#3B82F6;opacity:1}
        .i-win-top{display:flex;gap:20px;align-items:center;margin-bottom:16px;flex-wrap:wrap}
        .i-win-meta{flex:1;min-width:160px}
        .i-conf{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;margin-bottom:10px}
        .i-range{background:#1A1F2E;border-radius:8px;padding:14px;margin-bottom:12px}
        .i-range-title{font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
        .i-range-row{display:flex;justify-content:space-between;align-items:center}
        .i-range-val{font-size:16px;font-weight:700;color:#F1F5F9;font-family:monospace}
        .i-range-label{font-size:10px;color:#64748B}
        .i-factors{background:#1A1F2E;border-radius:8px;padding:14px}
        .i-factors-title{font-size:11px;font-weight:600;color:#94A3B8;margin-bottom:10px}
        .i-factor{display:flex;align-items:flex-start;gap:6px;margin-bottom:6px;font-size:12px;color:#CBD5E1}
        .i-factor-dot{width:5px;height:5px;border-radius:50%;background:#3B82F6;flex-shrink:0;margin-top:4px}
        .i-avg{font-size:11px;color:#64748B;margin-top:4px}
        .comp-banner{background:linear-gradient(135deg,#1E3A5F,#1A2540);border:1px solid #3B82F640;border-radius:8px;padding:14px 18px;margin-bottom:14px;display:flex;align-items:center;justify-content:space-between}
        .comp-banner-label{font-size:12px;color:#94A3B8}
        .comp-banner-val{font-size:24px;font-weight:700;font-family:monospace}
        .comp-card{background:#1A1F2E;border:1px solid #1E2537;border-radius:8px;margin-bottom:8px;overflow:hidden}
        .comp-head{display:flex;align-items:center;gap:10px;padding:12px 14px;cursor:pointer}
        .comp-rank{font-size:16px;font-weight:700;width:22px;text-align:center;font-family:monospace}
        .comp-info{flex:1;min-width:0}
        .comp-name{display:block;font-size:13px;font-weight:600;color:#E2E8F0}
        .comp-bid{display:block;font-size:11px;color:#64748B;font-family:monospace;margin-top:1px}
        .comp-pct{font-size:14px;font-weight:700;font-family:monospace;flex-shrink:0}
        .comp-bar-wrap{width:60px;height:3px;background:#1E2537;border-radius:2px;flex-shrink:0}
        .comp-bar{height:3px;border-radius:2px}
        .comp-toggle{background:none;border:none;color:#475569;cursor:pointer;font-size:11px}
        .comp-detail{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:0 14px 14px;border-top:1px solid #1E2537;padding-top:12px}
        .comp-col-title{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
        .comp-item{display:flex;align-items:flex-start;gap:5px;font-size:11px;color:#94A3B8;margin-bottom:4px;line-height:1.4}
        .comp-dot{width:4px;height:4px;border-radius:50%;flex-shrink:0;margin-top:4px}
        .mkt-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px}
        .mkt-card{background:#1A1F2E;border:1px solid #1E2537;border-radius:8px;padding:14px;text-align:center}
        .mkt-val{font-size:18px;font-weight:700;color:#F1F5F9;font-family:monospace;margin-bottom:3px}
        .mkt-label{font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:.5px}
        .mkt-bar-section{background:#1A1F2E;border:1px solid #1E2537;border-radius:8px;padding:14px}
        .mkt-bar-title{font-size:11px;color:#64748B;margin-bottom:10px}
        .mkt-bar-track{height:6px;background:#1E2537;border-radius:3px;margin-bottom:6px}
        .mkt-bar-fill{height:6px;border-radius:3px;background:linear-gradient(90deg,#3B82F6,#10B981)}
        .mkt-bar-labels{display:flex;justify-content:space-between;font-size:10px;color:#475569;font-family:monospace}
        .mkt-sample{font-size:11px;color:#475569;margin-top:8px}
        .i-error{background:#EF444420;border:1px solid #EF444440;border-radius:6px;padding:10px 14px;color:#FCA5A5;font-size:12px;margin-top:10px}
        .i-spinner{width:14px;height:14px;border:2px solid #1E2537;border-top-color:#3B82F6;border-radius:50%;animation:ispin .7s linear infinite;display:inline-block;vertical-align:middle;margin-right:6px}
        @keyframes ispin{to{transform:rotate(360deg)}}
        .i-empty{text-align:center;padding:32px;color:#475569;font-size:13px}
      `}</style>

      <div className="intel-wrap">
        <div className="intel-top">
          <div className="intel-title">
            🎯 Bid Intelligence
            <span className="intel-badge">AI Powered</span>
          </div>
        </div>

        <div className="i-tabs">
          {([
            { key: "winprob", label: "Win Probability" },
            { key: "competitors", label: "Competitors" },
            { key: "market", label: "Market Price" },
          ] as const).map((t) => (
            <div
              key={t.key}
              className={`i-tab${activeTab === t.key ? " i-tab--active" : ""}`}
              onClick={() => setActiveTab(t.key)}
            >
              {t.label}
            </div>
          ))}
        </div>

        <div className="i-body">

          {/* ── Win Probability ── */}
          {activeTab === "winprob" && (
            <div>
              <div className="i-row">
                <input
                  className="i-input"
                  type="number"
                  placeholder="Your bid amount in ₹ (optional)"
                  value={bidAmount}
                  onChange={(e) => setBidAmount(e.target.value)}
                />
                <button
                  className="i-btn"
                  disabled={winProbMutation.isPending}
                  onClick={() => winProbMutation.mutate()}
                >
                  {winProbMutation.isPending ? <><span className="i-spinner" />Analysing…</> : "Analyse"}
                </button>
              </div>

              {winProbMutation.isError && (
                <div className="i-error">Analysis failed. Please try again.</div>
              )}

              {!winProb && !winProbMutation.isPending && (
                <div className="i-empty">Enter your bid amount and click Analyse to get your win probability</div>
              )}

              {winProb && (
                <>
                  <div className="i-win-top">
                    <WinRing probability={winProb.win_probability} />
                    <div className="i-win-meta">
                      <span className="i-conf" style={{
                        background: winColor(winProb.win_probability) + "22",
                        color: winColor(winProb.win_probability),
                      }}>
                        {winProb.confidence?.toUpperCase()} CONFIDENCE
                      </span>

                      {winProb.recommended_range && (
                        <div className="i-range">
                          <div className="i-range-title">Recommended Bid Range</div>
                          <div className="i-range-row">
                            <div>
                              <div className="i-range-val">{fmt(winProb.recommended_range.min)}</div>
                              <div className="i-range-label">Min</div>
                            </div>
                            <div style={{ color: "#1E2537" }}>→</div>
                            <div>
                              <div className="i-range-val">{fmt(winProb.recommended_range.max)}</div>
                              <div className="i-range-label">Max</div>
                            </div>
                          </div>
                        </div>
                      )}

                      {winProb.market_avg && (
                        <div className="i-avg">Market average: {fmt(winProb.market_avg)}</div>
                      )}
                    </div>
                  </div>

                  {winProb.factors?.length > 0 && (
                    <div className="i-factors">
                      <div className="i-factors-title">Key Factors</div>
                      {winProb.factors.map((f, i) => (
                        <div key={i} className="i-factor">
                          <span className="i-factor-dot" />
                          {f}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* ── Competitors ── */}
          {activeTab === "competitors" && (
            <div>
              {compData && (
                <div className="comp-banner">
                  <div>
                    <div className="comp-banner-label">Our Win Probability</div>
                    {compData.recommended_price && (
                      <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>
                        Recommended: {fmt(compData.recommended_price)}
                      </div>
                    )}
                  </div>
                  <div className="comp-banner-val" style={{ color: winColor(compData.our_win_probability) }}>
                    {pct(compData.our_win_probability)}
                  </div>
                </div>
              )}

              <button
                className={`i-btn${compData ? " i-btn--outline" : ""}`}
                disabled={competitorMutation.isPending}
                onClick={() => competitorMutation.mutate()}
                style={{ marginBottom: 14 }}
              >
                {competitorMutation.isPending
                  ? <><span className="i-spinner" />Analysing…</>
                  : compData ? "Re-analyse" : "Analyse Competitors"}
              </button>

              {competitorMutation.isError && (
                <div className="i-error">Analysis failed. Please try again.</div>
              )}

              {!compData && !competitorMutation.isPending && (
                <div className="i-empty">Click Analyse Competitors to see who you're up against</div>
              )}

              {compData?.insights?.map((c, i) => (
                <div key={i} className="comp-card">
                  <div className="comp-head" onClick={() => setOpenComp(openComp === i ? null : i)}>
                    <div className="comp-rank" style={{ color: winColor(c.win_probability) }}>{i + 1}</div>
                    <div className="comp-info">
                      <span className="comp-name">{c.competitor_name}</span>
                      {c.estimated_bid && <span className="comp-bid">{fmt(c.estimated_bid)}</span>}
                    </div>
                    <div className="comp-pct" style={{ color: winColor(c.win_probability) }}>{pct(c.win_probability)}</div>
                    <div className="comp-bar-wrap">
                      <div className="comp-bar" style={{ width: pct(c.win_probability), background: winColor(c.win_probability) }} />
                    </div>
                    <button className="comp-toggle">{openComp === i ? "▲" : "▼"}</button>
                  </div>
                  {openComp === i && (
                    <div className="comp-detail">
                      <div>
                        <div className="comp-col-title" style={{ color: "#10B981" }}>Strengths</div>
                        {c.strengths.map((s, j) => (
                          <div key={j} className="comp-item">
                            <span className="comp-dot" style={{ background: "#10B981" }} />{s}
                          </div>
                        ))}
                      </div>
                      <div>
                        <div className="comp-col-title" style={{ color: "#EF4444" }}>Weaknesses</div>
                        {c.weaknesses.map((w, j) => (
                          <div key={j} className="comp-item">
                            <span className="comp-dot" style={{ background: "#EF4444" }} />{w}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* ── Market Price ── */}
          {activeTab === "market" && (
            <div>
              <div className="i-row">
                <div style={{ flex: 1, fontSize: 12, color: "#64748B" }}>
                  Category: <strong style={{ color: "#E2E8F0" }}>{tender.category || "Not specified"}</strong>
                </div>
                <button
                  className="i-btn"
                  disabled={!category || marketLoading}
                  onClick={() => fetchMarket()}
                >
                  {marketLoading ? <><span className="i-spinner" />Fetching…</> : "Get Price Data"}
                </button>
              </div>

              {!marketData && !marketLoading && (
                <div className="i-empty">Click Get Price Data to see market pricing for {tender.category || "this category"}</div>
              )}

              {marketData && (
                <>
                  <div className="mkt-grid">
                    <div className="mkt-card">
                      <div className="mkt-val">{fmt(marketData.avg_price)}</div>
                      <div className="mkt-label">Average Price</div>
                    </div>
                    <div className="mkt-card">
                      <div className="mkt-val" style={{ color: "#10B981" }}>{fmt(marketData.min_price)}</div>
                      <div className="mkt-label">Minimum (L1)</div>
                    </div>
                    <div className="mkt-card">
                      <div className="mkt-val" style={{ color: "#EF4444" }}>{fmt(marketData.max_price)}</div>
                      <div className="mkt-label">Maximum</div>
                    </div>
                    <div className="mkt-card">
                      <div className="mkt-val" style={{ color: "#F59E0B" }}>{marketData.sample_count}</div>
                      <div className="mkt-label">Tenders Sampled</div>
                    </div>
                  </div>
                  <div className="mkt-bar-section">
                    <div className="mkt-bar-title">Price Range Distribution</div>
                    <div className="mkt-bar-track">
                      <div className="mkt-bar-fill" style={{
                        width: `${((marketData.avg_price - marketData.min_price) / (marketData.max_price - marketData.min_price)) * 100}%`
                      }} />
                    </div>
                    <div className="mkt-bar-labels">
                      <span>{fmt(marketData.min_price)}</span>
                      <span>Avg: {fmt(marketData.avg_price)}</span>
                      <span>{fmt(marketData.max_price)}</span>
                    </div>
                    <div className="mkt-sample">
                      Based on {marketData.sample_count} tenders · Last updated {new Date(marketData.last_refreshed).toLocaleDateString("en-IN")}
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function TenderDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [showIntel, setShowIntel] = useState(false);

  const { data: rawData, isLoading, error, refetch } = useQuery({
    queryKey: ["tender", params.id],
    queryFn: () => api.tenders.get(params.id),
    staleTime: 60_000,
  });

  const tender: TenderDetail | null = rawData
    ? ((rawData as any).data ?? rawData) as TenderDetail
    : null;

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return "—";
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" });
  };

  const formatCurrency = (value: number | null | undefined) => {
    if (value === null || value === undefined) return "—";
    return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value);
  };

  const getDeadlineColor = (deadline: string | null | undefined) => {
    if (!deadline) return "text-gray-600";
    const d = new Date(deadline);
    if (isNaN(d.getTime())) return "text-gray-600";
    const days = Math.ceil((d.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
    if (days <= 3) return "text-red-600";
    if (days <= 7) return "text-orange-600";
    return "text-green-600";
  };

  const getDaysLeft = (deadline: string | null | undefined) => {
    if (!deadline) return null;
    const d = new Date(deadline);
    if (isNaN(d.getTime())) return null;
    const days = Math.ceil((d.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
    if (days < 0) return "Closed";
    if (days === 0) return "Due today";
    return `${days} days left`;
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-600">Loading tender...</p>
      </div>
    );
  }

  if (error || !tender) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">Failed to load tender</p>
          <Button onClick={() => refetch()}>Retry</Button>
          <button
            onClick={() => router.back()}
            className="ml-2 px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">

        {/* Back */}
        <button
          onClick={() => router.back()}
          className="text-sm text-gray-500 hover:text-gray-700 mb-6 flex items-center gap-1"
        >
          ← Back
        </button>

        {/* Header card */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex flex-col lg:flex-row lg:justify-between lg:items-start gap-4">
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-gray-900 mb-2">{tender.title}</h1>
              <p className="text-gray-600 text-lg mb-1">{tender.procuring_entity}</p>
              {tender.state && <p className="text-gray-500 text-sm">📍 {tender.state}</p>}
            </div>
            <div className="shrink-0 text-right">
              <p className="text-2xl font-bold text-gray-900">{formatCurrency(tender.estimated_value)}</p>
              {tender.bid_submission_deadline && (
                <p className={cn("text-sm font-medium mt-1", getDeadlineColor(tender.bid_submission_deadline))}>
                  {getDaysLeft(tender.bid_submission_deadline)}
                </p>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-2 mt-4">
            {tender.category && (
              <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium capitalize">
                {tender.category.replace('_', ' ')}
              </span>
            )}
            {tender.status && (
              <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm font-medium capitalize">
                {tender.status.replace('_', ' ')}
              </span>
            )}
          </div>
        </div>

        {/* Key details */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Key Details</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Posted</p>
              <p className="font-medium text-gray-900">{formatDate(tender.published_date)}</p>
            </div>
            <div>
              <p className="text-gray-500">Deadline</p>
              <p className={cn("font-medium", getDeadlineColor(tender.bid_submission_deadline))}>
                {formatDate(tender.bid_submission_deadline)}
              </p>
            </div>
            <div>
              <p className="text-gray-500">Estimated Value</p>
              <p className="font-medium text-gray-900">{formatCurrency(tender.estimated_value)}</p>
            </div>
            <div>
              <p className="text-gray-500">EMD Amount</p>
              <p className="font-medium text-gray-900">{formatCurrency(tender.emd_amount)}</p>
            </div>
            <div>
              <p className="text-gray-500">Document Fee</p>
              <p className="font-medium text-gray-900">{formatCurrency(tender.processing_fee)}</p>
            </div>
            <div>
              <p className="text-gray-500">Tender ID</p>
              <p className="font-medium text-gray-900 text-xs break-all">{tender.tender_id || tender.id}</p>
            </div>
          </div>
        </div>

        {/* Description */}
        {tender.description && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Description</h2>
            <p className="text-gray-700 leading-relaxed whitespace-pre-line">{tender.description}</p>
          </div>
        )}

        {/* Actions */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex flex-col sm:flex-row gap-3">
            {tender.source_url && (
              <a
                href={tender.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 transition-colors"
              >
                View on Source Site ↗
              </a>
            )}
            <button
              onClick={() => setShowIntel(!showIntel)}
              className="inline-flex items-center justify-center px-4 py-2 bg-gray-900 text-white rounded-md text-sm font-medium hover:bg-gray-800 transition-colors"
            >
              {showIntel ? "Hide Intelligence" : "🎯 Run Bid Intelligence"}
            </button>
            <Button variant="outline" onClick={() => router.back()}>
              Back to Tenders
            </Button>
          </div>
        </div>

        {/* Intelligence Panel — shown inline when button clicked */}
        {showIntel && <IntelligencePanel tender={tender} />}

      </div>
    </div>
  );
}
