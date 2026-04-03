"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface Client {
  id?: string;
  name?: string;
  company_name?: string;
  email?: string;
  phone?: string;
  industry?: string;
  active_bids_count?: number;
}

function SkeletonCard() {
  return (
    <div className="border border-gray-200 rounded-xl p-5 animate-pulse">
      <div className="h-5 bg-gray-200 rounded w-2/3 mb-3" />
      <div className="h-4 bg-gray-100 rounded w-1/2 mb-2" />
      <div className="h-4 bg-gray-100 rounded w-1/3" />
    </div>
  );
}

export default function ClientsPage() {
  const { data: rawClients, isLoading, isError, refetch } = useQuery({
    queryKey: ["ca-clients"],
    queryFn: () => api.partner.getClients(),
    retry: 1,
  });

  const clients: Client[] = Array.isArray(rawClients)
    ? rawClients
    : (rawClients as any)?.clients ?? (rawClients as any)?.data ?? [];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">CA Partner Portal</h1>
          <p className="text-gray-500 text-sm mt-1">Manage your client companies</p>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
          </div>
        ) : isError ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <div className="text-4xl mb-4">⚠️</div>
            <h3 className="text-lg font-semibold text-gray-800 mb-2">Could not load clients</h3>
            <p className="text-gray-500 text-sm mb-6">
              You may not be on the CA Partner plan, or there was a connection error.
            </p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => refetch()}
                className="px-5 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors"
              >
                Retry
              </button>
              <a
                href="/profile"
                className="px-5 py-2 border border-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
              >
                Upgrade Plan
              </a>
            </div>
          </div>
        ) : clients.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <div className="text-4xl mb-4">👥</div>
            <h3 className="text-lg font-semibold text-gray-800 mb-2">No clients yet</h3>
            <p className="text-gray-500 text-sm">
              Your client companies will appear here once they connect with you.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {clients.map((client, index) => {
              const name = client.name || client.company_name || `Client ${index + 1}`;
              return (
                <div
                  key={client.id || index}
                  className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold text-sm"
                      style={{ background: "linear-gradient(135deg, #3B82F6, #8B5CF6)" }}
                    >
                      {name[0].toUpperCase()}
                    </div>
                    {typeof client.active_bids_count === "number" && (
                      <span className="text-xs font-medium px-2 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-100">
                        {client.active_bids_count} active bid{client.active_bids_count !== 1 ? "s" : ""}
                      </span>
                    )}
                  </div>

                  <h3 className="text-base font-semibold text-gray-900 mb-1">{name}</h3>

                  {client.industry && (
                    <p className="text-xs text-gray-500 mb-2">{client.industry}</p>
                  )}

                  <div className="space-y-1">
                    {client.email && (
                      <p className="text-sm text-gray-600 truncate">{client.email}</p>
                    )}
                    {client.phone && (
                      <p className="text-sm text-gray-600">{client.phone}</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
