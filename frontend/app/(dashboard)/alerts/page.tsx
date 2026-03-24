"use client";
export const dynamic = "force-dynamic";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";

type Alert = {
  id: string;
  title: string;
  message: string;
  type: "expiry" | "bid" | "tender" | "system" | string;
  status: "pending" | "read" | string;
  created_at: string;
};

const TYPE_META: Record<string, { label: string; icon: string; color: string; bg: string }> = {
  expiry:  { label: "Expiry",  icon: "⏰", color: "text-amber-700",  bg: "bg-amber-50 border-amber-200"  },
  bid:     { label: "Bid",     icon: "📋", color: "text-blue-700",   bg: "bg-blue-50 border-blue-200"    },
  tender:  { label: "Tender",  icon: "📢", color: "text-violet-700", bg: "bg-violet-50 border-violet-200"},
  system:  { label: "System",  icon: "🔔", color: "text-gray-700",   bg: "bg-gray-50 border-gray-200"    },
};

function getMeta(type: string) {
  return TYPE_META[type] ?? TYPE_META.system;
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function AlertsPage() {
  const qc = useQueryClient();
  const [filter, setFilter] = useState<"all" | "unread">("all");

  const { data: alerts = [], isLoading, isError } = useQuery<Alert[]>({
    queryKey: ["alerts"],
    queryFn: async () => {
      const res = await api.alerts.list();
      return Array.isArray(res) ? res : res.notifications ?? res.data ?? [];
    },
    retry: 1,
  });

  const markRead = useMutation({
    mutationFn: (id: string) => api.alerts.markRead(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  const markAllRead = useMutation({
    mutationFn: () => api.alerts.markAllRead(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  const deleteAlert = useMutation({
    mutationFn: (id: string) => api.alerts.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  const unreadCount = alerts.filter((a) => a.status === "pending").length;
  const filtered = filter === "unread" ? alerts.filter((a) => a.status === "pending") : alerts;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-3xl mx-auto px-4 py-8">

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-gray-900">Alerts</h1>
            {unreadCount > 0 && (
              <span className="inline-flex items-center justify-center h-6 min-w-6 px-1.5 rounded-full bg-blue-600 text-white text-xs font-semibold">
                {unreadCount}
              </span>
            )}
          </div>
          {unreadCount > 0 && (
            <button
              onClick={() => markAllRead.mutate()}
              disabled={markAllRead.isPending}
              className="text-sm font-medium text-blue-600 hover:text-blue-700 disabled:opacity-50"
            >
              Mark all read
            </button>
          )}
        </div>

        {/* Filter tabs */}
        <div className="flex gap-1 mb-5 bg-white border border-gray-200 rounded-lg p-1 w-fit">
          {(["all", "unread"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors capitalize ${
                filter === f
                  ? "bg-gray-900 text-white"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              {f}
              {f === "unread" && unreadCount > 0 && ` (${unreadCount})`}
            </button>
          ))}
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-white border border-gray-200 rounded-xl p-4 animate-pulse">
                <div className="flex gap-3">
                  <div className="w-9 h-9 rounded-full bg-gray-200" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-gray-200 rounded w-1/3" />
                    <div className="h-3 bg-gray-100 rounded w-2/3" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : isError ? (
          <div className="bg-white border border-gray-200 rounded-xl p-8 text-center">
            <div className="text-3xl mb-3">⚠️</div>
            <p className="text-gray-700 font-medium">Couldn't load alerts</p>
            <p className="text-gray-500 text-sm mt-1">Check your connection and try again.</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-xl p-12 text-center">
            <div className="text-4xl mb-4">🔔</div>
            <p className="text-gray-700 font-semibold text-lg">
              {filter === "unread" ? "No unread alerts" : "No alerts yet"}
            </p>
            <p className="text-gray-400 text-sm mt-1">
              {filter === "unread"
                ? "You're all caught up."
                : "Alerts for expiring documents, bid deadlines, and new tenders will appear here."}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {filtered.map((alert) => {
              const meta = getMeta(alert.type);
              const isUnread = alert.status === "pending";
              return (
                <div
                  key={alert.id}
                  className={`relative bg-white border rounded-xl p-4 transition-all group ${
                    isUnread ? "border-blue-200 shadow-sm shadow-blue-50" : "border-gray-200"
                  }`}
                >
                  {isUnread && (
                    <span className="absolute top-4 right-4 w-2 h-2 rounded-full bg-blue-500" />
                  )}
                  <div className="flex gap-3 pr-6">
                    {/* Icon */}
                    <div className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center text-base border ${meta.bg}`}>
                      {meta.icon}
                    </div>

                    {/* Body */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start gap-2 flex-wrap">
                        <p className={`text-sm font-semibold ${isUnread ? "text-gray-900" : "text-gray-700"}`}>
                          {alert.title}
                        </p>
                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${meta.bg} ${meta.color}`}>
                          {meta.label}
                        </span>
                      </div>
                      <p className="text-sm text-gray-500 mt-0.5 line-clamp-2">{alert.message}</p>
                      <div className="flex items-center gap-3 mt-2">
                        <span className="text-xs text-gray-400">{timeAgo(alert.created_at)}</span>
                        {isUnread && (
                          <button
                            onClick={() => markRead.mutate(alert.id)}
                            className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                          >
                            Mark read
                          </button>
                        )}
                        <button
                          onClick={() => deleteAlert.mutate(alert.id)}
                          className="text-xs text-gray-400 hover:text-red-500 font-medium opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          Dismiss
                        </button>
                      </div>
                    </div>
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
