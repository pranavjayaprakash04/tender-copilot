const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://tender-copilot.onrender.com';

const getToken = () => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('auth_token');
  }
  return null;
};

const headers = (token?: string): Record<string, string> => ({
  'Content-Type': 'application/json',
  ...(token || getToken() ? { Authorization: `Bearer ${token || getToken()}` } : {}),
});

const request = async (method: string, endpoint: string, data?: any, token?: string) => {
  const res = await fetch(`${API_URL}${endpoint}`, {
    method,
    headers: headers(token),
    ...(data ? { body: JSON.stringify(data) } : {}),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
};

export const api = {
  get: (endpoint: string, token?: string) => request('GET', endpoint, undefined, token),
  post: (endpoint: string, data: any, token?: string) => request('POST', endpoint, data, token),
  put: (endpoint: string, data: any, token?: string) => request('PUT', endpoint, data, token),
  delete: (endpoint: string, token?: string) => request('DELETE', endpoint, undefined, token),

  bids: {
    get: (id: string) => request('GET', `/api/v1/bids/${id}`),
    list: (params?: any) => request('GET', `/api/v1/bids${params ? '?' + new URLSearchParams(params) : ''}`),
    search: (params?: any) => request('GET', `/api/v1/bids${params ? '?' + new URLSearchParams(params) : ''}`),
    create: (data: any) => request('POST', '/api/v1/bids', data),
    update: (id: string, data: any) => request('PUT', `/api/v1/bids/${id}`, data),
    updateStatus: (id: string, status: string) => request('POST', `/api/v1/bids/${id}/transition`, { new_status: status }),
    recordOutcome: (id: string, data: any) => request('POST', '/api/v1/outcomes', { bid_id: id, ...data }),
    delete: (id: string) => request('DELETE', `/api/v1/bids/${id}`),
    generateContent: (id: string, data?: any) => request('POST', `/api/v1/bids/${id}/generate`, data),
    getAnalytics: (id: string) => request('GET', `/api/v1/bids/${id}/analytics`),
  },

  tenders: {
    get: (id: string) => request('GET', `/api/v1/tenders/${id}`),
    list: (params?: any) => request('GET', `/api/v1/tenders${params ? '?' + new URLSearchParams(params) : ''}`),
    search: (params?: any) => request('GET', `/api/v1/tenders${params ? '?' + new URLSearchParams(params) : ''}`),
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
    me: (token: string) => request('GET', '/api/v1/auth/me', undefined, token),
    logout: () => request('POST', '/api/v1/auth/logout'),
    refreshToken: (token: string) => request('POST', '/api/v1/auth/refresh', { token }),
  },

  compliance: {
    list: (params?: any) => request('GET', `/api/v1/vault${params ? '?' + new URLSearchParams(params) : ''}`),
    get: (id: string) => request('GET', `/api/v1/vault/${id}`),
    upload: (data: any) => request('POST', '/api/v1/vault', data),
    update: (id: string, data: any) => request('PUT', `/api/v1/vault/${id}`, data),
    delete: (id: string) => request('DELETE', `/api/v1/vault/${id}`),
    getCategories: () => request('GET', '/api/v1/vault/categories'),
  },

  alerts: {
    list: () => request('GET', '/api/v1/notifications'),
    getActive: () => request('GET', '/api/v1/notifications?status=pending'),
    markRead: (id: string) => request('PUT', `/api/v1/notifications/${id}`, { status: 'read' }),
    markAllRead: () => request('PUT', '/api/v1/notifications/mark-all-read', {}),
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
