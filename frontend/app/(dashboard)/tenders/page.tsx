"use client";

import { useState, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

// Matches backend TenderResponse field names exactly
interface Tender {
  id: string;
  tender_id: string;
  title: string;
  description: string;
  procuring_entity: string;         // was: organization
  bid_submission_deadline: string | null; // was: deadline
  estimated_value?: number | null;  // was: value (and is number, not string)
  emd_amount?: number | null;
  category: string | null;
  status: string;
  published_date: string | null;    // was: posted_date
  source_url: string | null;
  state?: string | null;
  match_score?: number | null;
}

interface TenderListParams {
  category?: string;
  state?: string;
  deadline?: string;   // mapped to deadline_days in api.ts
  search?: string;     // mapped to search_query in api.ts
}

// Outside component — not recreated on every render
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

const getDeadlineColor = (deadline: string | null | undefined) => {
  if (!deadline) return "text-gray-400";
  const d = new Date(deadline);
  if (isNaN(d.getTime())) return "text-gray-400";
  const days = Math.ceil((d.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
  if (days <= 3) return "text-red-600";
  if (days <= 7) return "text-orange-600";
  return "text-green-600";
};

const formatDeadline = (deadline: string | null | undefined) => {
  if (!deadline) return "—";
  const d = new Date(deadline);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" });
};

const formatValue = (value: number | null | undefined) => {
  if (value === null || value === undefined) return "Value not specified";
  return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
};

const getMatchScoreColor = (score: number) => {
  if (score >= 80) return "bg-green-100 text-green-800";
  if (score >= 60) return "bg-yellow-100 text-yellow-800";
  if (score >= 40) return "bg-orange-100 text-orange-800";
  return "bg-red-100 text-red-800";
};

export default function TendersPage() {
  const router = useRouter();

  const [filters, setFilters] = useState<TenderListParams>({
    category: "",
    state: "",
    deadline: "",
    search: "",
  });

  // Debounced search — only fires API call 400ms after user stops typing
  const [debouncedSearch, setDebouncedSearch] = useState("");
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(filters.search || ""), 400);
    return () => clearTimeout(timer);
  }, [filters.search]);

  // Strip empty values; use debounced search
  const activeFilters = Object.fromEntries(
    Object.entries({ ...filters, search: debouncedSearch }).filter(([_, v]) => v !== "")
  );

  const { data: tenders, isLoading, error, refetch } = useQuery<Tender[]>({
    queryKey: ["tenders", activeFilters],
    queryFn: () => api.tenders.search(activeFilters),
    staleTime: 60_000,
  });

  const clearFilters = useCallback(() => {
    setFilters({ search: "", category: "", state: "", deadline: "" });
    setDebouncedSearch("");
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Tenders</h1>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <input
              type="text"
              placeholder="Search tenders..."
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {/* Category values match exactly what's stored in the DB */}
            <select
              value={filters.category}
              onChange={(e) => setFilters({ ...filters, category: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Categories</option>
              <option value="Works">Works</option>
              <option value="Goods">Goods</option>
              <option value="Services">Services</option>
            </select>
            <select
              value={filters.state}
              onChange={(e) => setFilters({ ...filters, state: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All States</option>
              <option value="Tamil Nadu">Tamil Nadu</option>
              <option value="Karnataka">Karnataka</option>
              <option value="Maharashtra">Maharashtra</option>
              <option value="Andhra Pradesh">Andhra Pradesh</option>
              <option value="Telangana">Telangana</option>
              <option value="Kerala">Kerala</option>
              <option value="Delhi">Delhi</option>
              <option value="Uttar Pradesh">Uttar Pradesh</option>
              <option value="Rajasthan">Rajasthan</option>
              <option value="Gujarat">Gujarat</option>
              <option value="West Bengal">West Bengal</option>
              <option value="Madhya Pradesh">Madhya Pradesh</option>
              <option value="Punjab">Punjab</option>
              <option value="Haryana">Haryana</option>
              <option value="Odisha">Odisha</option>
              <option value="Bihar">Bihar</option>
              <option value="Jharkhand">Jharkhand</option>
              <option value="Chhattisgarh">Chhattisgarh</option>
              <option value="Assam">Assam</option>
              <option value="Himachal Pradesh">Himachal Pradesh</option>
              <option value="Uttarakhand">Uttarakhand</option>
              <option value="Goa">Goa</option>
              <option value="Jammu and Kashmir">Jammu and Kashmir</option>
            </select>
            {/* deadline value is sent as deadline_days (number of days) via api.ts mapper */}
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
          <Button onClick={clearFilters}>Clear Filters</Button>
        </div>

        {/* Tender Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {isLoading ? (
            Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)
          ) : error ? (
            <div className="col-span-full text-center py-12">
              <p className="text-red-600 mb-4">Error loading tenders</p>
              <Button onClick={() => refetch()}>Retry</Button>
            </div>
          ) : !tenders || tenders.length === 0 ? (
            <div className="col-span-full text-center py-12">
              <p className="text-gray-600">No tenders found matching your filters</p>
            </div>
          ) : (
            tenders.map((tender) => (
              <div
                key={tender.id}
                className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
              >
                <h3 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">
                  {tender.title}
                </h3>
                {/* procuring_entity replaces organization */}
                <p className="text-gray-600 mb-2 truncate">{tender.procuring_entity}</p>
                {/* estimated_value is now a number */}
                <p className="text-lg font-medium text-gray-900 mb-4">
                  {formatValue(tender.estimated_value)}
                </p>
                <div className="flex justify-between items-center mb-4">
                  <span className={cn(
                    "px-2 py-1 rounded-full text-xs font-medium",
                    getMatchScoreColor(tender.match_score || 0)
                  )}>
                    Match: {tender.match_score || 0}%
                  </span>
                  {/* bid_submission_deadline replaces deadline */}
                  <span className={cn("text-sm font-medium", getDeadlineColor(tender.bid_submission_deadline))}>
                    {formatDeadline(tender.bid_submission_deadline)}
                  </span>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => router.push(`/tenders/${tender.id}`)}>
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
      </div>
    </div>
  );
}
