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

/**
 * Multipart file upload helper.
 * Do NOT set Content-Type manually — the browser sets it with the correct boundary.
 */
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

/**
 * Maps frontend filter keys to backend query param names for the tenders API.
 * Frontend uses short friendly names; backend expects TenderSearchFilters field names.
 */
const mapTenderParams = (params?: Record<string, any>): Record<string, any> => {
  if (!params) return {};
  const mapped: Record<string, any> = {};
  for (const [key, value] of Object.entries(params)) {
    if (value === '' || value === null || value === undefined) continue;
    switch (key) {
      case 'search':       mapped['search_query'] = value; break;
      case 'deadline':     mapped['deadline_days'] = value; break;
      // category, state, source, status pass through unchanged
      default:             mapped[key] = value;
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
    get: (id: string) => request('GET', `/api/v1/bids/${id}`),
    list: (params?: any) => request('GET', `/api/v1/bids${params ? '?' + new URLSearchParams(params) : ''}`),
    search: (params?: any) => request('GET', `/api/v1/bids${params ? '?' + new URLSearchParams(params) : ''}`),
    create: (data: any) => request('POST', '/api/v1/bids', data),
    update: (id: string, data: any) => request('PUT', `/api/v1/bids/${id}`, data),
    updateStatus: (id: string, status: string) => request('POST', `/api/v1/bids/${id}/transition`, { new_status: status }),
    recordOutcome: (id: string, data: any) => request('POST', '/api/v1/outcomes', { bid_id: id, ...data }),
    delete: (id: string) => request('DELETE', `/api/v1/bids/${id}`),
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
    get: (id: string) => request('GET', `/api/v1/companies/${id}`),
    getProfile: () => request('GET', '/api/v1/companies/profile'),
    create: (data: any) => request('POST', '/api/v1/companies', data),
    update: (id: string, data: any) => request('PUT', `/api/v1/companies/${id}`, data),
    updateProfile: (data: any) => request('PUT', '/api/v1/companies/profile', data),
  },

  auth: {
    login: (data: any) => request('POST', '/api/v1/auth/login', data),
    register: (data: any) => request('POST', '/api/v1/auth/register', data),
    me: () => request('GET', '/api/v1/auth/me'),
    logout: () => request('POST', '/api/v1/auth/logout'),
  },

  compliance: {
    // Backend returns PaginatedResponse: { data: [...], success, pagination }
    // Unwrap .data here so every caller gets a plain array — never an object.
    list:           (params?: any)          => request('GET', `/api/v1/vault/documents${params ? '?' + new URLSearchParams(params) : ''}`)
                                               .then((res: any) => res?.data ?? res),
    get:            (id: string)            => request('GET', `/api/v1/vault/${id}`)
                                               .then((res: any) => res?.data ?? res),
    getDocuments:   (params?: any)          => request('GET', `/api/v1/vault/documents${params ? '?' + new URLSearchParams(params) : ''}`)
                                               .then((res: any) => res?.data ?? res),
    // POST /vault/upload — multipart, must use uploadFile not request
    upload:         (data: FormData)        => uploadFile('/api/v1/vault/upload', data)
                                               .then((res: any) => res?.data ?? res),
    uploadDocument: (data: FormData)        => uploadFile('/api/v1/vault/upload', data)
                                               .then((res: any) => res?.data ?? res),
    update:         (id: string, data: any) => request('PUT', `/api/v1/vault/${id}`, data)
                                               .then((res: any) => res?.data ?? res),
    delete:         (id: string)            => request('DELETE', `/api/v1/vault/${id}`),
    deleteDocument: (id: string)            => request('DELETE', `/api/v1/vault/${id}`),
    getCategories:  ()                      => request('GET', '/api/v1/vault/categories')
                                               .then((res: any) => res?.data ?? res),
    download:       (id: string)            => request('GET', `/api/v1/vault/${id}/download`),
    getStats:       ()                      => request('GET', '/api/v1/vault/stats')
                                               .then((res: any) => res?.data ?? res),
  },

  // Fixed: unwrap PaginatedResponse { data: [...], pagination: {...} }
  alerts: {
    list: () => request('GET', '/api/v1/notifications').then((res: any) => res.data ?? []),
    getActive: () => request('GET', '/api/v1/notifications?status=pending').then((res: any) => res.data ?? []),
    markRead: (id: string) => request('PUT', `/api/v1/notifications/${id}`, { status: 'read' }),
    markAllRead: () => Promise.resolve(),
    delete: (id: string) => request('DELETE', `/api/v1/notifications/${id}`),
    getPreferences: () => request('GET', '/api/v1/notifications/preferences'),
    updatePreferences: (data: any) => request('PUT', '/api/v1/notifications/preferences', data),
  },

  profile: {
    get: () => request('GET', '/api/v1/profile'),
    update: (data: any) => request('PUT', '/api/v1/profile', data),
    uploadAvatar: (data: any) => request('POST', '/api/v1/profile/avatar', data),
  },

  partner: {
    getClients: () => request('GET', '/api/v1/ca/clients'),
    getClient: (id: string) => request('GET', `/api/v1/ca/clients/${id}`),
    addClient: (data: any) => request('POST', '/api/v1/ca/clients', data),
    updateClient: (id: string, data: any) => request('PUT', `/api/v1/ca/clients/${id}`, data),
    removeClient: (id: string) => request('DELETE', `/api/v1/ca/clients/${id}`),
    getDashboard: () => request('GET', '/api/v1/ca/dashboard'),
  },
};

export default api;
