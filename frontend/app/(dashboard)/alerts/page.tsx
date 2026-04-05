"use client";
export const dynamic = "force-dynamic";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useLang } from "@/src/components/LanguageContext";
import { cn } from "@/lib/utils";

interface TenderAlert {
  id: string;
  type: "deadline" | "new_match" | "bid_status" | "document";
  title: string;
  message: string;
  deadline?: string;
  daysLeft?: number;
  isRead: boolean;
  createdAt: string;
  tenderId?: string;
  bidId?: string;
  priority: "high" | "medium" | "low";
}

function daysLeft(dateStr: string): number {
  return Math.ceil((new Date(dateStr).getTime() - Date.now()) / 86400000);
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

const priorityConfig = {
  high:   { dot: "bg-red-500",    badge: "bg-red-100 text-red-800",    label: "Urgent" },
  medium: { dot: "bg-yellow-500", badge: "bg-yellow-100 text-yellow-800", label: "Medium" },
  low:    { dot: "bg-blue-500",   badge: "bg-blue-100 text-blue-800",  label: "Info" },
};

const typeIcon: Record<string, string> = {
  deadline:   "⏰",
  new_match:  "🎯",
  bid_status: "📋",
  document:   "📄",
};

export default function AlertsPage() {
  const qc = useQueryClient();
  const { t } = useLang();
  const [filter, setFilter] = useState<"all" | "unread" | "high">("all");

  // Pull closing-soon tenders to generate deadline alerts
  const { data: closingSoon } = useQuery({
    queryKey: ["closing-soon"],
    queryFn: () => api.get("/api/v1/tenders/closing-soon/list?days=7&limit=20").catch(() => null),
    staleTime: 60_000,
    retry: false,  // don't hammer the backend on 500
  });

  // Pull bids to generate bid status alerts
  const { data: bidsData } = useQuery({
    queryKey: ["bids", "all"],
    queryFn: () => api.bids.list({}),
    staleTime: 60_000,
  });

  // Build alerts from real data
  const alerts: TenderAlert[] = [];

  // Deadline alerts from closing-soon tenders
  const tenders = (closingSoon as any)?.data ?? [];
  tenders.forEach((t: any, i: number) => {
    const deadline = t.bid_submission_deadline || t.bid_end_date;
    if (!deadline) return;
    const days = daysLeft(deadline);
    if (days < 0) return;
    alerts.push({
      id: `deadline-${t.id || i}`,
      type: "deadline",
      title: days <= 2 ? "🚨 Tender Closing Today/Tomorrow!" : `Tender Closing in ${days} Days`,
      message: t.title || "Unnamed Tender",
      deadline,
      daysLeft: days,
      isRead: false,
      createdAt: new Date().toISOString(),
      tenderId: t.id,
      priority: days <= 2 ? "high" : days <= 5 ? "medium" : "low",
    });
  });

  // Bid status alerts
  const bids = (bidsData as any)?.bids ?? [];
  bids.forEach((bid: any) => {
    if (bid.status === "draft") {
      alerts.push({
        id: `bid-draft-${bid.id}`,
        type: "bid_status",
        title: "Bid in Draft",
        message: `"${bid.title || "Untitled Bid"}" is still in draft — review and submit before deadline.`,
        isRead: false,
        createdAt: bid.created_at,
        bidId: bid.id,
        priority: "medium",
      });
    }
    if (bid.status === "submitted") {
      alerts.push({
        id: `bid-submitted-${bid.id}`,
        type: "bid_status",
        title: "Bid Under Review",
        message: `"${bid.title || "Untitled Bid"}" has been submitted and is awaiting evaluation.`,
        isRead: true,
        createdAt: bid.updated_at,
        bidId: bid.id,
        priority: "low",
      });
    }
  });

  // Sort by priority then date
  const priorityOrder = { high: 0, medium: 1, low: 2 };
  alerts.sort((a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]);

  const filtered = alerts.filter(a => {
    if (filter === "unread") return !a.isRead;
    if (filter === "high") return a.priority === "high";
    return true;
  });

  const unreadCount = alerts.filter(a => !a.isRead).length;
  const highCount = alerts.filter(a => a.priority === "high").length;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Alerts</h1>
            <p className="text-gray-500 text-sm mt-1">
              {unreadCount > 0 ? `${unreadCount} ${t("unread alerts", "படிக்காத விழிப்பூட்டல்கள்")}` : t("All caught up", "அனைத்தும் படிக்கப்பட்டது")}
            </p>
          </div>
          {highCount > 0 && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
              <span className="text-red-600 font-semibold text-sm">🚨 {highCount} urgent</span>
            </div>
          )}
        </div>

        {/* Filters */}
        <div className="flex gap-2 mb-6">
          {(["all", "unread", "high"] as const).map((f) => (
            <button key={f} onClick={() => setFilter(f)}
              className={cn(
                "px-4 py-1.5 rounded-full text-sm font-medium border transition-colors",
                filter === f
                  ? "bg-gray-900 text-white border-gray-900"
                  : "bg-white text-gray-600 border-gray-200 hover:border-gray-400"
              )}>
              {f === "all" ? `${t("All","அனைத்தும்")} (${alerts.length})` : f === "unread" ? `${t("Unread","படிக்காதவை")} (${unreadCount})` : `${t("Urgent","அவசரம்")} (${highCount})`}
            </button>
          ))}
        </div>

        {/* Alerts list */}
        {filtered.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <div className="text-4xl mb-3">🎉</div>
            <p className="text-gray-600 font-medium">
              {filter === "all" ? t("No alerts right now — you're all caught up!", "இப்போது விழிப்பூட்டல்கள் இல்லை!") : `${t("No","இல்லை")} ${filter} ${t("alerts","விழிப்பூட்டல்கள்")}.`}
            </p>
            <p className="text-gray-400 text-sm mt-1">Alerts appear when tenders are closing soon or bid status changes.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((alert) => {
              const pc = priorityConfig[alert.priority];
              return (
                <div key={alert.id}
                  className={cn(
                    "bg-white rounded-lg border shadow-sm p-5 transition-all",
                    !alert.isRead ? "border-l-4 border-l-blue-500 border-gray-200" : "border-gray-200 opacity-80"
                  )}>
                  <div className="flex items-start gap-4">
                    <div className="text-2xl flex-shrink-0 mt-0.5">{typeIcon[alert.type]}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="font-semibold text-gray-900 text-sm">{alert.title}</span>
                        <span className={cn("px-2 py-0.5 rounded-full text-xs font-medium", pc.badge)}>
                          {pc.label}
                        </span>
                        {!alert.isRead && (
                          <span className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0" />
                        )}
                      </div>
                      <p className="text-gray-600 text-sm line-clamp-2">{alert.message}</p>
                      {alert.deadline && (
                        <p className={cn(
                          "text-xs font-medium mt-1",
                          alert.daysLeft! <= 2 ? "text-red-600" : alert.daysLeft! <= 5 ? "text-orange-600" : "text-gray-500"
                        )}>
                          📅 Deadline: {formatDate(alert.deadline)}
                          {alert.daysLeft !== undefined && ` · ${alert.daysLeft === 0 ? "Due today" : `${alert.daysLeft} day${alert.daysLeft === 1 ? "" : "s"} left`}`}
                        </p>
                      )}
                    </div>
                    <div className="flex gap-2 flex-shrink-0">
                      {alert.tenderId && (
                        <a href={`/tenders/${alert.tenderId}`}
                          className="px-3 py-1.5 text-xs font-medium bg-indigo-600 text-white rounded-md hover:bg-indigo-700">
                          View
                        </a>
                      )}
                      {alert.bidId && (
                        <a href={`/bids/${alert.bidId}`}
                          className="px-3 py-1.5 text-xs font-medium bg-gray-800 text-white rounded-md hover:bg-gray-900">
                          View Bid
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {alerts.length > 0 && (
          <p className="text-center text-xs text-gray-400 mt-6">
            Alerts are generated from tenders closing within 7 days and your active bids.
          </p>
        )}
      </div>
    </div>
  );
}
