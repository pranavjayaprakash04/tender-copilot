"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useLang } from "@/app/(dashboard)/layout";
import { cn } from "@/lib/utils";

function computeMatchScore(tender: Tender, profile: any): number | null {
  if (!profile) return null;
  const cat = ((tender.category || "") + " " + (tender.title || "")).toLowerCase();
  const loc = (tender.state || "").toLowerCase();
  const industry = (profile?.industry || "").toLowerCase();
  const location = (profile?.location || "").toLowerCase();
  const caps = (profile?.capabilities_text || "").toLowerCase();

  let score = 30;

  const itKw = ["it", "software", "tech", "digital", "computer", "ai", "cloud", "data", "web"];
  const isIT = itKw.some((k: string) => industry.includes(k) || caps.includes(k));
  const catIsIT = itKw.some((k: string) => cat.includes(k));
  const catIsServices = ["service", "consult", "support", "manag"].some((k: string) => cat.includes(k));

  if (isIT && catIsIT) score += 40;
  else if (isIT && catIsServices) score += 25;
  else if (isIT) score -= 10;
  else score += 20;

  if (location) {
    const locParts = location.toLowerCase().split(/[\s,/]+/).filter((w: string) => w.length > 2);
    if (locParts.some((w: string) => loc.includes(w))) score += 20;
    else score += 5;
  } else {
    score += 10;
  }

  if (caps) {
    const capKw = caps.split(/[\s,]+/).filter((w: string) => w.length > 3);
    const hits = capKw.filter((w: string) => cat.includes(w)).length;
    score += Math.min(hits * 5, 15);
  }

  return Math.max(15, Math.min(score, 97));
}

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

