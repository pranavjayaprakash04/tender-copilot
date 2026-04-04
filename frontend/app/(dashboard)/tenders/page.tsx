"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Tender {
  id: string;
  title: string;
  description: string;
  procuring_entity: string;
  bid_submission_deadline: string;
  estimated_value?: number;
  emd_amount?: number;
  category: string;
  status: string;
  state?: string;
  district?: string;
  match_score?: number;
  days_until_deadline?: number;
  is_urgent?: boolean;
  is_closing_soon?: boolean;
}

interface TenderListParams {
  [key: string]: string | undefined;
  category?: string;
  state?: string;
  deadline?: string;
  search?: string;
}

interface TenderListResponse {
  tenders: Tender[];
  total: number;
  page?: number;
  page_size?: number;
}

function safeFormatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "No deadline";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return "No deadline";
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

function deadlineColor(dateStr: string | null | undefined, isUrgent?: boolean, isClosingSoon?: boolean): string {
  if (isUrgent) return "text-red-600";
  if (isClosingSoon) return "text-orange-600";
  if (!dateStr) return "text-gray-500";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return "text-gray-500";
  const days = Math.ceil((d.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
  if (days <= 3) return "text-red-600";
  if (days <= 7) return "text-orange-600";
  return "text-green-600";
}

export default function TendersPage() {
  const [filters, setFilters] = useState<TenderListParams>({
    category: "",
    state: "",
    deadline: "",
    search: ""
  });

  const { data: tendersData, isLoading, error } = useQuery<TenderListResponse>({
    queryKey: ["tenders", filters],
    queryFn: async () => {
      return api.tenders.search(filters) as unknown as TenderListResponse;
    }
  });

  const SkeletonCard = () => (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 animate-pulse">
      <div className="h-6 bg-gray-200 rounded mb-4 w-3/4"></div>
      <div className="h-4 bg-gray-200 rounded mb-2 w-1/2"></div>
      <div className="h-4 bg-gray-200 rounded mb-4 w-1/3"></div>
      <div className="flex justify-between items-center">
        <div className="h-8 bg-gray-200 rounded w-20"></div>
        <div className="h-8 bg-gray-200 rounded w-24"></div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-6">Tenders</h1>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
              <input
                type="text"
                placeholder="Search tenders..."
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <select
                value={filters.category}
                onChange={(e) => setFilters({ ...filters, category: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Categories</option>
                <option value="construction">Construction</option>
                <option value="it">IT</option>
                <option value="transport">Transport</option>
              </select>
              <select
                value={filters.state}
                onChange={(e) => setFilters({ ...filters, state: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All States</option>
                <option value="tamil_nadu">Tamil Nadu</option>
                <option value="karnataka">Karnataka</option>
                <option value="maharashtra">Maharashtra</option>
              </select>
              <select
                value={filters.deadline}
                onChange={(e) => setFilters({ ...filters, deadline: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Deadlines</option>
                <option value="3">Next 3 Days</option>
                <option value="7">Next 7 Days</option>
                <option value="30">Next 30 Days</option>
              </select>
            </div>
            <Button onClick={() => setFilters({ search: "", category: "", state: "", deadline: "" })}>
              Clear Filters
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {isLoading ? (
            Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)
          ) : error ? (
            <div className="col-span-full text-center py-12">
              <p className="text-red-600 mb-4">Error loading tenders</p>
              <Button onClick={() => window.location.reload()}>Retry</Button>
            </div>
          ) : !tendersData?.tenders || tendersData.tenders.length === 0 ? (
            <div className="col-span-full text-center py-12">
              <p className="text-gray-600">No tenders found</p>
            </div>
          ) : (
            tendersData.tenders.map((tender: Tender) => (
              <div key={tender.id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
                <h3 className="text-base font-semibold text-gray-900 mb-2 line-clamp-2">{tender.title}</h3>
                <p className="text-gray-500 text-sm mb-1">{tender.procuring_entity}</p>
                {tender.state && (
                  <p className="text-gray-400 text-xs mb-2">{tender.district ? `${tender.district}, ` : ""}{tender.state}</p>
                )}
                <p className="text-base font-medium text-gray-900 mb-4">
                  {tender.estimated_value && tender.estimated_value > 0
                    ? `₹${tender.estimated_value.toLocaleString("en-IN")}`
                    : tender.emd_amount && tender.emd_amount > 0
                    ? `EMD: ₹${tender.emd_amount.toLocaleString("en-IN")}`
                    : "Value not disclosed"}
                </p>

                <div className="flex justify-between items-center mb-4">
                  {tender.match_score && tender.match_score > 0 ? (
                    <span className={cn(
                      "px-2 py-1 rounded-full text-xs font-medium",
                      tender.match_score >= 80 ? "bg-green-100 text-green-800" :
                      tender.match_score >= 60 ? "bg-yellow-100 text-yellow-800" :
                      "bg-orange-100 text-orange-800"
                    )}>
                      Match: {tender.match_score}%
                    </span>
                  ) : (
                    <span className="text-xs text-gray-400">Set profile for match score</span>
                  )}
                  <span className={cn("text-sm font-medium", deadlineColor(tender.bid_submission_deadline, tender.is_urgent, tender.is_closing_soon))}>
                    {safeFormatDate(tender.bid_submission_deadline)}
                  </span>
                </div>

                {tender.days_until_deadline !== undefined && tender.days_until_deadline > 0 && (
                  <p className="text-xs text-gray-400 mb-3">{tender.days_until_deadline} days left</p>
                )}

                <div className="flex gap-2">
                  <Button size="sm" onClick={() => window.location.href = `/tenders/${tender.id}`}>
                    View Details
                  </Button>
                  <Button size="sm" variant="outline">
                    Set Alert
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>

        {tendersData?.total && tendersData.total > 0 && (
          <p className="text-center text-sm text-gray-500 mt-6">
            Showing {tendersData.tenders?.length || 0} of {tendersData.total} tenders
          </p>
        )}
      </div>
    </div>
  );
}
