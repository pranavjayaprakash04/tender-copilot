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
  organization: string;
  deadline: string;
  value?: string;
  category: string;
  status: 'active' | 'closed' | 'cancelled';
  posted_date: string;
  source_url: string;
  department?: string;
  authority?: string;
  state?: string;
  requirements?: string[];
  match_score?: number;
  classification?: {
    relevance_score: number;
    category: string;
    keywords: string[];
  };
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
  limit?: number;
}

function safeFormatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "No deadline";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return "No deadline";
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

function safeDeadlineColor(dateStr: string | null | undefined): string {
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

  const getMatchScoreColor = (score: number) => {
    if (score >= 80) return "bg-green-100 text-green-800";
    if (score >= 60) return "bg-yellow-100 text-yellow-800";
    if (score >= 40) return "bg-orange-100 text-orange-800";
    return "bg-red-100 text-red-800";
  };

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
          
          {/* Search and Filters */}
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
                <option value="tamil-nadu">Tamil Nadu</option>
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

        {/* Tender Cards */}
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
                <h3 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">{tender.title}</h3>
                <p className="text-gray-600 text-sm mb-2">{tender.department || tender.authority || tender.organization}</p>
                <p className="text-base font-medium text-gray-900 mb-4">
                  {tender.value ? `₹${parseInt(tender.value).toLocaleString("en-IN")}` : "Value not specified"}
                </p>
                
                <div className="flex justify-between items-center mb-4">
                  {tender.match_score && tender.match_score > 0 ? (
                    <span className={cn(
                      "px-2 py-1 rounded-full text-xs font-medium",
                      getMatchScoreColor(tender.match_score)
                    )}>
                      Match: {tender.match_score}%
                    </span>
                  ) : (
                    <span className="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-500">
                      Complete profile for match score
                    </span>
                  )}
                  <span className={cn("text-sm font-medium", safeDeadlineColor(tender.deadline))}>
                    {safeFormatDate(tender.deadline)}
                  </span>
                </div>
                
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
