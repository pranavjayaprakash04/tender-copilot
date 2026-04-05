"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useLang } from "@/app/(dashboard)/layout";

interface BidDetail {
  id: string;
  tender_id: string;
  title: string;
  bid_number: string;
  status: string;
  bid_amount?: number;
  emd_amount?: number;
  submission_deadline?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
  can_edit?: boolean;
  can_submit?: boolean;
  can_withdraw?: boolean;
}

const statusColors: Record<string, string> = {
  draft:            "bg-gray-100 text-gray-800",
  reviewing:        "bg-yellow-100 text-yellow-800",
  submitted:        "bg-blue-100 text-blue-800",
  under_evaluation: "bg-purple-100 text-purple-800",
  won:              "bg-green-100 text-green-800",
  lost:             "bg-red-100 text-red-800",
  withdrawn:        "bg-gray-100 text-gray-600",
  on_hold:          "bg-orange-100 text-orange-800",
};

const formatDate = (d?: string | null) => {
  if (!d) return "—";
  const dt = new Date(d);
  if (isNaN(dt.getTime())) return "—";
  return dt.toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" });
};

const formatCurrency = (v?: number | null) => {
  if (v == null) return "—";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(v);
};

export default function BidDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { t } = useLang();
  const qc = useQueryClient();
  const bidId = params?.id;

  const { data: rawData, isLoading, error } = useQuery({
    queryKey: ["bid", bidId],
    queryFn: () => api.bids.get(bidId!),
    enabled: !!bidId,
  });

  const bid: BidDetail | null = rawData
    ? ((rawData as any).data ?? rawData) as BidDetail
    : null;

  const transitionMutation = useMutation({
    mutationFn: (newStatus: string) =>
      api.bids.transition(bidId!, newStatus),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bid", bidId] });
      qc.invalidateQueries({ queryKey: ["bids"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.bids.delete(bidId!),
    onSuccess: () => router.push("/bids"),
  });

  if (!bidId) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <p className="text-gray-600">Invalid bid ID</p>
    </div>
  );

  if (isLoading) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <p className="text-gray-600">Loading bid...</p>
    </div>
  );

  if (error || !bid) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <p className="text-red-600 mb-4">Failed to load bid</p>
        <Button onClick={() => router.back()}>Go Back</Button>
      </div>
    </div>
  );

  const statusLabel = bid.status.charAt(0).toUpperCase() + bid.status.slice(1).replace("_", " ");

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <button onClick={() => router.back()} className="text-sm text-gray-500 hover:text-gray-700 mb-6 flex items-center gap-1">
          ← Back to Bids
        </button>

        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-gray-900 mb-1">{bid.title || "Untitled Bid"}</h1>
              <p className="text-gray-500 text-sm">Bid #{bid.bid_number}</p>
            </div>
            <span className={cn("px-3 py-1 rounded-full text-sm font-medium self-start", statusColors[bid.status] ?? "bg-gray-100 text-gray-800")}>
              {statusLabel}
            </span>
          </div>
        </div>

        {/* Key Details */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Bid Details</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
            <div><p className="text-gray-500">Bid Amount</p><p className="font-semibold text-gray-900">{formatCurrency(bid.bid_amount)}</p></div>
            <div><p className="text-gray-500">EMD Amount</p><p className="font-medium text-gray-900">{formatCurrency(bid.emd_amount)}</p></div>
            <div><p className="text-gray-500">Submission Deadline</p><p className="font-medium text-gray-900">{formatDate(bid.submission_deadline)}</p></div>
            <div><p className="text-gray-500">Created</p><p className="font-medium text-gray-900">{formatDate(bid.created_at)}</p></div>
            <div><p className="text-gray-500">Last Updated</p><p className="font-medium text-gray-900">{formatDate(bid.updated_at)}</p></div>
            <div><p className="text-gray-500">Status</p><p className="font-medium text-gray-900">{statusLabel}</p></div>
          </div>
          {bid.notes && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <p className="text-gray-500 text-sm mb-1">Notes</p>
              <p className="text-gray-700 text-sm">{bid.notes}</p>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Actions</h2>
          <div className="flex flex-wrap gap-3">

            {/* Status transitions */}
            {bid.status === "draft" && (
              <button onClick={() => transitionMutation.mutate("reviewing")} disabled={transitionMutation.isPending}
                className="px-4 py-2 rounded-md text-sm font-medium bg-yellow-500 hover:bg-yellow-600 text-white disabled:opacity-50">
                Move to Reviewing
              </button>
            )}
            {bid.status === "reviewing" && (
              <button onClick={() => transitionMutation.mutate("submitted")} disabled={transitionMutation.isPending}
                className="px-4 py-2 rounded-md text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50">
                Mark as Submitted
              </button>
            )}
            {bid.status === "submitted" && (
              <button onClick={() => transitionMutation.mutate("under_evaluation")} disabled={transitionMutation.isPending}
                className="px-4 py-2 rounded-md text-sm font-medium bg-purple-600 hover:bg-purple-700 text-white disabled:opacity-50">
                Under Evaluation
              </button>
            )}
            {bid.status === "under_evaluation" && (
              <>
                <button onClick={() => transitionMutation.mutate("won")} disabled={transitionMutation.isPending}
                  className="px-4 py-2 rounded-md text-sm font-medium bg-green-600 hover:bg-green-700 text-white disabled:opacity-50">
                  🎉 Mark as Won
                </button>
                <button onClick={() => transitionMutation.mutate("lost")} disabled={transitionMutation.isPending}
                  className="px-4 py-2 rounded-md text-sm font-medium bg-red-600 hover:bg-red-700 text-white disabled:opacity-50">
                  Mark as Lost
                </button>
              </>
            )}
            {["draft", "reviewing", "submitted"].includes(bid.status) && (
              <button onClick={() => transitionMutation.mutate("withdrawn")} disabled={transitionMutation.isPending}
                className="px-4 py-2 rounded-md text-sm font-medium border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50">
                Withdraw
              </button>
            )}

            {/* Go to tender */}
            {bid.tender_id && (
              <button onClick={() => router.push(`/tenders/${bid.tender_id}`)}
                className="px-4 py-2 rounded-md text-sm font-medium border border-gray-300 text-gray-700 hover:bg-gray-50">
                View Tender
              </button>
            )}

            {/* Delete draft */}
            {bid.status === "draft" && (
              <button onClick={() => { if (confirm("Delete this bid?")) deleteMutation.mutate(); }}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 rounded-md text-sm font-medium border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-50">
                {deleteMutation.isPending ? t("Deleting...","நீக்குகிறது...") : t("Delete","நீக்கு")}
              </button>
            )}

            {transitionMutation.isError && (
              <p className="text-red-600 text-sm w-full">Transition failed. Please try again.</p>
            )}
            {transitionMutation.isSuccess && (
              <p className="text-green-600 text-sm w-full">✓ Status updated successfully</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
