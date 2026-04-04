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

export type TenderItem = {
  id: string;
  title: string;
  category?: string;
  deadline?: string;
  value?: string | number;
  portal?: string;
  location?: string;
  description?: string;
  organisation?: string;
  match_score?: number;
  status?: string;
};

export type AlertItem = {
  id: string;
  title?: string;
  message?: string;
  type?: string;
  is_read?: boolean;
  created_at?: string;
};

export const api = {
  get: (path: string) => request(path),
  post: (path: string, body: unknown) =>
    request(path, { method: "POST", body: JSON.stringify(body) }),

  tenders: {
    list: (params?: Record<string, string | undefined>) => {
      const q = new URLSearchParams(
        Object.fromEntries(
          Object.entries(params || {}).filter(([, v]) => v !== undefined)
        ) as Record<string, string>
      ).toString();
      return request<{ tenders: TenderItem[]; total: number }>(
        `/api/v1/tenders/${q ? `?${q}` : ""}`
      );
    },
    search: (params?: Record<string, string | undefined>) => {
      const q = new URLSearchParams(
        Object.fromEntries(
          Object.entries(params || {}).filter(([, v]) => v !== undefined)
        ) as Record<string, string>
      ).toString();
      return request<{ tenders: TenderItem[]; total: number }>(
        `/api/v1/tenders/${q ? `?${q}` : ""}`
      );
    },
    get: (id: string) => request<TenderItem>(`/api/v1/tenders/${id}`),
  },

  bids: {
    list: () => request<any>("/api/v1/bids/"),
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
    export: (id: string, format: string) =>
      request<any>(`/api/v1/bids/${id}/export?format=${format}`),
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
    uploadDocument: (data: Record<string, unknown>) =>
      request<any>("/api/v1/compliance/documents", {
        method: "POST",
        body: JSON.stringify(data),
      }),
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
