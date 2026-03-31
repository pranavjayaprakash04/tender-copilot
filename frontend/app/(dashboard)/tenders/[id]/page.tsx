"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
  source: string | null;
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
  recommended_range: { min: number; max: number; optimal?: number } | null;
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

interface EligibilityCriteria {
  name: string;
  status: "pass" | "fail" | "warning";
  detail: string;
}

interface EligibilityResponse {
  eligible: boolean;
  score: number;
  verdict: string;
  criteria: EligibilityCriteria[];
  missing_documents: string[];
  recommendations: string[];
  summary: string;
}

interface ChecklistItem {
  id: string;
  name: string;
  description: string;
  required: boolean;
  status: "have" | "missing" | "unknown";
  in_vault: boolean;
  notes?: string | null;
}

interface DocumentChecklistResponse {
  tender_id: string;
  checklist: ChecklistItem[];
  total: number;
  have_count: number;
  missing_count: number;
  readiness_score: number;
  summary: string;
}

interface PriceBand {
  label: string;
  min: number;
  max: number;
  win_rate_estimate: number;
  description: string;
}

interface PriceTrendPoint {
  label: string;
  avg: number;
  min: number;
  max: number;
}

interface PriceIntelligenceResponse {
  tender_id: string;
  category: string | null;
  market_avg: number | null;
  market_min: number | null;
  market_max: number | null;
  sample_count: number;
  price_to_win_score: number;
  price_to_win_label: string;
  optimal_price: number | null;
  our_bid_amount: number | null;
  our_position_pct: number | null;
  bands: PriceBand[];
  trend: PriceTrendPoint[];
  insights: string[];
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const fmt = (n: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);

const fmtShort = (n: number) => {
  if (n >= 1_00_00_000) return `₹${(n / 1_00_00_000).toFixed(1)}Cr`;
  if (n >= 1_00_000) return `₹${(n / 1_00_000).toFixed(1)}L`;
  return fmt(n);
};

const pct = (n: number) => `${(n * 100).toFixed(1)}%`;
const winColor = (p: number) => p >= 0.7 ? "#10B981" : p >= 0.4 ? "#F59E0B" : "#EF4444";

// ─── Modal Shell ──────────────────────────────────────────────────────────────

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-2xl shadow-2xl"
        style={{ background: "#0F1117", border: "1px solid #1E2537" }}
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#1E2537]">
          <h2 className="text-base font-semibold text-white">{title}</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 text-xl leading-none">✕</button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

// ─── Track Bid Modal ──────────────────────────────────────────────────────────

function TrackBidModal({ tender, companyId, onClose }: { tender: TenderDetail; companyId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    bid_amount: tender.estimated_value ? String(Math.round(tender.estimated_value * 0.95)) : "",
    emd_amount: tender.emd_amount ? String(tender.emd_amount) : "",
    notes: "",
  });

