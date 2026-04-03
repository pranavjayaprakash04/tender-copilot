"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Bid {
  id: string;
  tender_id: string;
  tender_title: string;
  company_id: string;
  status: "draft" | "reviewing" | "submitted" | "won" | "lost" | "withdrawn";
  executive_summary?: string;
  technical_approach?: string;
  financial_proposal?: string;
  compliance_statement?: string;
  created_at: string;
  updated_at: string;
}

interface OutcomeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (outcome: "won" | "lost", ourPrice: number, winningPrice?: number) => void;
  loading: boolean;
}

function OutcomeModal({ isOpen, onClose, onSubmit, loading }: OutcomeModalProps) {
  const [outcome, setOutcome] = useState<"won" | "lost">("won");
  const [ourPrice, setOurPrice] = useState("");
  const [winningPrice, setWinningPrice] = useState("");

  const handleSubmit = () => {
    if (!ourPrice) return;
    onSubmit(
      outcome,
      parseFloat(ourPrice),
      outcome === "lost" && winningPrice ? parseFloat(winningPrice) : undefined
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-2xl">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Record Outcome</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Result</label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="won"
                  checked={outcome === "won"}
                  onChange={() => setOutcome("won")}
                />
                <span className="text-green-700 font-medium">Won</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="lost"
                  checked={outcome === "lost"}
                  onChange={() => setOutcome("lost")}
                />
                <span className="text-red-700 font-medium">Lost</span>
              </label>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Our Price (₹)
            </label>
            <input
              type="number"
              step="1"
              value={ourPrice}
              onChange={(e) => setOurPrice(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              placeholder="0"
              required
            />
          </div>

          {outcome === "lost" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Winning Price (₹)
              </label>
              <input
                type="number"
                step="1"
                value={winningPrice}
                onChange={(e) => setWinningPrice(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                placeholder="0"
              />
            </div>
          )}
        </div>

        <div className="flex gap-3 pt-5">
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button
            variant="default"
            onClick={handleSubmit}
            disabled={loading || !ourPrice}
          >
            {loading ? "Saving…" : "Submit Outcome"}
          </Button>
        </div>
      </div>
    </div>
  );
}

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-800",
  reviewing: "bg-yellow-100 text-yellow-800",
  submitted: "bg-blue-100 text-blue-800",
  won: "bg-green-100 text-green-800",
  lost: "bg-red-100 text-red-800",
  withdrawn: "bg-gray-100 text-gray-600",
};

function BidSection({ title, content }: { title: string; content?: string }) {
  if (!content) return null;
  return (
    <div className="bg-gray-50 rounded-lg p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3 uppercase tracking-wide">{title}</h3>
      <div className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">{content}</div>
    </div>
  );
}

export default function BidDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [showOutcomeModal, setShowOutcomeModal] = useState(false);

  const { data: bid, isLoading, error } = useQuery<Bid>({
    queryKey: ["bid", params.id],
    queryFn: () => api.bids.get(params.id),
  });

  const updateStatusMutation = useMutation({
    mutationFn: (status: string) => api.bids.updateStatus(params.id, status),
    onSuccess: () => window.location.reload(),
  });

  const recordOutcomeMutation = useMutation({
    mutationFn: (data: { outcome: "won" | "lost"; our_price: number; winning_price?: number }) =>
      api.bids.recordOutcome(params.id, data),
    onSuccess: () => {
      setShowOutcomeModal(false);
      window.location.reload();
    },
  });

  const formatDate = (dateString: string) =>
    new Date(dateString).toLocaleDateString("en-IN", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-gray-200 rounded w-1/3" />
            <div className="h-32 bg-gray-200 rounded" />
            <div className="h-48 bg-gray-200 rounded" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !bid) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <div className="text-center py-12">
            <div className="text-4xl mb-4">⚠️</div>
            <p className="text-red-600 mb-4 font-medium">Bid not found or could not be loaded.</p>
            <Button onClick={() => router.push("/bids")}>Back to Bids</Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <button
            onClick={() => router.push("/bids")}
            className="text-sm text-gray-500 hover:text-gray-900 flex items-center gap-1"
          >
            ← Back
          </button>
          <h1 className="text-2xl font-bold text-gray-900">Bid Details</h1>
        </div>

        {/* Status & Actions */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">{bid.tender_title}</h2>
              <div className="flex flex-wrap gap-4 text-sm text-gray-500">
                <span>Created: {formatDate(bid.created_at)}</span>
                <span>Updated: {formatDate(bid.updated_at)}</span>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
              <span
                className={cn(
                  "px-3 py-1 rounded-full text-sm font-medium",
                  STATUS_COLORS[bid.status] ?? "bg-gray-100 text-gray-800"
                )}
              >
                {bid.status.charAt(0).toUpperCase() + bid.status.slice(1)}
              </span>

              <div className="flex gap-2">
                {bid.status === "draft" && (
                  <Button
                    size="sm"
                    onClick={() => updateStatusMutation.mutate("reviewing")}
                    disabled={updateStatusMutation.isPending}
                  >
                    {updateStatusMutation.isPending ? "Updating…" : "Submit for Review"}
                  </Button>
                )}

                {bid.status === "reviewing" && (
                  <Button
                    size="sm"
                    onClick={() => updateStatusMutation.mutate("submitted")}
                    disabled={updateStatusMutation.isPending}
                  >
                    {updateStatusMutation.isPending ? "Updating…" : "Mark as Submitted"}
                  </Button>
                )}

                {bid.status === "submitted" && (
                  <Button
                    size="sm"
                    onClick={() => setShowOutcomeModal(true)}
                  >
                    Record Outcome
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Bid Content Sections */}
        <div className="space-y-4">
          <BidSection title="Executive Summary" content={bid.executive_summary} />
          <BidSection title="Technical Approach" content={bid.technical_approach} />
          <BidSection title="Financial Proposal" content={bid.financial_proposal} />
          <BidSection title="Compliance Statement" content={bid.compliance_statement} />

          {!bid.executive_summary && !bid.technical_approach && !bid.financial_proposal && (
            <div className="bg-white rounded-xl border border-dashed border-gray-300 p-12 text-center">
              <div className="text-3xl mb-3">📄</div>
              <p className="text-gray-500 text-sm">No bid content generated yet.</p>
            </div>
          )}
        </div>
      </div>

      <OutcomeModal
        isOpen={showOutcomeModal}
        onClose={() => setShowOutcomeModal(false)}
        onSubmit={(outcome, ourPrice, winningPrice) =>
          recordOutcomeMutation.mutate({ outcome, our_price: ourPrice, winning_price: winningPrice })
        }
        loading={recordOutcomeMutation.isPending}
      />
    </div>
  );
}
