"use client";
export const dynamic = "force-dynamic";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Bid {
  id: string;
  tender_id: number;
  title: string;
  bid_number: string;
  bid_amount: number;
  emd_amount?: number;
  status: string;
  submission_deadline: string;
  submission_date?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

interface BidStats {
  total_bids: number;
  draft_bids: number;
  submitted_bids: number;
  won_bids: number;
  lost_bids: number;
  total_bid_value: number;
  won_bid_value: number;
  win_rate: number;
  average_bid_amount: number;
}

// ── Status config ─────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; border: string; dot: string }> = {
  draft:               { label: "Draft",             color: "text-gray-600",  bg: "bg-gray-50",   border: "border-gray-200", dot: "bg-gray-400"   },
  reviewing:           { label: "Reviewing",         color: "text-amber-700", bg: "bg-amber-50",  border: "border-amber-200", dot: "bg-amber-500"  },
  submitted:           { label: "Submitted",         color: "text-blue-700",  bg: "bg-blue-50",   border: "border-blue-200",  dot: "bg-blue-500"   },
  under_evaluation:    { label: "Under Evaluation",  color: "text-purple-700",bg: "bg-purple-50", border: "border-purple-200",dot: "bg-purple-500" },
  technically_qualified:{ label: "Tech Qualified",  color: "text-teal-700",  bg: "bg-teal-50",   border: "border-teal-200",  dot: "bg-teal-500"   },
  financially_qualified:{ label: "Fin Qualified",   color: "text-cyan-700",  bg: "bg-cyan-50",   border: "border-cyan-200",  dot: "bg-cyan-500"   },
  awarded:             { label: "Awarded",           color: "text-indigo-700",bg: "bg-indigo-50", border: "border-indigo-200",dot: "bg-indigo-500" },
  won:                 { label: "Won ✓",             color: "text-green-700", bg: "bg-green-50",  border: "border-green-200", dot: "bg-green-500"  },
  lost:                { label: "Lost",              color: "text-red-700",   bg: "bg-red-50",    border: "border-red-200",   dot: "bg-red-500"    },
  withdrawn:           { label: "Withdrawn",         color: "text-orange-700",bg: "bg-orange-50", border: "border-orange-200",dot: "bg-orange-500" },
  disqualified:        { label: "Disqualified",      color: "text-rose-700",  bg: "bg-rose-50",   border: "border-rose-200",  dot: "bg-rose-500"   },
  on_hold:             { label: "On Hold",           color: "text-slate-700", bg: "bg-slate-50",  border: "border-slate-200", dot: "bg-slate-500"  },
  cancelled:           { label: "Cancelled",         color: "text-gray-500",  bg: "bg-gray-50",   border: "border-gray-200",  dot: "bg-gray-400"   },
};

// What transitions are allowed from each status (non-final only)
const ALLOWED_TRANSITIONS: Record<string, string[]> = {
  draft:            ["reviewing", "submitted", "withdrawn", "cancelled"],
  reviewing:        ["submitted", "withdrawn", "cancelled", "on_hold"],
  submitted:        ["under_evaluation", "withdrawn"],
  under_evaluation: ["technically_qualified", "financially_qualified", "awarded", "lost", "disqualified"],
  technically_qualified: ["financially_qualified", "awarded", "lost"],
  financially_qualified: ["awarded", "lost"],
  awarded:          ["won", "lost"],
  on_hold:          ["reviewing", "cancelled"],
};

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmt = (n: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);

const fmtDate = (d: string) =>
  new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });

const daysUntil = (d: string) => {
  const diff = Math.ceil((new Date(d).getTime() - Date.now()) / 86400000);
  return diff;
};

// ── Status Badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.draft;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${cfg.color} ${cfg.bg} ${cfg.border}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}

// ── Stat Card ─────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${accent ?? "text-gray-900"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

// ── Bid Card ──────────────────────────────────────────────────────────────────