  const mutation = useMutation({
    mutationFn: () => {
      const now = new Date();
      const bidNumber = `BID-${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, "0")}${String(now.getDate()).padStart(2, "0")}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;
      return api.bids.create({
        tender_id: parseInt(tender.id),
        title: tender.title,
        bid_amount: parseFloat(form.bid_amount),
        emd_amount: form.emd_amount ? parseFloat(form.emd_amount) : undefined,
        submission_deadline: tender.bid_submission_deadline
          ? new Date(tender.bid_submission_deadline).toISOString()
          : new Date(Date.now() + 7 * 86400000).toISOString(),
        company_id: companyId,
        bid_number: bidNumber,
        notes: form.notes || undefined,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bids"] });
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden"
        onClick={e => e.stopPropagation()}>
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-white font-semibold text-lg">Track this Bid</h2>
              <p className="text-blue-100 text-sm mt-0.5 line-clamp-1">{tender.title}</p>
            </div>
            <button onClick={onClose} className="text-white/70 hover:text-white text-xl leading-none">✕</button>
          </div>
        </div>
        <div className="px-6 py-5 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Your Bid Amount (₹) <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              value={form.bid_amount}
              onChange={e => setForm(f => ({ ...f, bid_amount: e.target.value }))}
              placeholder="Enter your bid amount"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {tender.estimated_value && (
              <p className="text-xs text-gray-400 mt-1">Estimated value: {fmt(tender.estimated_value)}</p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">EMD Amount (₹)</label>
            <input
              type="number"
              value={form.emd_amount}
              onChange={e => setForm(f => ({ ...f, emd_amount: e.target.value }))}
              placeholder="Earnest money deposit"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
            <textarea
              value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              placeholder="Add any notes about this bid..."
              rows={3}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>
          {mutation.isError && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-3 py-2">
              {(mutation.error as Error).message}
            </div>
          )}
          {mutation.isSuccess && (
            <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg px-3 py-2">
              ✓ Bid tracked! View it in your <a href="/bids" className="underline font-medium">Bid Pipeline</a>.
            </div>
          )}
        </div>
        <div className="px-6 pb-5 flex gap-3">
          <button onClick={onClose}
            className="flex-1 border border-gray-200 text-gray-600 rounded-lg py-2.5 text-sm font-medium hover:bg-gray-50 transition-colors">
            Cancel
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={!form.bid_amount || mutation.isPending || mutation.isSuccess}
            className="flex-1 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg py-2.5 text-sm font-medium hover:from-blue-700 hover:to-indigo-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {mutation.isPending ? "Tracking..." : mutation.isSuccess ? "Tracked ✓" : "Start Tracking →"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Win Probability Ring ─────────────────────────────────────────────────────

function WinRing({ probability }: { probability: number }) {
  const r = 44;
  const circ = 2 * Math.PI * r;
  const dash = circ * probability;
  const color = winColor(probability);
  return (
    <svg width="110" height="110" viewBox="0 0 110 110">
      <circle cx="55" cy="55" r={r} fill="none" stroke="#1E2537" strokeWidth="10" />
      <circle cx="55" cy="55" r={r} fill="none" stroke={color} strokeWidth="10"
        strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
        transform="rotate(-90 55 55)" style={{ transition: "stroke-dasharray 1s ease" }} />
      <text x="55" y="51" textAnchor="middle" fill={color} fontSize="18" fontWeight="700" fontFamily="sans-serif">
        {(probability * 100).toFixed(0)}%
      </text>
      <text x="55" y="66" textAnchor="middle" fill="#6B7280" fontSize="10" fontFamily="sans-serif">Win Chance</text>
    </svg>
  );
}

// ─── Win Probability Modal ────────────────────────────────────────────────────

function WinProbabilityModal({ tender, companyId, onClose }: { tender: TenderDetail; companyId: string; onClose: () => void }) {
  const [bidAmount, setBidAmount] = useState("");

  const mutation = useMutation<WinProbabilityResponse, Error>({
    mutationFn: () =>
      api.post("/api/v1/intelligence/bid/win-probability", {
        tender_id: tender.id,
        company_id: companyId,
        our_bid_amount: bidAmount ? parseFloat(bidAmount) : null,
      }),
  });

  const data = mutation.data;

  return (
    <Modal title="🎯 Win Probability" onClose={onClose}>
      <style>{`
        .i-input{width:100%;padding:9px 12px;background:#1A1F2E;border:1px solid #1E2537;border-radius:8px;color:#E2E8F0;font-size:13px;outline:none;margin-bottom:12px}
        .i-input:focus{border-color:#3B82F6}
        .i-btn{padding:10px 20px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;border:none;background:#3B82F6;color:#fff;transition:opacity .15s}
        .i-btn:hover{opacity:.85}
        .i-btn:disabled{opacity:.4;cursor:not-allowed}
        .i-spinner{width:13px;height:13px;border:2px solid #1E2537;border-top-color:#3B82F6;border-radius:50%;animation:ispin .7s linear infinite;display:inline-block;vertical-align:middle;margin-right:6px}
        @keyframes ispin{to{transform:rotate(360deg)}}
        .i-range{background:#1A1F2E;border-radius:8px;padding:14px;margin-top:14px}
        .i-factors{background:#1A1F2E;border-radius:8px;padding:14px;margin-top:12px}
      `}</style>

      <input className="i-input" type="number" placeholder="Your bid amount in ₹ (optional)"
        value={bidAmount} onChange={e => setBidAmount(e.target.value)} />
      <button className="i-btn" disabled={mutation.isPending} onClick={() => mutation.mutate()}>
        {mutation.isPending ? <><span className="i-spinner" />Analysing…</> : "Analyse"}
      </button>

      {mutation.isError && (
        <div style={{ background: "#EF444420", border: "1px solid #EF444440", borderRadius: 6, padding: "10px 14px", color: "#FCA5A5", fontSize: 12, marginTop: 12 }}>
          Analysis failed. Please try again.
        </div>
      )}

      {!data && !mutation.isPending && (
        <p style={{ color: "#475569", fontSize: 13, textAlign: "center", marginTop: 24 }}>
          Enter your bid amount and click Analyse
        </p>
      )}

      {data && (
        <>
          <div style={{ display: "flex", gap: 20, alignItems: "center", marginTop: 16, flexWrap: "wrap" }}>
            <WinRing probability={data.win_probability} />
            <div style={{ flex: 1 }}>
              <span style={{
                display: "inline-block", padding: "3px 10px", borderRadius: 20, fontSize: 11, fontWeight: 600,
                background: winColor(data.win_probability) + "22", color: winColor(data.win_probability), marginBottom: 10
              }}>
                {data.confidence?.toUpperCase()} CONFIDENCE
              </span>
              {data.market_avg && (
                <p style={{ fontSize: 11, color: "#64748B", marginTop: 4 }}>Market average: {fmt(data.market_avg)}</p>
              )}
            </div>
          </div>
          {data.recommended_range && (
            <div className="i-range">
              <div style={{ fontSize: 10, color: "#475569", textTransform: "uppercase", letterSpacing: ".5px", marginBottom: 8 }}>Recommended Bid Range</div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: "#F1F5F9", fontFamily: "monospace" }}>{fmt(data.recommended_range.min)}</div>
                  <div style={{ fontSize: 10, color: "#64748B" }}>Min</div>
                </div>
                <div style={{ color: "#1E2537" }}>→</div>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: "#F1F5F9", fontFamily: "monospace" }}>{fmt(data.recommended_range.max)}</div>
                  <div style={{ fontSize: 10, color: "#64748B" }}>Max</div>
                </div>
              </div>
            </div>
          )}
          {data.factors?.length > 0 && (
            <div className="i-factors">
              <div style={{ fontSize: 11, fontWeight: 600, color: "#94A3B8", marginBottom: 10 }}>Key Factors</div>
              {data.factors.map((f, i) => (
                <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 6, marginBottom: 6, fontSize: 12, color: "#CBD5E1" }}>
                  <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#3B82F6", flexShrink: 0, marginTop: 4, display: "inline-block" }} />
                  {f}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </Modal>
  );
}

// ─── Competitors Modal ────────────────────────────────────────────────────────

function CompetitorsModal({ tender, companyId, onClose }: { tender: TenderDetail; companyId: string; onClose: () => void }) {
  const [openComp, setOpenComp] = useState<number | null>(null);

  const mutation = useMutation<CompetitorAnalysisResponse, Error>({
    mutationFn: async () => {
      const res = await fetch("/api/competitors", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tender_id: tender.id,
          company_id: companyId,
          title: tender.title,
          category: tender.category,
          estimated_value: tender.estimated_value,
          location: tender.state,
          portal: tender.source ?? "cppp",
        }),
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      return {
        tender_id: tender.id,
        company_id: companyId,
        insights: data.competitors ?? [],
        our_win_probability: data.our_win_probability ?? 0.72,
        recommended_price: data.recommended_price ?? null,
        analysis_lang: "en",
        generated_at: new Date().toISOString(),
      };
    },
  });

  const data = mutation.data;

  return (
    <Modal title="🏆 Competitor Analysis" onClose={onClose}>
      <style>{`
        .i-btn{padding:10px 20px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;border:none;background:#3B82F6;color:#fff;transition:opacity .15s}
        .i-btn:hover{opacity:.85}
        .i-btn:disabled{opacity:.4;cursor:not-allowed}
        .i-btn--outline{background:transparent;border:1px solid #1E2537;color:#94A3B8}
        .i-btn--outline:hover{border-color:#3B82F6;color:#3B82F6;opacity:1}
        .i-spinner{width:13px;height:13px;border:2px solid #1E2537;border-top-color:#3B82F6;border-radius:50%;animation:ispin .7s linear infinite;display:inline-block;vertical-align:middle;margin-right:6px}
        @keyframes ispin{to{transform:rotate(360deg)}}
        .comp-card{background:#1A1F2E;border:1px solid #1E2537;border-radius:8px;margin-bottom:8px;overflow:hidden}
        .comp-head{display:flex;align-items:center;gap:10px;padding:12px 14px;cursor:pointer}
        .comp-detail{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:12px 14px;border-top:1px solid #1E2537}
      `}</style>

      {data && (
        <div style={{ background: "linear-gradient(135deg,#1E3A5F,#1A2540)", border: "1px solid #3B82F640", borderRadius: 8, padding: "14px 18px", marginBottom: 14, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ fontSize: 12, color: "#94A3B8" }}>
            Our Win Probability
            {data.recommended_price && <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>Recommended: {fmt(data.recommended_price)}</div>}
          </div>
          <div style={{ fontSize: 24, fontWeight: 700, fontFamily: "monospace", color: winColor(data.our_win_probability) }}>
            {pct(data.our_win_probability)}
          </div>
        </div>
      )}

      <button
        className={`i-btn${data ? " i-btn--outline" : ""}`}
        disabled={mutation.isPending}
        onClick={() => mutation.mutate()}
        style={{ marginBottom: 14 }}
      >
        {mutation.isPending ? <><span className="i-spinner" />Analysing…</> : data ? "Re-analyse" : "Analyse Competitors"}
      </button>

      {mutation.isError && (
        <div style={{ background: "#EF444420", border: "1px solid #EF444440", borderRadius: 6, padding: "10px 14px", color: "#FCA5A5", fontSize: 12, marginBottom: 12 }}>
          Analysis failed. Please try again.
        </div>
      )}

      {!data && !mutation.isPending && (
        <p style={{ color: "#475569", fontSize: 13, textAlign: "center", marginTop: 16 }}>
          Click Analyse Competitors to see who you&apos;re up against
        </p>
      )}

      {data?.insights?.map((c, i) => (
        <div key={i} className="comp-card">
          <div className="comp-head" onClick={() => setOpenComp(openComp === i ? null : i)}>
            <div style={{ fontSize: 16, fontWeight: 700, width: 22, textAlign: "center", fontFamily: "monospace", color: winColor(c.win_probability) }}>{i + 1}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <span style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#E2E8F0" }}>{c.competitor_name}</span>
              {c.estimated_bid && <span style={{ display: "block", fontSize: 11, color: "#64748B", fontFamily: "monospace", marginTop: 1 }}>{fmt(c.estimated_bid)}</span>}
            </div>
            <div style={{ fontSize: 14, fontWeight: 700, fontFamily: "monospace", color: winColor(c.win_probability) }}>{pct(c.win_probability)}</div>
            <button style={{ background: "none", border: "none", color: "#475569", cursor: "pointer", fontSize: 11 }}>{openComp === i ? "▲" : "▼"}</button>
          </div>
          {openComp === i && (
            <div className="comp-detail">
              <div>
                <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".5px", marginBottom: 6, color: "#10B981" }}>Strengths</div>
                {c.strengths.map((s, j) => (
                  <div key={j} style={{ display: "flex", alignItems: "flex-start", gap: 5, fontSize: 11, color: "#94A3B8", marginBottom: 4, lineHeight: 1.4 }}>
                    <span style={{ width: 4, height: 4, borderRadius: "50%", background: "#10B981", flexShrink: 0, marginTop: 4, display: "inline-block" }} />{s}
                  </div>
                ))}
              </div>
              <div>
                <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: ".5px", marginBottom: 6, color: "#EF4444" }}>Weaknesses</div>
                {c.weaknesses.map((w, j) => (
                  <div key={j} style={{ display: "flex", alignItems: "flex-start", gap: 5, fontSize: 11, color: "#94A3B8", marginBottom: 4, lineHeight: 1.4 }}>
                    <span style={{ width: 4, height: 4, borderRadius: "50%", background: "#EF4444", flexShrink: 0, marginTop: 4, display: "inline-block" }} />{w}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </Modal>
  );
}

// ─── Market Price Modal ───────────────────────────────────────────────────────

function MarketPriceModal({ tender, onClose }: { tender: TenderDetail; onClose: () => void }) {
  const category = tender.category || "";

  const { data, isLoading, refetch } = useQuery<MarketPriceResponse>({
    queryKey: ["market-price", category],
    queryFn: () => api.get(`/api/v1/intelligence/bid/market-price/${encodeURIComponent(category)}`),
    enabled: false,
  });

  return (
    <Modal title="📊 Market Price Intelligence" onClose={onClose}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
        <div style={{ fontSize: 12, color: "#64748B" }}>
          Category: <strong style={{ color: "#E2E8F0" }}>{tender.category || "Not specified"}</strong>
        </div>
        <button
          onClick={() => refetch()}
          disabled={!category || isLoading}
          style={{ padding: "9px 18px", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer", border: "none", background: "#3B82F6", color: "#fff", opacity: (!category || isLoading) ? 0.4 : 1 }}
        >
          {isLoading ? "Fetching…" : "Get Price Data"}
        </button>
      </div>

      {!data && !isLoading && (
        <p style={{ color: "#475569", fontSize: 13, textAlign: "center", marginTop: 24 }}>
          Click Get Price Data to see market pricing for {tender.category || "this category"}
        </p>
      )}

      {data && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 14 }}>
            {[
              { label: "Average Price", value: fmt(data.avg_price), color: "#F1F5F9" },
              { label: "Minimum (L1)", value: fmt(data.min_price), color: "#10B981" },
              { label: "Maximum", value: fmt(data.max_price), color: "#EF4444" },
              { label: "Tenders Sampled", value: data.sample_count.toString(), color: "#F59E0B" },
            ].map(({ label, value, color }) => (
              <div key={label} style={{ background: "#1A1F2E", border: "1px solid #1E2537", borderRadius: 8, padding: 14, textAlign: "center" }}>
                <div style={{ fontSize: 18, fontWeight: 700, color, fontFamily: "monospace", marginBottom: 3 }}>{value}</div>
                <div style={{ fontSize: 10, color: "#475569", textTransform: "uppercase", letterSpacing: ".5px" }}>{label}</div>
              </div>
            ))}
          </div>
          <div style={{ background: "#1A1F2E", border: "1px solid #1E2537", borderRadius: 8, padding: 14 }}>
            <div style={{ fontSize: 11, color: "#64748B", marginBottom: 10 }}>Price Range Distribution</div>
            <div style={{ height: 6, background: "#1E2537", borderRadius: 3, marginBottom: 6 }}>
              <div style={{
                height: 6, borderRadius: 3, background: "linear-gradient(90deg,#3B82F6,#10B981)",
                width: `${((data.avg_price - data.min_price) / (data.max_price - data.min_price)) * 100}%`
              }} />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "#475569", fontFamily: "monospace" }}>
              <span>{fmt(data.min_price)}</span>
              <span>Avg: {fmt(data.avg_price)}</span>
              <span>{fmt(data.max_price)}</span>
            </div>
            <div style={{ fontSize: 11, color: "#475569", marginTop: 8 }}>
              Based on {data.sample_count} tenders · Last updated {new Date(data.last_refreshed).toLocaleDateString("en-IN")}
            </div>
          </div>
        </>
      )}
    </Modal>
  );
}

// ─── Eligibility Modal ────────────────────────────────────────────────────────

function EligibilityModal({ tender, profile, onClose }: { tender: TenderDetail; profile: any; onClose: () => void }) {
  const mutation = useMutation<EligibilityResponse, Error>({
    mutationFn: async () => {
      const res = await fetch("/api/eligibility", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tender_title: tender.title,
          tender_category: tender.category,
          estimated_value: tender.estimated_value,
          tender_location: tender.state,
          portal: tender.source ?? "cppp",
          requirements: tender.description,
          company_name: profile?.name,
          company_industry: profile?.industry,
          company_location: profile?.location,
          gstin: profile?.gstin,
          udyam_number: profile?.udyam_number,
          turnover_range: profile?.turnover_range,
          capabilities: profile?.capabilities_text,
        }),
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      return res.json();
    },
  });

  const data = mutation.data;
  const verdictColor = (v: string) => {
    if (v?.includes("Highly")) return "#10B981";
    if (v?.includes("Likely")) return "#3B82F6";
    if (v?.includes("Marginally")) return "#F59E0B";
    return "#EF4444";
  };
  const statusIcon = (s: string) => s === "pass" ? "✓" : s === "warning" ? "⚠" : "✗";
  const statusColor = (s: string) => s === "pass" ? "#10B981" : s === "warning" ? "#F59E0B" : "#EF4444";

  return (
    <Modal title="✅ Eligibility Checker" onClose={onClose}>
      {!data && !mutation.isPending && (
        <>
          <p style={{ color: "#94A3B8", fontSize: 13, marginBottom: 16 }}>
            AI will check if <strong style={{ color: "#E2E8F0" }}>{profile?.name || "your company"}</strong> is eligible to bid on this tender based on your profile.
          </p>
          <button onClick={() => mutation.mutate()}
            style={{ padding: "10px 20px", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer", border: "none", background: "#10B981", color: "#fff" }}>
            Check Eligibility
          </button>
        </>
      )}
      {mutation.isPending && (
        <div style={{ textAlign: "center", padding: "32px 0", color: "#64748B", fontSize: 13 }}>
          <div style={{ width: 32, height: 32, border: "3px solid #1E2537", borderTopColor: "#10B981", borderRadius: "50%", animation: "ispin .7s linear infinite", margin: "0 auto 12px" }} />
          Analysing eligibility…
          <style>{`@keyframes ispin{to{transform:rotate(360deg)}}`}</style>
        </div>
      )}
      {mutation.isError && (
        <div style={{ background: "#EF444420", border: "1px solid #EF444440", borderRadius: 6, padding: "10px 14px", color: "#FCA5A5", fontSize: 12, marginBottom: 12 }}>
          Analysis failed. Please try again.
          <button onClick={() => mutation.mutate()} style={{ marginLeft: 8, background: "none", border: "none", color: "#3B82F6", cursor: "pointer", fontSize: 12 }}>Retry</button>
        </div>
      )}
      {data && (
        <>
          <div style={{ background: verdictColor(data.verdict) + "18", border: `1px solid ${verdictColor(data.verdict)}40`, borderRadius: 10, padding: "16px 20px", marginBottom: 16, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div>
              <div style={{ fontSize: 18, fontWeight: 700, color: verdictColor(data.verdict) }}>{data.verdict}</div>
              <div style={{ fontSize: 12, color: "#94A3B8", marginTop: 4, maxWidth: 340 }}>{data.summary}</div>
            </div>
            <div style={{ textAlign: "center", flexShrink: 0 }}>
              <div style={{ fontSize: 32, fontWeight: 800, color: verdictColor(data.verdict), fontFamily: "monospace" }}>{data.score}</div>
              <div style={{ fontSize: 10, color: "#64748B", textTransform: "uppercase", letterSpacing: ".5px" }}>Score</div>
            </div>
          </div>
          <div style={{ background: "#1A1F2E", borderRadius: 8, padding: "12px 14px", marginBottom: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#64748B", marginBottom: 6 }}><span>Eligibility Score</span><span>{data.score}/100</span></div>
            <div style={{ height: 8, background: "#1E2537", borderRadius: 4 }}>
              <div style={{ height: 8, borderRadius: 4, width: `${data.score}%`, background: `linear-gradient(90deg, ${verdictColor(data.verdict)}, ${verdictColor(data.verdict)}99)`, transition: "width 1s ease" }} />
            </div>
          </div>
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: "#94A3B8", marginBottom: 8, textTransform: "uppercase", letterSpacing: ".5px" }}>Eligibility Criteria</div>
            {data.criteria.map((c, i) => (
              <div key={i} style={{ background: "#1A1F2E", border: `1px solid ${statusColor(c.status)}30`, borderRadius: 8, padding: "10px 14px", marginBottom: 8, display: "flex", gap: 12, alignItems: "flex-start" }}>
                <span style={{ fontSize: 14, color: statusColor(c.status), flexShrink: 0, marginTop: 1 }}>{statusIcon(c.status)}</span>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: "#E2E8F0", marginBottom: 2 }}>{c.name}</div>
                  <div style={{ fontSize: 11, color: "#64748B" }}>{c.detail}</div>
                </div>
              </div>
            ))}
          </div>
          {data.missing_documents?.length > 0 && (
            <div style={{ background: "#F59E0B10", border: "1px solid #F59E0B30", borderRadius: 8, padding: "12px 14px", marginBottom: 14 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: "#F59E0B", marginBottom: 8 }}>⚠ Missing Documents</div>
              {data.missing_documents.map((d, i) => (
                <div key={i} style={{ fontSize: 11, color: "#94A3B8", marginBottom: 4, display: "flex", gap: 6, alignItems: "center" }}>
                  <span style={{ width: 4, height: 4, borderRadius: "50%", background: "#F59E0B", display: "inline-block", flexShrink: 0 }} />{d}
                </div>
              ))}
            </div>
          )}
          {data.recommendations?.length > 0 && (
            <div style={{ background: "#3B82F610", border: "1px solid #3B82F630", borderRadius: 8, padding: "12px 14px" }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: "#3B82F6", marginBottom: 8 }}>💡 Recommendations</div>
              {data.recommendations.map((r, i) => (
                <div key={i} style={{ fontSize: 11, color: "#94A3B8", marginBottom: 4, display: "flex", gap: 6, alignItems: "flex-start" }}>
                  <span style={{ width: 4, height: 4, borderRadius: "50%", background: "#3B82F6", display: "inline-block", flexShrink: 0, marginTop: 4 }} />{r}
                </div>
              ))}
            </div>
          )}
          <button onClick={() => mutation.mutate()} style={{ marginTop: 14, padding: "8px 16px", borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: "pointer", border: "1px solid #1E2537", background: "transparent", color: "#94A3B8" }}>Re-check</button>
        </>
      )}
    </Modal>
  );
}

// ─── Document Checklist Modal ─────────────────────────────────────────────────

function DocumentChecklistModal({ tender, onClose }: { tender: TenderDetail; onClose: () => void }) {
  const [checked, setChecked] = useState<Record<string, boolean>>({});

  const mutation = useMutation<DocumentChecklistResponse, Error>({
    mutationFn: () =>
      api.post("/api/v1/intelligence/document-checklist", {
        tender_id: tender.id,
        tender_title: tender.title,
        tender_category: tender.category,
        estimated_value: tender.estimated_value,
        tender_location: tender.state,
        description: tender.description,
        lang: "en",
      }),
    onSuccess: (data) => {
      const initial: Record<string, boolean> = {};
      data.checklist.forEach((item) => {
        if (item.status === "have" || item.in_vault) initial[item.id] = true;
      });
      setChecked(initial);
    },
  });

  const data = mutation.data;
  const toggleCheck = (id: string) => setChecked((prev) => ({ ...prev, [id]: !prev[id] }));
  const checkedCount = Object.values(checked).filter(Boolean).length;
  const total = data?.checklist.length ?? 0;
  const readiness = total > 0 ? Math.round((checkedCount / total) * 100) : 0;
  const readinessColor = readiness >= 80 ? "#10B981" : readiness >= 50 ? "#F59E0B" : "#EF4444";

  return (
    <Modal title="📋 Document Checklist" onClose={onClose}>
      <style>{`@keyframes ispin{to{transform:rotate(360deg)}}`}</style>
      {!data && !mutation.isPending && (
        <>
          <p style={{ color: "#94A3B8", fontSize: 13, marginBottom: 16 }}>AI will generate a required document checklist for this tender and match against your Vault.</p>
          <button onClick={() => mutation.mutate()} style={{ padding: "10px 20px", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer", border: "none", background: "#6366F1", color: "#fff" }}>Generate Checklist</button>
        </>
      )}
      {mutation.isPending && (
        <div style={{ textAlign: "center", padding: "32px 0", color: "#64748B", fontSize: 13 }}>
          <div style={{ width: 32, height: 32, border: "3px solid #1E2537", borderTopColor: "#6366F1", borderRadius: "50%", animation: "ispin .7s linear infinite", margin: "0 auto 12px" }} />
          Generating checklist…
        </div>
      )}
      {mutation.isError && (
        <div style={{ background: "#EF444420", border: "1px solid #EF444440", borderRadius: 6, padding: "10px 14px", color: "#FCA5A5", fontSize: 12, marginBottom: 12 }}>
          Failed to generate checklist. Please try again.
          <button onClick={() => mutation.mutate()} style={{ marginLeft: 8, background: "none", border: "none", color: "#3B82F6", cursor: "pointer", fontSize: 12 }}>Retry</button>
        </div>
      )}
      {data && (
        <>
          <div style={{ background: readinessColor + "18", border: `1px solid ${readinessColor}40`, borderRadius: 10, padding: "14px 18px", marginBottom: 16, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: readinessColor }}>Readiness Score</div>
              <div style={{ fontSize: 11, color: "#94A3B8", marginTop: 3 }}>{data.summary}</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 28, fontWeight: 800, color: readinessColor, fontFamily: "monospace" }}>{readiness}%</div>
              <div style={{ fontSize: 10, color: "#64748B" }}>{checkedCount}/{total} docs</div>
            </div>
          </div>
          <div style={{ height: 6, background: "#1E2537", borderRadius: 3, marginBottom: 16 }}>
            <div style={{ height: 6, borderRadius: 3, background: readinessColor, width: `${readiness}%`, transition: "width 0.5s ease" }} />
          </div>
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            {[{ val: checkedCount, label: "Have", color: "#10B981" }, { val: total - checkedCount, label: "Missing", color: "#EF4444" }, { val: total, label: "Total", color: "#3B82F6" }].map(({ val, label, color }) => (
              <div key={label} style={{ flex: 1, background: color + "15", border: `1px solid ${color}30`, borderRadius: 8, padding: 10, textAlign: "center" }}>
                <div style={{ fontSize: 18, fontWeight: 700, color, fontFamily: "monospace" }}>{val}</div>
                <div style={{ fontSize: 10, color: "#64748B", textTransform: "uppercase", letterSpacing: ".5px" }}>{label}</div>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {data.checklist.map((item) => {
              const isChecked = !!checked[item.id];
              return (
                <div key={item.id} style={{ background: isChecked ? "#10B98108" : "#1A1F2E", border: `1px solid ${isChecked ? "#10B98140" : item.required ? "#EF444430" : "#1E2537"}`, borderRadius: 8, padding: "12px 14px", cursor: "pointer", transition: "all 0.15s" }} onClick={() => toggleCheck(item.id)}>
                  <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                    <div style={{ width: 18, height: 18, borderRadius: 4, border: `2px solid ${isChecked ? "#10B981" : "#475569"}`, background: isChecked ? "#10B981" : "transparent", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 1 }}>
                      {isChecked && <span style={{ color: "#fff", fontSize: 11, fontWeight: 700 }}>✓</span>}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3 }}>
                        <span style={{ fontSize: 13, fontWeight: 600, color: isChecked ? "#10B981" : "#E2E8F0" }}>{item.name}</span>
                        {item.required && <span style={{ fontSize: 9, fontWeight: 700, color: "#EF4444", textTransform: "uppercase" }}>Required</span>}
                        {item.in_vault && <span style={{ fontSize: 9, fontWeight: 700, color: "#10B981", background: "#10B98115", padding: "1px 6px", borderRadius: 10 }}>In Vault</span>}
                      </div>
                      <div style={{ fontSize: 11, color: "#64748B" }}>{item.description}</div>
                      {item.notes && <div style={{ fontSize: 10, color: "#F59E0B", marginTop: 4 }}>💡 {item.notes}</div>}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          <button onClick={() => mutation.mutate()} style={{ marginTop: 16, padding: "8px 16px", borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: "pointer", border: "1px solid #1E2537", background: "transparent", color: "#94A3B8" }}>Regenerate</button>
        </>
      )}
    </Modal>
  );
}

// ─── Price Intelligence Modal ─────────────────────────────────────────────────

function PriceIntelligenceModal({ tender, companyId, onClose }: { tender: TenderDetail; companyId: string; onClose: () => void }) {
  const [bidAmount, setBidAmount] = useState(
    tender.estimated_value ? String(Math.round(tender.estimated_value * 0.92)) : ""
  );
  const [hasAnalysed, setHasAnalysed] = useState(false);

  const mutation = useMutation<PriceIntelligenceResponse, Error>({
    mutationFn: () =>
      api.post("/api/v1/intelligence/bid/price-intelligence", {
        tender_id: tender.id,
        company_id: companyId,
        our_bid_amount: bidAmount ? parseFloat(bidAmount) : null,
      }),
    onSuccess: () => setHasAnalysed(true),
  });

  const data = mutation.data;
  const scoreColor = (s: number) => s >= 80 ? "#10B981" : s >= 55 ? "#F59E0B" : "#EF4444";
  const bandColors = ["#10B981", "#3B82F6", "#F59E0B", "#EF4444"];

  const TrendChart = ({ trend }: { trend: PriceTrendPoint[] }) => {
    const W = 480, H = 100, PAD = 32;
    const allVals = [...trend.map(t => t.avg), ...trend.map(t => t.min), ...trend.map(t => t.max)];
    const lo = Math.min(...allVals), hi = Math.max(...allVals), range = hi - lo || 1;
    const xScale = (i: number) => PAD + (i / (trend.length - 1)) * (W - PAD * 2);
    const yScale = (v: number) => H - 12 - ((v - lo) / range) * (H - 24);
    const avgPath = trend.map((t, i) => `${i === 0 ? "M" : "L"}${xScale(i)},${yScale(t.avg)}`).join(" ");
    const areaPath = [
      ...trend.map((t, i) => `${i === 0 ? "M" : "L"}${xScale(i)},${yScale(t.max)}`),
      ...trend.map((t, i) => `L${xScale(trend.length - 1 - i)},${yScale(trend[trend.length - 1 - i].min)}`),
      "Z",
    ].join(" ");
    return (
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: 100 }}>
        <defs>
          <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#3B82F6" stopOpacity="0.03" />
          </linearGradient>
        </defs>
        <path d={areaPath} fill="url(#trendGrad)" />
        <path d={avgPath} fill="none" stroke="#3B82F6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        {trend.map((t, i) => <circle key={i} cx={xScale(i)} cy={yScale(t.avg)} r="3" fill="#3B82F6" />)}
        {trend.map((t, i) => <text key={i} x={xScale(i)} y={H - 1} textAnchor="middle" fontSize="9" fill="#475569">{t.label}</text>)}
      </svg>
    );
  };

  return (
    <Modal title="💰 Price Intelligence" onClose={onClose}>
      <style>{`
        .pi-input{width:100%;padding:9px 12px;background:#1A1F2E;border:1px solid #1E2537;border-radius:8px;color:#E2E8F0;font-size:13px;outline:none}
        .pi-input:focus{border-color:#F59E0B}
        .pi-btn{padding:10px 20px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;border:none;background:#F59E0B;color:#111;transition:opacity .15s;margin-top:10px}
        .pi-btn:hover{opacity:.85}
        .pi-btn:disabled{opacity:.4;cursor:not-allowed}
        .pi-btn--sm{padding:7px 14px;font-size:12px;background:transparent;border:1px solid #1E2537;color:#94A3B8;margin-top:14px}
        .pi-spinner{width:13px;height:13px;border:2px solid #1E2537;border-top-color:#F59E0B;border-radius:50%;animation:pispin .7s linear infinite;display:inline-block;vertical-align:middle;margin-right:6px}
        @keyframes pispin{to{transform:rotate(360deg)}}
        .pi-card{background:#1A1F2E;border:1px solid #1E2537;border-radius:8px;padding:14px;margin-top:10px}
        .pi-section-title{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;color:#475569;margin-bottom:10px}
      `}</style>

      <div style={{ marginBottom: 4 }}>
        <label style={{ fontSize: 12, color: "#64748B", display: "block", marginBottom: 6 }}>
          Your intended bid amount <span style={{ color: "#F59E0B" }}>*</span>
        </label>
        <input className="pi-input" type="number" placeholder="Enter your bid amount in ₹"
          value={bidAmount} onChange={e => setBidAmount(e.target.value)} />
        {tender.estimated_value ? (
          <div style={{ fontSize: 11, color: "#475569", marginTop: 4 }}>
            Tender estimate: {fmt(tender.estimated_value)} · Pre-filled at 92% (optimal zone)
          </div>
        ) : (
          <div style={{ fontSize: 11, color: "#F59E0B", marginTop: 4 }}>
            ⚠ No tender estimate available — enter your bid amount to analyse
          </div>
        )}
      </div>

      <button className="pi-btn" disabled={mutation.isPending || !bidAmount} onClick={() => mutation.mutate()}>
        {mutation.isPending ? <><span className="pi-spinner" />Analysing…</> : hasAnalysed ? "Re-analyse" : "Analyse Pricing"}
      </button>

      {mutation.isError && (
        <div style={{ background: "#EF444420", border: "1px solid #EF444440", borderRadius: 6, padding: "10px 14px", color: "#FCA5A5", fontSize: 12, marginTop: 12 }}>
          Analysis failed. Please try again.
        </div>
      )}

      {data && !data.market_avg && (
        <div style={{ background: "#F59E0B10", border: "1px solid #F59E0B30", borderRadius: 8, padding: "14px 16px", marginTop: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#F59E0B", marginBottom: 6 }}>⚠ Not enough similar tenders found</div>
          <div style={{ fontSize: 12, color: "#94A3B8", lineHeight: 1.6 }}>
            No tenders with a similar value range were found in the <strong style={{ color: "#E2E8F0" }}>{data.category}</strong> category.
          </div>
          <div style={{ fontSize: 11, color: "#64748B", marginTop: 8 }}>
            💡 Try the <strong style={{ color: "#E2E8F0" }}>Market Price</strong> button for a broader category overview.
          </div>
        </div>
      )}

      {!hasAnalysed && !mutation.isPending && (
        <p style={{ color: "#475569", fontSize: 13, textAlign: "center", marginTop: 28 }}>
          {bidAmount ? "Click Analyse Pricing to see market intelligence" : "Enter your bid amount and click Analyse Pricing"}
        </p>
      )}

      {data && data.market_avg && (
        <>
          {data.our_bid_amount && (
            <div style={{ background: scoreColor(data.price_to_win_score) + "14", border: `1px solid ${scoreColor(data.price_to_win_score)}35`, borderRadius: 10, padding: "16px 18px", marginTop: 16, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
              <div>
                <div style={{ fontSize: 11, color: "#64748B", marginBottom: 4 }}>Price-to-Win Score</div>
                <div style={{ fontSize: 15, fontWeight: 700, color: scoreColor(data.price_to_win_score) }}>{data.price_to_win_label}</div>
                {data.optimal_price && (
                  <div style={{ fontSize: 11, color: "#64748B", marginTop: 5 }}>
                    Optimal target: <span style={{ color: "#F1F5F9", fontFamily: "monospace" }}>{fmt(data.optimal_price)}</span>
                  </div>
                )}
              </div>
              <div style={{ textAlign: "center", flexShrink: 0 }}>
                <div style={{ fontSize: 36, fontWeight: 800, color: scoreColor(data.price_to_win_score), fontFamily: "monospace", lineHeight: 1 }}>{data.price_to_win_score}</div>
                <div style={{ fontSize: 10, color: "#64748B" }}>/ 100</div>
              </div>
            </div>
          )}

          <div className="pi-card">
            <div className="pi-section-title">Market Benchmarks — {data.category}</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginBottom: 12 }}>
              {[
                { label: "Market Min", value: fmtShort(data.market_min!), color: "#10B981" },
                { label: "Market Avg", value: fmtShort(data.market_avg), color: "#F1F5F9" },
                { label: "Market Max", value: fmtShort(data.market_max!), color: "#EF4444" },
              ].map(({ label, value, color }) => (
                <div key={label} style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 15, fontWeight: 700, color, fontFamily: "monospace" }}>{value}</div>
                  <div style={{ fontSize: 10, color: "#475569" }}>{label}</div>
                </div>
              ))}
            </div>
            {data.our_position_pct !== null && data.our_position_pct !== undefined && (
              <>
                <div style={{ fontSize: 10, color: "#475569", marginBottom: 6 }}>Your bid position in market range</div>
                <div style={{ position: "relative", height: 8, background: "#1E2537", borderRadius: 4, marginBottom: 4 }}>
                  <div style={{ position: "absolute", height: 8, borderRadius: 4, background: "linear-gradient(90deg,#10B981,#3B82F6,#F59E0B,#EF4444)", width: "100%", opacity: 0.3 }} />
                  <div style={{ position: "absolute", top: -3, width: 14, height: 14, borderRadius: "50%", background: scoreColor(data.price_to_win_score), border: "2px solid #0F1117", left: `calc(${(data.our_position_pct * 100).toFixed(1)}% - 7px)`, transition: "left 0.8s ease" }} />
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9, color: "#475569" }}>
                  <span>Min (L1)</span><span>Avg</span><span>Max</span>
                </div>
              </>
            )}
            {data.sample_count > 0 && (
              <div style={{ fontSize: 11, color: "#475569", marginTop: 8 }}>
                Based on {data.sample_count} similar tenders · <span style={{ fontStyle: "italic" }}>Market benchmarks from live tender data</span>
              </div>
            )}
          </div>

          {data.trend?.length > 0 && (
            <div className="pi-card">
              <div className="pi-section-title">Price Trend — {data.category}</div>
              <TrendChart trend={data.trend} />
              <div style={{ fontSize: 10, color: "#475569", marginTop: 4 }}>
                Blue line = market avg · Shaded area = min–max range · <span style={{ color: "#374151" }}>Trend is estimated from current spread</span>
              </div>
            </div>
          )}

          {data.bands?.length > 0 && (
            <div className="pi-card">
              <div className="pi-section-title">Price Bands</div>
              {data.bands.map((band, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "9px 0", borderBottom: i < data.bands.length - 1 ? "1px solid #1E2537" : "none" }}>
                  <div style={{ width: 3, height: 36, borderRadius: 2, background: bandColors[i], flexShrink: 0 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: bandColors[i], marginBottom: 2 }}>{band.label}</div>
                    <div style={{ fontSize: 10, color: "#475569" }}>{fmtShort(band.min)} – {fmtShort(band.max)}</div>
                    <div style={{ fontSize: 10, color: "#64748B", marginTop: 1 }}>{band.description}</div>
                  </div>
                  <div style={{ textAlign: "right", flexShrink: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: bandColors[i], fontFamily: "monospace" }}>{(band.win_rate_estimate * 100).toFixed(0)}%</div>
                    <div style={{ fontSize: 9, color: "#475569" }}>est. win rate</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {data.insights?.length > 0 && (
            <div className="pi-card">
              <div className="pi-section-title">💡 Insights</div>
              {data.insights.map((ins, i) => (
                <div key={i} style={{ display: "flex", gap: 8, alignItems: "flex-start", marginBottom: 8, fontSize: 12, color: "#94A3B8", lineHeight: 1.5 }}>
                  <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#F59E0B", flexShrink: 0, marginTop: 5, display: "inline-block" }} />
                  {ins}
                </div>
              ))}
            </div>
          )}

          <button className="pi-btn pi-btn--sm" onClick={() => mutation.mutate()}>Re-analyse</button>
        </>
      )}
    </Modal>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function TenderDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [modal, setModal] = useState<"winprob" | "competitors" | "market" | "eligibility" | "trackbid" | "checklist" | "priceintel" | null>(null);

  const { data: rawData, isLoading, error, refetch } = useQuery({
    queryKey: ["tender", params.id],
    queryFn: () => api.tenders.get(params.id),
    staleTime: 60_000,
  });

  const tender: TenderDetail | null = rawData
    ? ((rawData as any).data ?? rawData) as TenderDetail
    : null;

  const { data: profileData } = useQuery({
    queryKey: ["company-profile"],
    queryFn: () => api.companies.getProfile(),
    staleTime: 300_000,
  });

  const companyId = (profileData as any)?.id ?? null;

  const formatDate = (d: string | null | undefined) => {
    if (!d) return "—";
    const dt = new Date(d);
    if (isNaN(dt.getTime())) return "—";
    return dt.toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" });
  };

  const formatCurrency = (v: number | null | undefined) => {
    if (v == null) return "—";
    return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(v);
  };

  const getDeadlineColor = (d: string | null | undefined) => {
    if (!d) return "text-gray-600";
    const days = Math.ceil((new Date(d).getTime() - Date.now()) / 86400000);
    if (days <= 3) return "text-red-600";
    if (days <= 7) return "text-orange-600";
    return "text-green-600";
  };

  const getDaysLeft = (d: string | null | undefined) => {
    if (!d) return null;
    const days = Math.ceil((new Date(d).getTime() - Date.now()) / 86400000);
    if (days < 0) return "Closed";
    if (days === 0) return "Due today";
    return `${days} days left`;
  };

  if (isLoading) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <p className="text-gray-600">Loading tender...</p>
    </div>
  );

  if (error || !tender) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <p className="text-red-600 mb-4">Failed to load tender</p>
        <Button onClick={() => refetch()}>Retry</Button>
        <button onClick={() => router.back()} className="ml-2 px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50">Go Back</button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <button onClick={() => router.back()} className="text-sm text-gray-500 hover:text-gray-700 mb-6 flex items-center gap-1">← Back</button>

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
            {tender.category && <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium capitalize">{tender.category.replace("_", " ")}</span>}
            {tender.status && <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm font-medium capitalize">{tender.status.replace("_", " ")}</span>}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Key Details</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
            <div><p className="text-gray-500">Posted</p><p className="font-medium text-gray-900">{formatDate(tender.published_date)}</p></div>
            <div><p className="text-gray-500">Deadline</p><p className={cn("font-medium", getDeadlineColor(tender.bid_submission_deadline))}>{formatDate(tender.bid_submission_deadline)}</p></div>
            <div><p className="text-gray-500">Estimated Value</p><p className="font-medium text-gray-900">{formatCurrency(tender.estimated_value)}</p></div>
            <div><p className="text-gray-500">EMD Amount</p><p className="font-medium text-gray-900">{formatCurrency(tender.emd_amount)}</p></div>
            <div><p className="text-gray-500">Document Fee</p><p className="font-medium text-gray-900">{formatCurrency(tender.processing_fee)}</p></div>
            <div><p className="text-gray-500">Tender ID</p><p className="font-medium text-gray-900 text-xs break-all">{tender.tender_id || tender.id}</p></div>
          </div>
        </div>

        {tender.description && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Description</h2>
            <p className="text-gray-700 leading-relaxed whitespace-pre-line">{tender.description}</p>
          </div>
        )}

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Actions</h2>
          <div className="flex flex-wrap gap-3">
            {tender.source_url && (
              <a href={tender.source_url} target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center justify-center px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 transition-colors">
                View on Source Site ↗
              </a>
            )}
            <button onClick={() => setModal("eligibility")} className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-md text-sm font-medium hover:bg-emerald-700 transition-colors">✅ Check Eligibility</button>
            <button onClick={() => setModal("winprob")} className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 transition-colors">🎯 Win Probability</button>
            <button onClick={() => setModal("competitors")} className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-md text-sm font-medium hover:bg-purple-700 transition-colors">🏆 Competitors</button>
            <button onClick={() => setModal("market")} className="inline-flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-md text-sm font-medium hover:bg-orange-700 transition-colors">📊 Market Price</button>
            <button onClick={() => setModal("priceintel")} className="inline-flex items-center gap-2 px-4 py-2 bg-yellow-500 text-gray-900 rounded-md text-sm font-medium hover:bg-yellow-400 transition-colors">💰 Price Intel</button>
            <button onClick={() => setModal("checklist")} className="inline-flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-md text-sm font-medium hover:bg-violet-700 transition-colors">📋 Doc Checklist</button>
            <button onClick={() => setModal("trackbid")} className="inline-flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-md text-sm font-medium hover:bg-gray-800 transition-colors">📌 Track this Bid</button>
            <Button variant="outline" onClick={() => router.back()}>Back to Tenders</Button>
          </div>
        </div>
      </div>

      {modal === "winprob" && companyId && <WinProbabilityModal tender={tender} companyId={companyId} onClose={() => setModal(null)} />}
      {modal === "competitors" && companyId && <CompetitorsModal tender={tender} companyId={companyId} onClose={() => setModal(null)} />}
      {modal === "market" && <MarketPriceModal tender={tender} onClose={() => setModal(null)} />}
      {modal === "eligibility" && <EligibilityModal tender={tender} profile={profileData} onClose={() => setModal(null)} />}
      {modal === "checklist" && <DocumentChecklistModal tender={tender} onClose={() => setModal(null)} />}
      {modal === "priceintel" && companyId && <PriceIntelligenceModal tender={tender} companyId={companyId} onClose={() => setModal(null)} />}
      {modal === "trackbid" && companyId && <TrackBidModal tender={tender} companyId={companyId} onClose={() => setModal(null)} />}
      {(modal === "winprob" || modal === "competitors" || modal === "eligibility" || modal === "trackbid" || modal === "priceintel") && !companyId && (
        <Modal title="Profile Required" onClose={() => setModal(null)}>
          <p style={{ color: "#94A3B8", fontSize: 14 }}>
            Please complete your <a href="/profile" style={{ color: "#3B82F6" }}>company profile</a> before using this feature.
          </p>
        </Modal>
      )}
    </div>
  );
}
