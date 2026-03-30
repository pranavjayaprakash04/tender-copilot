"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Tender {
  id: string;
  tender_id: string;
  title: string;
  description: string;
  procuring_entity: string;
  bid_submission_deadline: string | null;
  estimated_value?: number | null;
  emd_amount?: number | null;
  category: string | null;
  status: string;
  published_date: string | null;
  source_url: string | null;
  state?: string | null;
  match_score?: number | null;
}

interface CompanyProfile {
  id: string;
  name: string;
  industry: string | null;
  location: string | null;
  capabilities_text: string | null;
}

interface TenderListParams {
  category?: string;
  state?: string;
  deadline?: string;
  search?: string;
}

// ─── Match score calculation ──────────────────────────────────────────────────

const CITY_TO_STATE: Record<string, string> = {
  chennai: "tamil nadu", madurai: "tamil nadu", coimbatore: "tamil nadu",
  vellore: "tamil nadu", trichy: "tamil nadu", tiruchirappalli: "tamil nadu",
  salem: "tamil nadu", tirunelveli: "tamil nadu", tirupur: "tamil nadu",
  erode: "tamil nadu", thoothukudi: "tamil nadu", tuticorin: "tamil nadu",
  dindigul: "tamil nadu", thanjavur: "tamil nadu", ranipet: "tamil nadu",
  kanchipuram: "tamil nadu", chengalpattu: "tamil nadu", villupuram: "tamil nadu",
  cuddalore: "tamil nadu", nagapattinam: "tamil nadu", adyar: "tamil nadu",
  tambaram: "tamil nadu", avadi: "tamil nadu", ambattur: "tamil nadu",
  kagithapuram: "tamil nadu", moongilthuraipattu: "tamil nadu",
  kachirayapalayam: "tamil nadu", mondipatti: "tamil nadu", ttps: "tamil nadu",
  "new delhi": "delhi", delhi: "delhi",
  mumbai: "maharashtra", pune: "maharashtra", nagpur: "maharashtra",
  bengaluru: "karnataka", bangalore: "karnataka", mysuru: "karnataka",
  hyderabad: "telangana", warangal: "telangana",
  lucknow: "uttar pradesh", kanpur: "uttar pradesh", agra: "uttar pradesh",
  jaipur: "rajasthan", jodhpur: "rajasthan",
  ahmedabad: "gujarat", surat: "gujarat", vadodara: "gujarat",
  kolkata: "west bengal",
  bhopal: "madhya pradesh", indore: "madhya pradesh",
  patna: "bihar", ranchi: "jharkhand",
  roorkee: "uttarakhand", dehradun: "uttarakhand",
  chandigarh: "punjab",
};

const KNOWN_STATES = [
  "tamil nadu", "karnataka", "maharashtra", "delhi", "telangana",
  "uttar pradesh", "rajasthan", "gujarat", "west bengal", "madhya pradesh",
  "kerala", "andhra pradesh", "bihar", "jharkhand", "odisha",
  "punjab", "haryana", "uttarakhand", "himachal pradesh", "assam",
  "chhattisgarh", "goa", "jammu and kashmir", "sikkim", "meghalaya",
];

const CATEGORY_INDUSTRY_MAP: Record<string, string[]> = {
  Works:    ["construction", "infrastructure", "civil", "engineering", "real estate", "building", "facility"],
  Goods:    ["manufacturing", "supply", "trading", "retail", "logistics", "procurement", "goods", "equipment"],
  Services: ["it", "software", "consulting", "services", "technology", "management", "facility", "maintenance", "digital"],
};

function resolveState(location: string | null | undefined): string {
  if (!location) return "";
  const lower = location.toLowerCase().trim();
  for (const state of KNOWN_STATES) {
    if (lower.includes(state)) return state;
  }
  for (const [city, state] of Object.entries(CITY_TO_STATE)) {
    if (lower.includes(city)) return state;
  }
  return lower;
}

