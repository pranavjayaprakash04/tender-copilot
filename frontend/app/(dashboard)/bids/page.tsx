"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useLang } from "@/app/(dashboard)/layout";
import { cn } from "@/lib/utils";

interface Bid {
  id: string;
  tender_id: string;
  tender_title: string;
  company_id: string;
  status: "draft" | "reviewing" | "submitted" | "won" | "lost" | "withdrawn";
  created_at: string;
  updated_at: string;
}

const statusColors: Record<string, string> = {
  draft: "bg-gray-100 text-gray-800",
  reviewing: "bg-yellow-100 text-yellow-800",
  submitted: "bg-blue-100 text-blue-800",
  won: "bg-green-100 text-green-800",
  lost: "bg-red-100 text-red-800",
  withdrawn: "bg-gray-100 text-gray-600"
};

export default function BidsPage() {
  const { t } = useLang();
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const { data: bidsData, isLoading, error } = useQuery({
    queryKey: ["bids", statusFilter],
    queryFn: () =>
      api.bids.list({
        status: statusFilter === "all" ? undefined : statusFilter,
      }),
  });

  const getStatusText = (status: string) =>
    status.charAt(0).toUpperCase() + status.slice(1);

  const formatDate = (dateString: string) => {
    if (!dateString) return "—";
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleDateString("en-IN", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const bids: Bid[] = bidsData?.bids ?? bidsData?.items ?? [];

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="flex items-center justify-center py-12">
            <span className="text-gray-600">{t("Loading bids...","ஒப்பந்தங்கள் ஏற்றுகிறது...")}</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="text-center py-12">
            <p className="text-red-600 mb-4">Error loading bids. Please try again.</p>
            <Button onClick={() => window.location.reload()}>Retry</Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Bids</h1>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="p-6 border-b border-gray-200">
            <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
              <div className="flex flex-wrap gap-2">
                <Button
                  variant={statusFilter === "all" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setStatusFilter("all")}
                >
                  All
                </Button>
                {["draft", "reviewing", "submitted", "won", "lost", "withdrawn"].map((status) => (
                  <Button
                    key={status}
                    variant={statusFilter === status ? "default" : "outline"}
                    size="sm"
                    onClick={() => setStatusFilter(status)}
                  >
                    {getStatusText(status)}
                  </Button>
                ))}
              </div>
              <div className="text-sm text-gray-600">
                {t("Total","மொத்தம்")}: {bids.length} {t("bids","ஒப்பந்தங்கள்")}
              </div>
            </div>
          </div>

          <div className="divide-y divide-gray-200">
            {bids.length === 0 ? (
              <div className="p-12 text-center">
                <p className="text-gray-600 mb-4">
                  {statusFilter === "all"
                    ? t("No bids yet. Find a tender and start bidding!","இன்னும் ஒப்பந்தங்கள் இல்லை. ஒரு டெண்டர் கண்டுபிடித்து தொடங்குங்கள்!")
                    : `${t("No","இல்லை")} ${statusFilter} ${t("bids found","ஒப்பந்தங்கள் இல்லை")}.`}
                </p>
                <Button onClick={() => (window.location.href = "/tenders")}>
                  Browse Tenders
                </Button>
              </div>
            ) : (
              bids.map((bid) => (
                <div
                  key={bid.id}
                  className="p-6 hover:bg-gray-50 transition-colors cursor-pointer"
                  onClick={() => (window.location.href = `/bids/${bid.id}`)}
                >
                  <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                    <div className="flex-1">
                      <h3 className="text-lg font-medium text-gray-900 mb-2">
                        {bid.tender_title || "Untitled Bid"}
                      </h3>
                      <div className="flex flex-wrap gap-4 text-sm text-gray-600">
                        <span>Created: {formatDate(bid.created_at)}</span>
                        <span>Updated: {formatDate(bid.updated_at)}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span
                        className={cn(
                          "px-3 py-1 rounded-full text-sm font-medium",
                          statusColors[bid.status] ?? "bg-gray-100 text-gray-800"
                        )}
                      >
                        {getStatusText(bid.status)}
                      </span>
                      <div onClick={(e) => e.stopPropagation()}>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => (window.location.href = `/bids/${bid.id}`)}
                        >
                          View
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
