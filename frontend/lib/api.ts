import { createClient } from '@supabase/supabase-js';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://tender-copilot.onrender.com';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

const getToken = async (): Promise<string | null> => {
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token || null;
};

const request = async (method: string, endpoint: string, data?: any) => {
  const token = await getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${endpoint}`, {
    method,
    headers,
    ...(data ? { body: JSON.stringify(data) } : {}),
  });

  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
};

const uploadFile = async (endpoint: string, formData: FormData) => {
  const token = await getToken();
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${endpoint}`, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
};

const mapTenderParams = (params?: Record<string, any>): Record<string, any> => {
  if (!params) return {};
  const mapped: Record<string, any> = {};
  for (const [key, value] of Object.entries(params)) {
    if (value === '' || value === null || value === undefined) continue;
    switch (key) {
      case 'search':   mapped['search_query'] = value; break;
      case 'deadline': mapped['deadline_days'] = value; break;
      default:         mapped[key] = value;
    }
  }
  return mapped;
};

export const api = {
  get: (endpoint: string) => request('GET', endpoint),
  post: (endpoint: string, data: any) => request('POST', endpoint, data),
  put: (endpoint: string, data: any) => request('PUT', endpoint, data),
  delete: (endpoint: string) => request('DELETE', endpoint),

  bids: {
    // ── Bid lifecycle (pipeline tracking) ────────────────────────────────────
    list: async (params?: { search?: string; status?: string; page?: number; page_size?: number }) => {
      const token = await getToken();
      const qs = new URLSearchParams();
      if (params?.search) qs.set('search', params.search);
      if (params?.status) qs.set('status', params.status);
      if (params?.page) qs.set('page', String(params.page));
      if (params?.page_size) qs.set('page_size', String(params.page_size));
      const res = await fetch(`${API_URL}/api/v1/bids?${qs}`, {
        headers: { Authorization: `Bearer ${await getToken()}` },
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    stats: async () => {
      const res = await fetch(`${API_URL}/api/v1/bids/stats`, {
        headers: { Authorization: `Bearer ${await getToken()}` },
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    create: async (data: {
      tender_id: number;
      title: string;
      bid_amount: number;
      submission_deadline: string;
      company_id: string;
      bid_number: string;
      notes?: string;
      emd_amount?: number;
    }) => {
      const res = await fetch(`${API_URL}/api/v1/bids`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${await getToken()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    get: async (bidId: string) => {
      const res = await fetch(`${API_URL}/api/v1/bids/${bidId}`, {
        headers: { Authorization: `Bearer ${await getToken()}` },
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    update: async (bidId: string, data: Record<string, unknown>) => {
      const res = await fetch(`${API_URL}/api/v1/bids/${bidId}`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${await getToken()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    delete: async (bidId: string) => {
      const res = await fetch(`${API_URL}/api/v1/bids/${bidId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${await getToken()}` },
      });
      if (!res.ok) throw new Error(await res.text());
    },
    transition: async (bidId: string, newStatus: string, reason?: string) => {
      const res = await fetch(`${API_URL}/api/v1/bids/${bidId}/transition`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${await getToken()}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_status: newStatus, reason }),
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    // ── Legacy bid generation methods (kept for existing pages) ───────────────
    search: (params?: any) => request('GET', `/api/v1/bids${params ? '?' + new URLSearchParams(params) : ''}`),
    updateStatus: (id: string, status: string) => request('POST', `/api/v1/bids/${id}/transition`, { new_status: status }),
    recordOutcome: (id: string, data: any) => request('POST', '/api/v1/outcomes', { bid_id: id, ...data }),
    generate: (id: string, lang?: string) => request('POST', `/api/v1/bids/${id}/generate`, { lang }),
    generateContent: (id: string, data?: any) => request('POST', `/api/v1/bids/${id}/generate`, data),
    getStatus: (taskId: string) => request('GET', `/api/v1/bids/status/${taskId}`),
    getAnalytics: (id: string) => request('GET', `/api/v1/bids/${id}/analytics`),
    export: (id: string, format?: string) => request('GET', `/api/v1/bids/${id}/export${format ? '?format=' + format : ''}`),
    getPreview: (id: string) => request('GET', `/api/v1/bids/${id}/preview`),
    saveSection: (id: string, section: string, data: any) => request('PUT', `/api/v1/bids/${id}/sections/${section}`, data),
  },

  tenders: {
    get: (id: string) => request('GET', `/api/v1/tenders/${id}`).then((res: any) => res.data ?? res),
    list: (params?: any) => {
      const mapped = mapTenderParams(params);
      const qs = Object.keys(mapped).length ? '?' + new URLSearchParams(mapped) : '';
      return request('GET', `/api/v1/tenders${qs}`).then((res: any) => res.tenders ?? res.data ?? res);
    },
    search: (params?: any) => {
      const mapped = mapTenderParams(params);
      const qs = Object.keys(mapped).length ? '?' + new URLSearchParams(mapped) : '';
      return request('GET', `/api/v1/tenders${qs}`).then((res: any) => res.tenders ?? res.data ?? res);
    },
    create: (data: any) => request('POST', '/api/v1/tenders', data),
    update: (id: string, data: any) => request('PUT', `/api/v1/tenders/${id}`, data),
    delete: (id: string) => request('DELETE', `/api/v1/tenders/${id}`),
    getMatches: (params?: any) => request('GET', `/api/v1/tenders/matches${params ? '?' + new URLSearchParams(params) : ''}`),
    getSimilar: (id: string) => request('GET', `/api/v1/tenders/${id}/similar`),
  },

  companies: {
    // GET — returns null (not 404) when no profile exists yet
    getProfile: () => request('GET', '/api/v1/company/profile').catch(() => null),
    // POST — first-time profile creation
    createProfile: (data: any) => request('POST', '/api/v1/company/profile', data),
    // PATCH — update existing profile
    updateProfile: (data: any) => request('PATCH', '/api/v1/company/profile', data),
  },

  auth: {
    login: (data: any) => request('POST', '/api/v1/auth/login', data),
    register: (data: any) => request('POST', '/api/v1/auth/register', data),
    me: () => request('GET', '/api/v1/auth/me'),
    logout: () => request('POST', '/api/v1/auth/logout'),
  },

  compliance: {
    list: (params?: any) =>
      request('GET', `/api/v1/vault/documents${params ? '?' + new URLSearchParams(params) : ''}`)
        .then((res: any) => res?.data ?? res),
    get: (id: string) =>
      request('GET', `/api/v1/vault/${id}`)
        .then((res: any) => res?.data ?? res),
    getDocuments: (params?: any) =>
      request('GET', `/api/v1/vault/documents${params ? '?' + new URLSearchParams(params) : ''}`)
        .then((res: any) => res?.data ?? res),
    upload: (formData: FormData, docType: string = 'other') =>
      uploadFile(`/api/v1/vault/upload?doc_type=${encodeURIComponent(docType)}`, formData)
        .then((res: any) => res?.data ?? res),
    uploadDocument: (formData: FormData, docType: string = 'other') =>
      uploadFile(`/api/v1/vault/upload?doc_type=${encodeURIComponent(docType)}`, formData)
        .then((res: any) => res?.data ?? res),
    update: (id: string, data: any) =>
      request('PUT', `/api/v1/vault/documents/${id}`, data)
        .then((res: any) => res?.data ?? res),
    delete: (id: string) =>
      request('DELETE', `/api/v1/vault/documents/${id}`)
        .then((res: any) => res?.data ?? res),
    download: async (id: string): Promise<string> => {
      const token = await getToken();
      const res = await fetch(`${API_URL}/api/v1/vault/${id}/download`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      return data?.url ?? data?.data?.url ?? data;
    },
  },

  intelligence: {
    getWinProbability: (data: any) =>
      request('POST', '/api/v1/intelligence/bid/win-probability', data),
    getCompetitorAnalysis: (data: any) =>
      request('POST', '/api/v1/intelligence/bid/analyze-competitors', data),
    getMarketPrice: (category: string) =>
      request('GET', `/api/v1/intelligence/bid/market-price/${encodeURIComponent(category)}`),
  },
};

export default api;