function BidCard({ bid, onTransition, onDelete }: {
  bid: Bid;
  onTransition: (bid: Bid) => void;
  onDelete: (bid: Bid) => void;
}) {
  const days = daysUntil(bid.submission_deadline);
  const isUrgent = days >= 0 && days <= 3;
  const isOverdue = days < 0;

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md hover:border-gray-200 transition-all p-4 space-y-3">
      {/* Title + status */}
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-semibold text-gray-900 line-clamp-2 leading-snug flex-1">{bid.title}</p>
        <StatusBadge status={bid.status} />
      </div>

      {/* Bid number */}
      <p className="text-xs text-gray-400 font-mono">{bid.bid_number}</p>

      {/* Amount */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-gray-500">Bid Amount</p>
          <p className="text-base font-bold text-gray-900">{fmt(bid.bid_amount)}</p>
        </div>
        {bid.emd_amount && (
          <div className="text-right">
            <p className="text-xs text-gray-500">EMD</p>
            <p className="text-sm font-medium text-gray-700">{fmt(bid.emd_amount)}</p>
          </div>
        )}
      </div>

      {/* Deadline */}
      <div className={`flex items-center gap-1.5 text-xs rounded-lg px-2.5 py-1.5 ${
        isOverdue ? "bg-red-50 text-red-700" :
        isUrgent  ? "bg-amber-50 text-amber-700" :
                    "bg-gray-50 text-gray-600"
      }`}>
        <span>🗓</span>
        <span>
          {isOverdue ? `Closed ${Math.abs(days)}d ago` :
           days === 0 ? "Due today!" :
           `${days}d left — ${fmtDate(bid.submission_deadline)}`}
        </span>
      </div>

      {/* Notes */}
      {bid.notes && <p className="text-xs text-gray-400 line-clamp-1">{bid.notes}</p>}

      {/* Actions */}
      <div className="flex gap-2 pt-1">
        {ALLOWED_TRANSITIONS[bid.status] && (
          <button
            onClick={() => onTransition(bid)}
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded-lg py-2 transition-colors"
          >
            Update Status
          </button>
        )}
        {(bid.status === "draft" || bid.status === "cancelled") && (
          <button
            onClick={() => onDelete(bid)}
            className="px-3 py-2 text-xs text-red-500 hover:bg-red-50 rounded-lg transition-colors border border-red-100"
          >
            Delete
          </button>
        )}
      </div>
    </div>
  );
}

// ── Transition Modal ──────────────────────────────────────────────────────────

