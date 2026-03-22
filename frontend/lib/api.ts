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
  },

  tenders: {
    get: (id: string) => request('GET', `/api/v1/tenders/${id}`),
    list: (params?: any) => request('GET', `/api/v1/tenders${params ? '?' + new URLSearchParams(params) : ''}`),
    search: (params?: any) => request('GET', `/api/v1/tenders${params ? '?' + new URLSearchParams(params) : ''}`),
    create: (data: any) => request('POST', '/api/v1/tenders', data),
    update: (id: string, data: any) => request('PUT', `/api/v1/tenders/${id}`, data),
    delete: (id: string) => request('DELETE', `/api/v1/tenders/${id}`),
  },

  companies: {
    get: (id: string) => request('GET', `/api/v1/companies/${id}`),
    create: (data: any) => request('POST', '/api/v1/companies', data),
    update: (id: string, data: any) => request('PUT', `/api/v1/companies/${id}`, data),
  },

  auth: {
    login: (data: any) => request('POST', '/api/v1/auth/login', data),
    register: (data: any) => request('POST', '/api/v1/auth/register', data),
    me: (token: string) => request('GET', '/api/v1/auth/me', undefined, token),
  },

  compliance: {
    list: (params?: any) => request('GET', `/api/v1/vault${params ? '?' + new URLSearchParams(params) : ''}`),
    upload: (data: any) => request('POST', '/api/v1/vault', data),
    delete: (id: string) => request('DELETE', `/api/v1/vault/${id}`),
  },

  alerts: {
    list: () => request('GET', '/api/v1/notifications'),
    markRead: (id: string) => request('PUT', `/api/v1/notifications/${id}`, { status: 'read' }),
  },
};

export default api;
