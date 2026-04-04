const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

async function getToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  try {
    const { createClient } = await import("@supabase/supabase-js");
    const sb = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );
    const {
      data: { session },
    } = await sb.auth.getSession();
    return session?.access_token ?? null;
  } catch {
    return null;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((options.headers as Record<string, string>) ?? {}),
  };
  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json() as Promise<T>;
}

export const api = {
  tenders: {
    list: (params?: Record<string, string | undefined>) => {
      const q = new URLSearchParams();
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          if (v) q.set(k, v);
        });
      }
      return request<{
        tenders: TenderItem[];
        total: number;
        page: number;
        limit: number;
      }>(`/api/v1/tenders/?${q}`);
    },
    search: (params?: Record<string, string | undefined>) =>
      api.tenders.list(params),
    get: (id: string) => request<TenderDetail>(`/api/v1/tenders/${id}`),
  },

  bids: {
    list: (params?: { status?: string }) => {
      const q = params?.status ? `?status=${params.status}` : "";
      return request<{ bids: BidItem[]; total: number; page: number; limit: number }>(
        `/api/v1/bids/${q}`
      );
    },
    get: (id: string) => request<BidDetail>(`/api/v1/bids/${id}`),
    create: (data: Record<string, unknown>) =>
      request<BidDetail>("/api/v1/bids/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Partial<BidDetail>) =>
      request<BidDetail>(`/api/v1/bids/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    updateStatus: (id: string, status: string) =>
      request<BidDetail>(`/api/v1/bids/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    recordOutcome: (
      id: string,
      data: { outcome: string; our_price: number; winning_price?: number }
    ) =>
      request<BidDetail>(`/api/v1/bids/${id}/outcome`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    generate: (tenderId: string, language = "en") =>
      request<{ task_id: string; bid_id: string; status: string }>(
        "/api/v1/bids/generate",
        {
          method: "POST",
          body: JSON.stringify({ tender_id: tenderId, language }),
        }
      ),
    getStatus: (taskId: string) =>
      request<{ status: string; progress: number; bid_id?: string; error?: string }>(
        `/api/v1/bids/${taskId}/status`
      ),
    export: (id: string) => request<Blob>(`/api/v1/bids/${id}/export`),
  },

  alerts: {
    list: (params?: Record<string, string | undefined>) => {
      const q = new URLSearchParams();
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          if (v) q.set(k, v);
        });
      }
      return request<AlertItem[]>(`/api/v1/alerts/?${q}`);
    },
    getActive: () => request<AlertItem[]>("/api/v1/alerts/?active=true"),
    markRead: (id: string) =>
      request<void>(`/api/v1/alerts/${id}/read`, { method: "PATCH" }),
    markAllRead: () =>
      request<void>("/api/v1/alerts/mark-all-read", { method: "POST" }),
    create: (data: Record<string, unknown>) =>
      request<AlertItem>("/api/v1/alerts/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  vault: {
    list: () => request<DocumentItem[]>("/api/v1/vault/documents"),
    delete: (id: string) =>
      request<void>(`/api/v1/vault/documents/${id}`, { method: "DELETE" }),
    getSignedUrl: (id: string) =>
      request<{ url: string }>(`/api/v1/vault/documents/${id}/url`),
    uploadMetadata: (data: Record<string, unknown>) =>
      request<DocumentItem>("/api/v1/vault/upload", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  compliance: {
    getDocuments: () => request<DocumentItem[]>("/api/v1/vault/documents"),
    uploadDocument: async (file: File) => {
      const token = await getToken();
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${API_URL}/api/v1/vault/upload`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      if (!res.ok) throw new Error("Upload failed");
      return res.json() as Promise<DocumentItem>;
    },
  },

  company: {
    getProfile: () => request<CompanyProfile>("/api/v1/company/profile"),
    updateProfile: (data: Partial<CompanyProfile>) =>
      request<CompanyProfile>("/api/v1/company/profile", {
        method: "PUT",
        body: JSON.stringify(data),
      }),
  },

  partner: {
    getClients: () => request<CompanyProfile[]>("/api/v1/partner/clients"),
  },

  getCACompanies: () => request<CompanyProfile[]>("/api/v1/partner/clients"),

  intelligence: {
    getMarketPrices: () =>
      request<MarketPriceData>("/api/v1/intelligence/market-prices"),
  },
};

// ---- Shared type stubs (minimal, match backend schemas) ----

export interface TenderItem {
  id: string;
  title: string;
  description: string;
  organization: string;
  deadline: string;
  value?: string | number;
  category: string;
  status: "active" | "closed" | "cancelled";
  posted_date: string;
  source_url: string;
  department?: string;
  authority?: string;
  state?: string;
  requirements?: string[];
  match_score?: number;
}

export interface TenderDetail extends TenderItem {
  match_score: number;
  value: number | string;
  department: string;
  authority: string;
  state: string;
  requirements: string[];
}

export interface BidItem {
  id: string;
  tender_id: string;
  tender_title: string;
  company_id: string;
  status: "draft" | "reviewing" | "submitted" | "won" | "lost" | "withdrawn";
  created_at: string;
  updated_at: string;
}

export interface BidDetail extends BidItem {
  executive_summary: string;
  technical_approach: string;
  financial_proposal: string;
  compliance_statement: string;
}

export interface AlertItem {
  id: string;
  message?: string;
  is_read?: boolean;
  created_at?: string;
}

export interface DocumentItem {
  id: string;
  filename: string;
  doc_type: string;
  version: number;
  expires_at?: string;
  is_current: boolean;
  uploaded_at: string;
  file_size?: number;
  download_url?: string;
}

export interface CompanyProfile {
  id?: string;
  name?: string;
  gstin?: string;
  pan?: string;
  udyam_number?: string;
  category?: string;
  state?: string;
  turnover?: number;
}

export interface MarketPriceData {
  prices?: unknown[];
  [key: string]: unknown;
}
