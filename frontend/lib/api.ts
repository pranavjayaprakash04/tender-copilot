import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
const supabase = createClient(supabaseUrl, supabaseAnonKey);

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

async function getAuthToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(error || `Request failed: ${res.status}`);
  }
  if (res.status === 204) return {} as T;
  return res.json();
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type TenderItem = {
  id: string;
  title: string;
  category?: string;
  deadline?: string;
  value?: string | number;
  portal?: string;
  location?: string;
  description?: string;
  /** Both spellings of organisation/organization accepted */
  organisation?: string;
  organization?: string;
  match_score?: number;
  status?: string;
  estimated_value?: string | number;
  tender_value?: string | number;
};

export type AlertItem = {
  id: string;
  title?: string;
  message?: string;
  type?: string;
  is_read?: boolean;
  created_at?: string;
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const api = {
  get: (path: string) => request<any>(path),
  post: (path: string, body: unknown) =>
    request<any>(path, { method: "POST", body: JSON.stringify(body) }),

  tenders: {
    list: (params?: Record<string, string | undefined>) => {
      const q = new URLSearchParams(
        Object.fromEntries(
          Object.entries(params || {}).filter(([, v]) => v !== undefined)
        ) as Record<string, string>
      ).toString();
      return request<{ tenders: TenderItem[]; total: number; page?: number; limit?: number }>(
        `/api/v1/tenders/${q ? `?${q}` : ""}`
      );
    },
    search: (params?: Record<string, string | undefined>) => {
      const q = new URLSearchParams(
        Object.fromEntries(
          Object.entries(params || {}).filter(([, v]) => v !== undefined)
        ) as Record<string, string>
      ).toString();
      return request<{ tenders: TenderItem[]; total: number; page?: number; limit?: number }>(
        `/api/v1/tenders/${q ? `?${q}` : ""}`
      );
    },
    get: (id: string) => request<TenderItem>(`/api/v1/tenders/${id}`),
  },

  bids: {
    list: (params?: Record<string, string | undefined>) => {
      const q = params
        ? new URLSearchParams(
            Object.fromEntries(
              Object.entries(params).filter(([, v]) => v !== undefined)
            ) as Record<string, string>
          ).toString()
        : "";
      return request<any>(`/api/v1/bids/${q ? `?${q}` : ""}`);
    },
    get: (id: string) => request<any>(`/api/v1/bids/${id}`),
    create: (data: Record<string, unknown>) =>
      request<any>("/api/v1/bids/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: Record<string, unknown>) =>
      request<any>(`/api/v1/bids/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    updateStatus: (id: string, status: string) =>
      request<any>(`/api/v1/bids/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    transition: (id: string, status: string, reason?: string) =>
      request<any>(`/api/v1/bids/${id}/transition`, {
        method: "POST",
        body: JSON.stringify({ status, reason }),
      }),
    recordOutcome: (id: string, data: Record<string, unknown>) =>
      request<any>(`/api/v1/bids/${id}/outcome`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    generate: (data: Record<string, unknown>) =>
      request<any>("/api/v1/bids/generate", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    getStatus: (taskId: string) => request<any>(`/api/v1/bids/${taskId}/status`),
    export: (id: string, format = "pdf") =>
      request<any>(`/api/v1/bids/${id}/export?format=${format}`),
    stats: () => request<any>("/api/v1/bids/stats"),
    approve: (id: string) =>
      request<any>(`/api/v1/bids/${id}/approve`, { method: "POST" }),
    reject: (id: string, reason?: string) =>
      request<any>(`/api/v1/bids/${id}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      }),
    submitForReview: (id: string) =>
      request<any>(`/api/v1/bids/${id}/submit-review`, { method: "POST" }),
    delete: (id: string) =>
      request<void>(`/api/v1/bids/${id}`, { method: "DELETE" }),
  },

  alerts: {
    list: (params?: Record<string, string | undefined>) => {
      const q = new URLSearchParams(
        Object.fromEntries(
          Object.entries(params || {}).filter(([, v]) => v !== undefined)
        ) as Record<string, string>
      ).toString();
      return request<AlertItem[]>(`/api/v1/alerts/${q ? `?${q}` : ""}`);
    },
    getActive: () => request<AlertItem[]>("/api/v1/alerts/?active=true"),
    markRead: (id: string) =>
      request<void>(`/api/v1/alerts/${id}/read`, { method: "PATCH" }),
    markAllRead: () =>
      request<void>("/api/v1/alerts/mark-all-read", { method: "POST" }),
    delete: (id: string) =>
      request<void>(`/api/v1/alerts/${id}`, { method: "DELETE" }),
    create: (data: Record<string, unknown>) =>
      request<AlertItem>("/api/v1/alerts/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  vault: {
    list: () => request<any>("/api/v1/vault/documents"),
    delete: (id: string) =>
      request<void>(`/api/v1/vault/documents/${id}`, { method: "DELETE" }),
    getSignedUrl: (id: string) =>
      request<{ url: string }>(`/api/v1/vault/documents/${id}/url`),
    uploadMetadata: (data: Record<string, unknown>) =>
      request<any>("/api/v1/vault/upload", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  compliance: {
    getDocuments: () => request<any>("/api/v1/compliance/documents"),
    uploadDocument: async (fileOrData: File | Record<string, unknown>) => {
      if (fileOrData instanceof File) {
        const token = await getAuthToken();
        const formData = new FormData();
        formData.append("file", fileOrData);
        const res = await fetch(`${BASE_URL}/api/v1/compliance/documents`, {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        });
        if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
        return res.json();
      }
      return request<any>("/api/v1/compliance/documents", {
        method: "POST",
        body: JSON.stringify(fileOrData),
      });
    },
    deleteDocument: (id: string) =>
      request<void>(`/api/v1/compliance/documents/${id}`, { method: "DELETE" }),
    getSignedUrl: (id: string) =>
      request<{ url: string }>(`/api/v1/compliance/documents/${id}/url`),
  },

  company: {
    getProfile: () => request<any>("/api/v1/company/profile"),
    updateProfile: (data: Record<string, unknown>) =>
      request<any>("/api/v1/company/profile", {
        method: "PUT",
        body: JSON.stringify(data),
      }),
  },

  partner: {
    getClients: () => request<any>("/api/v1/partner/clients"),
  },

  intelligence: {
    getMarketPrices: (params?: Record<string, string>) => {
      const q = new URLSearchParams(params || {}).toString();
      return request<any>(`/api/v1/intelligence/market-prices${q ? `?${q}` : ""}`);
    },
  },
};

export default api;
