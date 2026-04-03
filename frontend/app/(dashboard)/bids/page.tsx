"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { MessageLoading } from "@/components/ui/message-loading";
import { api } from "@/lib/api";
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

interface BidListResponse {
  bids: Bid[];
  total: number;
  page: number;
  limit: number;
}

const statusColors = {
  draft: "bg-gray-100 text-gray-800",
  reviewing: "bg-yellow-100 text-yellow-800",
  submitted: "bg-blue-100 text-blue-800",
  won: "bg-green-100 text-green-800",
  lost: "bg-red-100 text-red-800",
  withdrawn: "bg-gray-100 text-gray-600"
};

export default function BidsPage() {
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const { data: bidsData, isLoading, error } = useQuery<BidListResponse>({
    queryKey: ["bids", statusFilter],
    queryFn: () => api.bids.list({ status: statusFilter === "all" ? undefined : statusFilter as any })
  });

  const handleViewBid = (bidId: string) => {
    window.location.href = `/bids/${bidId}`;
  };

  const handleBidRowClick = (bidId: string) => {
    window.location.href = `/bids/${bidId}`;
  };

  const getStatusText = (status: string) => {
    return status.charAt(0).toUpperCase() + status.slice(1);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(
      "en-IN",
      { 
        year: "numeric", 
        month: "short", 
        day: "numeric" 
      }
    );
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="flex items-center justify-center py-12">
            <MessageLoading />
            <span className="ml-2 text-gray-600">Loading bids...</span>
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
            <p className="text-red-600 mb-4">Error loading bids</p>
            <Button onClick={() => window.location.reload()}>Retry</Button>
          </div>
        </div>
      </div>
    );
  }

  const bids = bidsData?.bids || [];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">
            Bids
          </h1>
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
                Total: {bids.length} bids
              </div>
            </div>
          </div>

          <div className="divide-y divide-gray-200">
            {bids.length === 0 ? (
              <div className="p-12 text-center">
                <p className="text-gray-600 mb-4">
                  {statusFilter === "all" 
                    ? "No bids found" 
                    : "No bids found with this filter"
                  }
                </p>
                <Button onClick={() => window.location.href = "/tenders"}>
                  View Tenders
                </Button>
              </div>
            ) : (
              bids.map((bid) => (
                <div
                  key={bid.id}
                  className="p-6 hover:bg-gray-50 transition-colors cursor-pointer"
                  onClick={() => window.location.href = `/bids/${bid.id}`}
                >
                  <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                    <div className="flex-1">
                      <h3 className="text-lg font-medium text-gray-900 mb-2">
                        {bid.tender_title}
                      </h3>
                      <div className="flex flex-wrap gap-4 text-sm text-gray-600">
                        <span>
                          Created: {formatDate(bid.created_at)}
                        </span>
                        <span>
                          Updated: {formatDate(bid.updated_at)}
                        </span>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-3">
                      <span
                        className={cn(
                          "px-3 py-1 rounded-full text-sm font-medium",
                          statusColors[bid.status]
                        )}
                      >
                        {getStatusText(bid.status)}
                      </span>
                      
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleViewBid(bid.id)}
                      >
                        View
                      </Button>
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