function calculateMatchScore(tender: Tender, profile: CompanyProfile | null): number {
  if (!profile) return 0;
  let score = 0;

  // Category vs Industry (50 pts)
  if (tender.category && profile.industry) {
    const companyIndustry = profile.industry.toLowerCase();
    const keywords = CATEGORY_INDUSTRY_MAP[tender.category] ?? [];
    if (keywords.some((kw) => companyIndustry.includes(kw))) {
      score += 50;
    } else if (companyIndustry.includes(tender.category.toLowerCase())) {
      score += 25;
    }
  }

  // Location match (30 pts)
  const tenderState = resolveState(tender.state);
  const companyState = resolveState(profile.location);
  if (tenderState && companyState) {
    if (tenderState === companyState) {
      score += 30;
    } else if (tenderState.includes(companyState) || companyState.includes(tenderState)) {
      score += 15;
    }
  }

  // Capabilities keyword match (20 pts)
  if (tender.title && profile.capabilities_text) {
    const capabilities = profile.capabilities_text.toLowerCase();
    const titleWords = tender.title.toLowerCase().split(/\s+/);
    const matchCount = titleWords.filter(
      (w) => w.length > 4 && capabilities.includes(w)
    ).length;
    if (matchCount >= 3) score += 20;
    else if (matchCount >= 1) score += 10;
  }

  return Math.min(score, 100);
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

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

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function TendersPage() {
  const router = useRouter();

  const [filters, setFilters] = useState<TenderListParams>({
    category: "",
    state: "",
    deadline: "",
    search: "",
  });

  const [debouncedSearch, setDebouncedSearch] = useState("");
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(filters.search || ""), 400);
    return () => clearTimeout(timer);
  }, [filters.search]);

  const activeFilters = Object.fromEntries(
    Object.entries({ ...filters, search: debouncedSearch }).filter(([_, v]) => v !== "")
  );

  const { data: tenders, isLoading, error, refetch } = useQuery<Tender[]>({
    queryKey: ["tenders", activeFilters],
    queryFn: () => api.tenders.search(activeFilters),
    staleTime: 60_000,
  });

  const { data: profileRaw, isLoading: profileLoading } = useQuery({
    queryKey: ["company-profile"],
    queryFn: () => api.companies.getProfile(),
    staleTime: 300_000,
  });
  const profile: CompanyProfile | null = profileRaw
    ? ((profileRaw as any).data ?? profileRaw) as CompanyProfile
    : null;

  // Score and sort tenders by match score descending
  const sortedTenders = useMemo(() => {
    if (!tenders) return [];
    return [...tenders]
      .map((t) => ({ ...t, _score: calculateMatchScore(t, profile) }))
      .sort((a, b) => b._score - a._score);
  }, [tenders, profile]);

  const clearFilters = useCallback(() => {
    setFilters({ search: "", category: "", state: "", deadline: "" });
    setDebouncedSearch("");
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Tenders</h1>

        {/* Profile setup banner */}
        {!profile && !profileLoading && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-amber-500 text-xl">⚠️</span>
              <div>
                <p className="text-sm font-semibold text-amber-800">Complete your company profile</p>
                <p className="text-xs text-amber-600">Set up your profile to enable bid matching, Bid Intelligence, and Alerts.</p>
              </div>
            </div>
            <a
              href="/profile"
              className="px-4 py-2 bg-amber-500 text-white text-sm font-medium rounded-lg hover:bg-amber-600 transition-colors whitespace-nowrap"
            >
              Set up profile →
            </a>
          </div>
        )}

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
          ) : !sortedTenders || sortedTenders.length === 0 ? (
            <div className="col-span-full text-center py-12">
              <p className="text-gray-600">No tenders found matching your filters</p>
            </div>
          ) : (
            sortedTenders.map((tender) => (
              <div
                key={tender.id}
                className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
              >
                <h3 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">
                  {tender.title}
                </h3>
                <p className="text-gray-600 mb-2 truncate">{tender.procuring_entity}</p>
                <p className="text-lg font-medium text-gray-900 mb-4">
                  {formatValue(tender.estimated_value)}
                </p>
                <div className="flex justify-between items-center mb-4">
                  <span className={cn(
                    "px-2 py-1 rounded-full text-xs font-medium",
                    getMatchScoreColor(tender._score)
                  )}>
                    {profile ? `Match: ${tender._score}%` : "Match: —"}
                  </span>
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
