"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "next-i18next";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Tender {
  id: string;
  title: string;
  department: string;
  value: number;
  deadline: string;
  category: string;
  state: string;
  match_score: number;
}

interface TenderListParams {
  category?: string;
  state?: string;
  deadline?: string;
  search?: string;
}

interface TenderListResponse {
  tenders: Tender[];
  total: number;
  page: number;
  limit: number;
}

export default function TendersPage() {
  const { t, i18n } = useTranslation("common");
  const [filters, setFilters] = useState<TenderListParams>({
    category: "",
    state: "",
    deadline: "",
    search: ""
  });

  const { data: tendersData, isLoading, error } = useQuery<TenderListResponse>({
    queryKey: ["tenders", filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
      });
      const response = await fetch(`/api/tenders?${params}`);
      if (!response.ok) throw new Error("Failed to fetch tenders");
      return response.json();
    }
  });

  const getMatchScoreColor = (score: number) => {
    if (score >= 80) return "bg-green-100 text-green-800";
    if (score >= 60) return "bg-yellow-100 text-yellow-800";
    if (score >= 40) return "bg-orange-100 text-orange-800";
    return "bg-red-100 text-red-800";
  };

  const getDeadlineColor = (deadline: string) => {
    const days = Math.ceil((new Date(deadline).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24));
    if (days <= 3) return "text-red-600";
    if (days <= 7) return "text-orange-600";
    return "text-green-600";
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
          <h1 className="text-3xl font-bold text-gray-900 mb-6">{t("tenders.title")}</h1>
          
          {/* Search and Filters */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
              <input
                type="text"
                placeholder={t("tenders.search_placeholder")}
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <select
                value={filters.category}
                onChange={(e) => setFilters({ ...filters, category: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">{t("tenders.all_categories")}</option>
                <option value="construction">{t("tenders.construction")}</option>
                <option value="it">{t("tenders.it")}</option>
                <option value="transport">{t("tenders.transport")}</option>
              </select>
              <select
                value={filters.state}
                onChange={(e) => setFilters({ ...filters, state: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">{t("tenders.all_states")}</option>
                <option value="tamil-nadu">{t("tenders.tamil_nadu")}</option>
                <option value="karnataka">{t("tenders.karnataka")}</option>
                <option value="maharashtra">{t("tenders.maharashtra")}</option>
              </select>
              <select
                value={filters.deadline}
                onChange={(e) => setFilters({ ...filters, deadline: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">{t("tenders.all_deadlines")}</option>
                <option value="3">{t("tenders.next_3_days")}</option>
                <option value="7">{t("tenders.next_7_days")}</option>
                <option value="30">{t("tenders.next_30_days")}</option>
              </select>
            </div>
            <Button onClick={() => setFilters({ search: "", category: "", state: "", deadline: "" })}>
              {t("tenders.clear_filters")}
            </Button>
          </div>
        </div>

        {/* Tender Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {isLoading ? (
            Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)
          ) : error ? (
            <div className="col-span-full text-center py-12">
              <p className="text-red-600 mb-4">{t("tenders.error_loading")}</p>
              <Button onClick={() => window.location.reload()}>{t("tenders.retry")}</Button>
            </div>
          ) : tendersData?.tenders.length === 0 ? (
            <div className="col-span-full text-center py-12">
              <p className="text-gray-600">{t("tenders.no_tenders")}</p>
            </div>
          ) : (
            tendersData?.tenders.map((tender) => (
              <div key={tender.id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">{tender.title}</h3>
                <p className="text-gray-600 mb-2">{tender.department}</p>
                <p className="text-lg font-medium text-gray-900 mb-4">₹{tender.value.toLocaleString("en-IN")}</p>
                
                <div className="flex justify-between items-center mb-4">
                  <span className={cn(
                    "px-2 py-1 rounded-full text-xs font-medium",
                    getMatchScoreColor(tender.match_score)
                  )}>
                    {t("tenders.match_score")}: {tender.match_score}%
                  </span>
                  <span className={cn(
                    "text-sm font-medium",
                    getDeadlineColor(tender.deadline)
                  )}>
                    {new Date(tender.deadline).toLocaleDateString(i18n.language === "ta" ? "ta-IN" : "en-IN")}
                  </span>
                </div>
                
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => window.location.href = `/tenders/${tender.id}`}>
                    {t("tenders.view_details")}
                  </Button>
                  <Button size="sm" variant="outline">
                    {t("tenders.set_alert")}
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
