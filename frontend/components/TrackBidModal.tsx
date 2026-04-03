"use client";

// ── TrackBidModal ─────────────────────────────────────────────────────────────
// Drop this component into frontend/app/(dashboard)/tenders/[id]/page.tsx
// Import it and add <TrackBidModal /> alongside the other modals.
//
// Usage: add `trackBid` to the activeModal state union, then trigger it with:
//   <button onClick={() => setActiveModal("trackBid")}>Track this Bid</button>

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface TrackBidModalProps {
  tender: {
    id: string;                  // DB UUID (not URL param)
    title: string;
    bid_submission_deadline?: string;
    emd_amount?: string;
    estimated_value?: string;
  };
  companyId: string;
  onClose: () => void;
}

export function TrackBidModal({ tender, companyId, onClose }: TrackBidModalProps) {
  const qc = useQueryClient();

  const [form, setForm] = useState({
    bid_amount: tender.estimated_value ? String(parseFloat(tender.estimated_value) * 0.95) : "",
    notes: "",
    emd_amount: tender.emd_amount || "",
  });

  const mutation = useMutation({
    mutationFn: () => {
      const now = new Date();
      const bidNumber = `BID-${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, "0")}${String(now.getDate()).padStart(2, "0")}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;
      return api.bids.create({
        tender_id: tender.id,
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-white font-semibold text-lg">Track this Bid</h2>
              <p className="text-blue-100 text-sm mt-0.5 line-clamp-1">{tender.title}</p>
            </div>
            <button onClick={onClose} className="text-white/70 hover:text-white transition-colors text-xl leading-none">&times;</button>
          </div>
        </div>

        {/* Form */}
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
              <p className="text-xs text-gray-400 mt-1">
                Estimated value: ₹{parseFloat(tender.estimated_value).toLocaleString("en-IN")}
              </p>
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
        </div>

        {/* Actions */}
        <div className="px-6 pb-5 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 border border-gray-200 text-gray-600 rounded-lg py-2.5 text-sm font-medium hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={!form.bid_amount || mutation.isPending}
            className="flex-1 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg py-2.5 text-sm font-medium hover:from-blue-700 hover:to-indigo-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {mutation.isPending ? "Tracking..." : "Start Tracking →"}
          </button>
        </div>
      </div>
    </div>
  );
}