function daysLeft(dateStr: string | null | undefined): number | null {
  if (!dateStr) return null;
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return null;
  return Math.ceil((d.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
}

function deadlineColor(days: number | null): string {
  if (days === null) return "text-gray-400";
  if (days < 0) return "text-gray-400";
  if (days <= 3) return "text-red-600";
  if (days <= 7) return "text-orange-500";
  return "text-green-600";
}

function formatValue(estimated_value?: number, emd_amount?: number): string {
  if (estimated_value && estimated_value > 0)
    return `₹${estimated_value.toLocaleString("en-IN")}`;
  if (emd_amount && emd_amount > 0)
    return `EMD: ₹${emd_amount.toLocaleString("en-IN")}`;
  return "Value not disclosed";
}

export default function TendersPage() {
  const { t, lang } = useLang();
  const [filters, setFilters] = useState<TenderListParams>({
    category: "",
    state: "",
    deadline: "",
    search: "",
  });

  const { data: rawProfile } = useQuery({
    queryKey: ["company-profile"],
    queryFn: () => api.company.getProfile().catch(() => null),
    staleTime: 300_000,
  });
  const profileData = rawProfile ? ((rawProfile as any).data ?? rawProfile) : null;

  const [translations, setTranslations] = useState<Record<string, string>>({});
  const [translatingIds, setTranslatingIds] = useState<Record<string, boolean>>({});

  const translateTender = async (tender: Tender) => {
    if (translations[tender.id] || translatingIds[tender.id]) return;
    setTranslatingIds(prev => ({ ...prev, [tender.id]: true }));
    try {
      const res = await fetch("/api/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: tender.title, target_language: "ta" }),
      });
      if (res.ok) {
        const data = await res.json();
        setTranslations(prev => ({ ...prev, [tender.id]: data.translated }));
      }
    } catch {}
    setTranslatingIds(prev => ({ ...prev, [tender.id]: false }));
  };

  const { data: tendersData, isLoading, error } = useQuery<TenderListResponse>({
    queryKey: ["tenders", filters],
    queryFn: async () => {
      return api.tenders.search(filters) as unknown as TenderListResponse;
    },
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
          <h1 className="text-3xl font-bold text-gray-900 mb-6">{t("Tenders", "டெண்டர்கள்")}</h1>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
              <input
                type="text"
                placeholder={t("Search tenders...", "டெண்டர்களை தேடுங்கள்...")}
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <select
                value={filters.category}
                onChange={(e) => setFilters({ ...filters, category: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">{t("All Categories", "அனைத்து வகைகள்")}</option>
                <option value="Works">Works</option>
                <option value="Goods">Goods</option>
                <option value="Services">Services</option>
              </select>
              <select
                value={filters.state}
                onChange={(e) => setFilters({ ...filters, state: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">{t("All States", "அனைத்து மாநிலங்கள்")}</option>
                <option value="Chennai">Chennai</option>
                <option value="Madurai">Madurai</option>
                <option value="Coimbatore">Coimbatore</option>
                <option value="Vellore">Vellore</option>
                <option value="Mumbai">Mumbai</option>
                <option value="Delhi">Delhi</option>
                <option value="Bangalore">Bangalore</option>
              </select>
              <select
                value={filters.deadline}
                onChange={(e) => setFilters({ ...filters, deadline: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">{t("All Deadlines", "அனைத்து காலக்கெடுகள்")}</option>
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
              <Button onClick={() => window.location.reload()}>{t("Retry", "மீண்டும் முயற்சி")}</Button>
            </div>
          ) : !tendersData?.tenders || tendersData.tenders.length === 0 ? (
            <div className="col-span-full text-center py-12">
              <p className="text-gray-600">{t("No tenders found", "டெண்டர்கள் இல்லை")}</p>
            </div>
          ) : (
            tendersData.tenders.map((tender: Tender) => {
              const days = daysLeft(tender.bid_submission_deadline);
              const isExpired = days !== null && days < 0;
              const score = computeMatchScore(tender, profileData);

              return (
                <div
                  key={tender.id}
                  className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
                >
                  <h3 className="text-base font-semibold text-gray-900 mb-1 line-clamp-2">
                    {translations[tender.id] || tender.title}
                  </h3>
                  {translations[tender.id] && (
                    <p className="text-xs text-gray-400 line-clamp-1 mb-1">{tender.title}</p>
                  )}
                  <p className="text-gray-500 text-sm mb-1">{tender.procuring_entity}</p>
                  {tender.state && (
                    <p className="text-gray-400 text-xs mb-3">
                      {tender.district ? `${tender.district}, ` : ""}{tender.state}
                    </p>
                  )}

                  <p className="text-base font-semibold text-gray-800 mb-4">
                    {formatValue(tender.estimated_value, tender.emd_amount)}
                  </p>

                  <div className="flex justify-between items-center mb-3">
                    {score !== null ? (
                      <span className={cn(
                        "px-2 py-1 rounded-full text-xs font-medium",
                        score >= 70 ? "bg-green-100 text-green-800" :
                        score >= 45 ? "bg-yellow-100 text-yellow-800" :
                        "bg-orange-100 text-orange-800"
                      )}>
                        Match: {score}%
                      </span>
                    ) : (
                      <span className="text-xs text-gray-400">Complete profile for score</span>
                    )}

                    <div className={cn("text-right text-sm font-medium", deadlineColor(days))}>
                      {isExpired ? (
                        <span className="text-gray-400">Expired</span>
                      ) : days === null ? (
                        <span className="text-gray-400">No deadline</span>
                      ) : (
                        <>
                          <span>{safeFormatDate(tender.bid_submission_deadline)}</span>
                          <span className="block text-xs font-normal">
                            {days === 0 ? "Due today" : `${days} day${days === 1 ? "" : "s"} left`}
                          </span>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="flex gap-2 flex-wrap">
                    <Button size="sm" onClick={() => (window.location.href = `/tenders/${tender.id}`)}>
                      {t("View Details", "விவரங்கள் பார்க்க")}
                    </Button>
                    <Button size="sm" variant="outline">
                      {t("Set Alert", "விழிப்பூட்டல் அமை")}
                    </Button>
                    {!translations[tender.id] ? (
                      <button
                        onClick={() => translateTender(tender)}
                        disabled={translatingIds[tender.id]}
                        className="px-2 py-1 text-xs border border-orange-200 text-orange-600 rounded-md hover:bg-orange-50 disabled:opacity-50 transition-colors flex items-center gap-1"
                        title="Translate to Tamil"
                      >
                        {translatingIds[tender.id] ? "⏳" : "🇮🇳 தமிழ்"}
                      </button>
                    ) : (
                      <button
                        onClick={() => setTranslations(prev => { const n = {...prev}; delete n[tender.id]; return n; })}
                        className="px-2 py-1 text-xs border border-gray-200 text-gray-500 rounded-md hover:bg-gray-50 transition-colors"
                        title="Show original"
                      >
                        🇬🇧 EN
                      </button>
                    )}
                  </div>
                </div>
              );
            })
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
