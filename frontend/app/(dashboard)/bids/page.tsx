"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Bid {
  id: string;
  tender_id: string;
  tender_title: string;
  organisation: string;
  status: "active" | "closing_soon" | "closed";
  posted_date: string;
  deadline: string;
  estimated_value: number | null;
  location: string | null;
}

interface BidListResponse {
  bids: Bid[];
  total: number;
  page: number;
  limit: number;
}

const statusColors: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  closing_soon: "bg-yellow-100 text-yellow-800",
  closed: "bg-gray-100 text-gray-600",
};

const statusLabels: Record<string, string> = {
  all: "All",
  active: "Active",
  closing_soon: "Closing Soon",
  closed: "Closed",
};

export default function BidsPage() {
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const params = statusFilter === "all" ? {} : { status: statusFilter };

  const { data: bidsData, isLoading, error, refetch } = useQuery<BidListResponse>({
    queryKey: ["bids", statusFilter],
    queryFn: () => api.bids.list(params),
  });

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return "—";
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleDateString("en-IN", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const formatCurrency = (value: number | null | undefined) => {
    if (!value) return null;
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(value);
  };

  const bids = bidsData?.bids || [];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Bids Pipeline</h1>
        </div>

        {isLoading ? (
          <div className="text-center py-12 text-gray-600">Loading bids...</div>
        ) : error ? (
          <div className="text-center py-12">
            <p className="text-red-600 mb-4">Error loading bids</p>
            <Button onClick={() => refetch()}>Retry</Button>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
                <div className="flex flex-wrap gap-2">
                  {["all", "active", "closing_soon", "closed"].map((status) => (
                    <Button
                      key={status}
                      variant={statusFilter === status ? "default" : "outline"}
                      size="sm"
                      onClick={() => setStatusFilter(status)}
                    >
                      {statusLabels[status]}
                    </Button>
                  ))}
                </div>
                <div className="text-sm text-gray-600">
                  Total: {bidsData?.total ?? bids.length} bids
                </div>
              </div>
            </div>

            <div className="divide-y divide-gray-200">
              {bids.length === 0 ? (
                <div className="p-12 text-center">
                  <p className="text-gray-600 mb-4">
                    {statusFilter === "all"
                      ? "No bids found"
                      : `No ${statusLabels[statusFilter].toLowerCase()} bids`}
                  </p>
                  <Button onClick={() => { window.location.href = "/tenders"; }}>
                    View Tenders
                  </Button>
                </div>
              ) : (
                bids.map((bid) => (
                  <div
                    key={bid.id}
                    className="p-6 hover:bg-gray-50 transition-colors cursor-pointer"
                    onClick={() => { window.location.href = `/tenders/${bid.tender_id || bid.id}`; }}
                  >
                    <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-medium text-gray-900 mb-1 truncate">
                          {bid.tender_title}
                        </h3>
                        <p className="text-sm text-gray-500 mb-2">{bid.organisation}</p>
                        <div className="flex flex-wrap gap-4 text-sm text-gray-600">
                          <span>Posted: {formatDate(bid.posted_date)}</span>
                          <span>Deadline: {formatDate(bid.deadline)}</span>
                          {bid.location && <span>📍 {bid.location}</span>}
                          {bid.estimated_value && (
                            <span className="font-medium text-gray-800">
                              {formatCurrency(bid.estimated_value)}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        <span
                          className={cn(
                            "px-3 py-1 rounded-full text-sm font-medium",
                            statusColors[bid.status] ?? "bg-gray-100 text-gray-600"
                          )}
                        >
                          {statusLabels[bid.status] ?? bid.status}
                        </span>
                        <button
                          className="px-3 py-1 text-sm border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
                          onClick={(e) => {
                            e.stopPropagation();
                            window.location.href = `/tenders/${bid.tender_id || bid.id}`;
                          }}
                        >
                          View
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
