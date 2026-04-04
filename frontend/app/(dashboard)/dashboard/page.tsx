"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "@/lib/i18n";
import { api } from "@/lib/api";

export default function DashboardPage() {
  const { t } = useTranslation("common");

  const { data: tendersData, isLoading: tendersLoading } = useQuery({
    queryKey: ["tenders-search"],
    queryFn: () => api.tenders.search({})
  });

  const { data: alertsData, isLoading: alertsLoading } = useQuery({
    queryKey: ["alerts-active"],
    queryFn: () => api.alerts.getActive()
  });

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            {t("dashboard.title")}
          </h1>
          <p className="text-gray-600">
            {t("dashboard.subtitle")}
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 bg-blue-100 rounded-full">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600">{t("dashboard.total_tenders")}</p>
                <p className="text-2xl font-bold text-gray-900">
                  {tendersLoading ? "..." : tendersData?.total || 0}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 bg-green-100 rounded-full">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-5 5 5-5M9 12l5 5-5-5" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600">{t("dashboard.active_bids")}</p>
                <p className="text-2xl font-bold text-gray-900">0</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 bg-yellow-100 rounded-full">
                <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600">{t("dashboard.pending_reviews")}</p>
                <p className="text-2xl font-bold text-gray-900">0</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 bg-red-100 rounded-full">
                <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600">{t("dashboard.active_alerts")}</p>
                <p className="text-2xl font-bold text-gray-900">
                  {alertsLoading ? "..." : alertsData?.length || 0}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Recent Tenders */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">
                {t("dashboard.recent_tenders")}
              </h2>
            </div>
            <div className="p-6">
              {tendersLoading ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                  <p className="mt-2 text-gray-600">{t("common.loading")}</p>
                </div>
              ) : tendersData?.tenders && tendersData.tenders.length > 0 ? (
                <div className="space-y-4">
                  {tendersData.tenders.slice(0, 5).map((tender: any) => (
                    <div key={tender.id} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                      <div>
                        <h4 className="text-sm font-medium text-gray-900">{tender.title}</h4>
                        <p className="text-xs text-gray-600">{(tender as any).organisation ?? (tender as any).organization ?? ""}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-medium text-gray-900">
                          {tender.value ? `₹${parseInt(String(tender.value)).toLocaleString("en-IN")}` : 'N/A'}
                        </p>
                        <p className="text-xs text-gray-500">
                          {tender.deadline ? new Date(tender.deadline).toLocaleDateString() : ''}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-gray-600">{t("dashboard.no_recent_tenders")}</p>
                </div>
              )}
            </div>
          </div>

          {/* Recent Alerts */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">
                {t("dashboard.recent_alerts")}
              </h2>
            </div>
            <div className="p-6">
              {alertsLoading ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                  <p className="mt-2 text-gray-600">{t("common.loading")}</p>
                </div>
              ) : alertsData && alertsData.length > 0 ? (
                <div className="space-y-4">
                  {alertsData.slice(0, 5).map((alert: any, index: number) => (
                    <div key={index} className="flex items-center p-3 bg-yellow-50 rounded">
                      <div className="flex-shrink-0">
                        <svg className="w-5 h-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                        </svg>
                      </div>
                      <div className="ml-3">
                        <p className="text-sm font-medium text-gray-900">
                          {typeof alert === 'string' ? alert : 'New alert'}
                        </p>
                        <p className="text-xs text-gray-500">
                          {new Date().toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-gray-600">{t("dashboard.no_recent_alerts")}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}