function TransitionModal({ bid, onClose, onSuccess }: {
  bid: Bid;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const qc = useQueryClient();
  const [newStatus, setNewStatus] = useState("");
  const [reason, setReason] = useState("");

  const transitions = ALLOWED_TRANSITIONS[bid.status] ?? [];

  const mutation = useMutation({
    mutationFn: () => api.bids.transition(bid.id, newStatus, reason || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bids"] });
      qc.invalidateQueries({ queryKey: ["bid-stats"] });
      onSuccess();
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden">
        <div className="bg-gradient-to-r from-slate-800 to-slate-700 px-5 py-4">
          <div className="flex items-center justify-between">
            <h2 className="text-white font-semibold">Update Bid Status</h2>
            <button onClick={onClose} className="text-white/60 hover:text-white text-xl">&times;</button>
          </div>
          <p className="text-slate-300 text-xs mt-1 line-clamp-1">{bid.title}</p>
        </div>

        <div className="px-5 py-4 space-y-4">
          <div>
            <p className="text-xs text-gray-500 mb-2">Current: <StatusBadge status={bid.status} /></p>
            <label className="block text-sm font-medium text-gray-700 mb-2">Move to</label>
            <div className="grid grid-cols-2 gap-2">
              {transitions.map(s => {
                const cfg = STATUS_CONFIG[s] ?? STATUS_CONFIG.draft;
                return (
                  <button
                    key={s}
                    onClick={() => setNewStatus(s)}
                    className={`text-xs font-medium px-3 py-2.5 rounded-lg border transition-all text-left ${
                      newStatus === s
                        ? `${cfg.bg} ${cfg.border} ${cfg.color} ring-2 ring-offset-1 ring-blue-400`
                        : "border-gray-200 hover:border-gray-300 text-gray-600"
                    }`}
                  >
                    <span className={`w-2 h-2 rounded-full inline-block mr-1.5 ${cfg.dot}`} />
                    {cfg.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Reason (optional)</label>
            <textarea
              value={reason}
              onChange={e => setReason(e.target.value)}
              placeholder="Add a note about this status change..."
              rows={2}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {mutation.isError && (
            <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">
              {(mutation.error as Error).message}
            </p>
          )}
        </div>

        <div className="px-5 pb-5 flex gap-2">
          <button onClick={onClose} className="flex-1 border border-gray-200 text-gray-600 rounded-lg py-2.5 text-sm hover:bg-gray-50 transition-colors">
            Cancel
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={!newStatus || mutation.isPending}
            className="flex-1 bg-slate-800 hover:bg-slate-900 text-white rounded-lg py-2.5 text-sm font-medium transition-colors disabled:opacity-40"
          >
            {mutation.isPending ? "Updating..." : "Update →"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function BidsPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [transitionBid, setTransitionBid] = useState<Bid | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Bid | null>(null);

  const { data: bidsData, isLoading: bidsLoading } = useQuery({
    queryKey: ["bids", search, statusFilter],
    queryFn: () =>
      api.bids.list({
        search: search || undefined,
        status: statusFilter === "all" ? undefined : statusFilter,
        page_size: 50,
      }),
  });

  const { data: statsData } = useQuery({
    queryKey: ["bid-stats"],
    queryFn: () => api.bids.stats(),
  });

  const deleteMutation = useMutation({
    mutationFn: (bid: Bid) => api.bids.delete(bid.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bids"] });
      qc.invalidateQueries({ queryKey: ["bid-stats"] });
      setDeleteTarget(null);
    },
  });

  const bids: Bid[] = bidsData?.bids ?? [];
  const stats: BidStats | undefined = statsData;

  const FILTER_TABS = [
    { key: "all",       label: "All Bids" },
    { key: "draft",     label: "Draft" },
    { key: "reviewing", label: "Reviewing" },
    { key: "submitted", label: "Submitted" },
    { key: "won",       label: "Won" },
    { key: "lost",      label: "Lost" },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Bid Pipeline</h1>
          <p className="text-gray-500 text-sm mt-1">Track and manage all your government tender bids</p>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            <StatCard label="Total Bids" value={String(stats.total_bids)} />
            <StatCard
              label="Total Value"
              value={fmt(stats.total_bid_value)}
              sub="across all bids"
            />
            <StatCard
              label="Won Value"
              value={fmt(stats.won_bid_value)}
              accent="text-green-700"
              sub={`${stats.won_bids} bids won`}
            />
            <StatCard
              label="Win Rate"
              value={`${Math.round(stats.win_rate)}%`}
              accent={stats.win_rate >= 50 ? "text-green-700" : stats.win_rate >= 25 ? "text-amber-700" : "text-gray-900"}
              sub="of submitted bids"
            />
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          {/* Search */}
          <div className="relative flex-1 max-w-xs">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">🔍</span>
            <input
              type="text"
              placeholder="Search bids..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Status tabs */}
          <div className="flex gap-1 overflow-x-auto">
            {FILTER_TABS.map(t => (
              <button
                key={t.key}
                onClick={() => setStatusFilter(t.key)}
                className={`px-3 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
                  statusFilter === t.key
                    ? "bg-blue-600 text-white"
                    : "bg-white border border-gray-200 text-gray-600 hover:border-gray-300"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Bids grid */}
        {bidsLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="bg-white rounded-xl border border-gray-100 h-48 animate-pulse" />
            ))}
          </div>
        ) : bids.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-5xl mb-4">📋</div>
            <h3 className="text-lg font-semibold text-gray-700">No bids yet</h3>
            <p className="text-gray-400 text-sm mt-2">
              Go to a tender and click <strong>"Track this Bid"</strong> to start tracking.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {bids.map(bid => (
              <BidCard
                key={bid.id}
                bid={bid}
                onTransition={setTransitionBid}
                onDelete={setDeleteTarget}
              />
            ))}
          </div>
        )}

        {/* Count */}
        {!bidsLoading && bids.length > 0 && (
          <p className="text-xs text-gray-400 text-center mt-6">
            Showing {bids.length} bid{bids.length !== 1 ? "s" : ""}
            {bidsData?.total > bids.length ? ` of ${bidsData.total}` : ""}
          </p>
        )}
      </div>

      {/* Transition Modal */}
      {transitionBid && (
        <TransitionModal
          bid={transitionBid}
          onClose={() => setTransitionBid(null)}
          onSuccess={() => setTransitionBid(null)}
        />
      )}

      {/* Delete Confirmation */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 space-y-4">
            <div className="text-center">
              <div className="text-4xl mb-3">🗑️</div>
              <h3 className="font-semibold text-gray-900">Delete this bid?</h3>
              <p className="text-sm text-gray-500 mt-1 line-clamp-2">{deleteTarget.title}</p>
            </div>
            <p className="text-xs text-gray-400 text-center">This action cannot be undone.</p>
            <div className="flex gap-3">
              <button
                onClick={() => setDeleteTarget(null)}
                className="flex-1 border border-gray-200 rounded-lg py-2.5 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate(deleteTarget)}
                disabled={deleteMutation.isPending}
                className="flex-1 bg-red-600 hover:bg-red-700 text-white rounded-lg py-2.5 text-sm font-medium transition-colors disabled:opacity-50"
              >
                {deleteMutation.isPending ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
