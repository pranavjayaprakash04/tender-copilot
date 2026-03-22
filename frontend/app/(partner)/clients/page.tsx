"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface Company {
  id?: string;
  name?: string;
  email?: string;
  phone?: string;
}

export default function ClientsPage() {
  const { data: companies, isLoading } = useQuery({
    queryKey: ["ca-companies"],
    queryFn: () => api.partner.getClients()
  });

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">CA Partner Portal</h1>

        {isLoading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-2 text-gray-600">Loading companies...</p>
          </div>
        ) : companies && companies.length > 0 ? (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {companies.map((company: Company, index: number) => (
                  <div key={company.id || index} className="border border-gray-200 rounded-lg p-4">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      {company.name || `Company ${index + 1}`}
                    </h3>
                    <p className="text-gray-600">
                      {company.email || 'Company information available'}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <p className="text-gray-600">No companies found.</p>
          </div>
        )}
      </div>
    </div>
  );
}
