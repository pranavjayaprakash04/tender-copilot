// ── Add this to your api.ts under the existing companies section ──────────────
// Paste this entire block into frontend/lib/api.ts

bids: {
  // List all bids for the company
  list: async (params?: { search?: string; status?: string; page?: number; page_size?: number }) => {
    const token = await getToken();
    const qs = new URLSearchParams();
    if (params?.search) qs.set("search", params.search);
    if (params?.status) qs.set("status", params.status);
    if (params?.page) qs.set("page", String(params.page));
    if (params?.page_size) qs.set("page_size", String(params.page_size));
    const res = await fetch(`${API_URL}/api/v1/bids?${qs}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Get bid stats
  stats: async () => {
    const token = await getToken();
    const res = await fetch(`${API_URL}/api/v1/bids/stats`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Create a bid from a tender
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
    const token = await getToken();
    const res = await fetch(`${API_URL}/api/v1/bids`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Get a single bid
  get: async (bidId: string) => {
    const token = await getToken();
    const res = await fetch(`${API_URL}/api/v1/bids/${bidId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Update a bid
  update: async (bidId: string, data: Record<string, unknown>) => {
    const token = await getToken();
    const res = await fetch(`${API_URL}/api/v1/bids/${bidId}`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Delete a bid
  delete: async (bidId: string) => {
    const token = await getToken();
    const res = await fetch(`${API_URL}/api/v1/bids/${bidId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error(await res.text());
  },

  // Transition bid status
  transition: async (bidId: string, newStatus: string, reason?: string) => {
    const token = await getToken();
    const res = await fetch(`${API_URL}/api/v1/bids/${bidId}/transition`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ new_status: newStatus, reason }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
},
