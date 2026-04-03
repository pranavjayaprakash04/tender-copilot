"use client";
import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useTranslation } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { MessageLoading } from "@/components/ui/message-loading";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface TenderDetail {
  id: string;
  title: string;
  department: string;
  authority: string;
  value: number;
  category: string;
  state: string;
  deadline: string;
  description: string;
  requirements: string[];
  match_score: number;
}

interface BidStatusResponse {
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  bid_id?: string;
  error?: string;
}

interface CreateAlertInput {
  tender_id: string;
  criteria: {
    keywords?: string[];
    category?: string;
    state?: string;
    min_value?: number;
  };
}

export default function TenderDetailPage({ params }: { params: { id: string } }) {
  const { t, i18n } = useTranslation("common");
  const [taskId, setTaskId] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);

  const { data: tender, isLoading, error } = useQuery<TenderDetail>({
    queryKey: ["tender", params.id],
    queryFn: () => api.tenders.get(params.id) as Promise<TenderDetail>
  });

  const generateBidMutation = useMutation({
    mutationFn: async (tenderId: string) => {
      const result = await api.bids.generate(tenderId);
      setTaskId(result.task_id);
      setPolling(true);
      return result;
    }
  });

  const { data: bidStatus } = useQuery<BidStatusResponse>({
    queryKey: ["bid-status", taskId],
    queryFn: () => api.bids.getStatus(taskId!) as Promise<BidStatusResponse>,
    enabled: !!taskId && polling,
    refetchInterval: polling ? 3000 : false
  });

  const createAlertMutation = useMutation({
    mutationFn: (data: CreateAlertInput) =>
      api.alerts.create(data as unknown as Record<string, unknown>),
    onSuccess: () => {
      alert(t("tenders.alert_created"));
    }
  });

  useEffect(() => {
    if (bidStatus?.status === "completed") {
      setPolling(false);
      window.location.href = `/bids/${bidStatus.bid_id}`;
    } else if (bidStatus?.status === "failed") {
      setPolling(false);
      alert(t("tenders.bid_generation_failed"));
    }
  }, [bidStatus]);

  const getMatchScoreColor = (score: number) => {
    if (score >= 80) return "bg-green-100 text-green-800";
    if (score >= 60) return "bg-yellow-100 text-yellow-800";
    if (score >= 40) return "bg-orange-100 text-orange-800";
    return "bg-red-100 text-red-800";
  };

  const getDeadlineColor = (deadline: string) => {
    const days = Math.ceil((new Date(deadline).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24));
    if (days <= 3) return "text-red-600";
    if (days <= 7) return "text-orange-600";
    return "text-green-600";
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <MessageLoading />
          <p className="mt-4 text-gray-600">Loading tender...</p>
        </div>
      </div>
    );
  }

  if (error || !tender) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">Error loading tender</p>
          <Button onClick={() => window.location.reload()}>Retry</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex justify-between items-start mb-4">
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-gray-900 mb-2">{tender.title}</h1>
              <p className="text-lg text-gray-600 mb-1">{tender.authority}</p>
              <p className="text-gray-600">{tender.department}</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-gray-900">₹{tender.value.toLocaleString("en-IN")}</p>
              <span className={cn(
                "px-3 py-1 rounded-full text-sm font-medium inline-block mt-2",
                getMatchScoreColor(tender.match_score)
              )}>
                Match Score: {tender.match_score}%
              </span>
            </div>
          </div>

          <div className="flex flex-wrap gap-4 mb-4">
            <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
              {tender.category}
            </span>
            <span className="px-3 py-1 bg-gray-100 text-gray-800 rounded-full text-sm font-medium">
              {tender.state}
            </span>
            <span className={cn(
              "px-3 py-1 rounded-full text-sm font-medium",
              getDeadlineColor(tender.deadline)
            )}>
              Deadline: {new Date(tender.deadline).toLocaleDateString(
                i18n.language === "ta" ? "ta-IN" : "en-IN"
              )}
            </span>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Description</h2>
          <p className="text-gray-700 leading-relaxed">{tender.description}</p>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Requirements</h2>
          <ul className="space-y-2">
            {tender.requirements.map((req, index) => (
              <li key={index} className="flex items-start">
                <span className="text-blue-600 mr-2">•</span>
                <span className="text-gray-700">{req}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <Button
              variant="default"
              size="lg"
              onClick={() => generateBidMutation.mutate(tender.id)}
              disabled={generateBidMutation.isPending || polling}
            >
              {generateBidMutation.isPending || polling ? (
                <>
                  <MessageLoading />
                  <span className="ml-2">Generating bid...</span>
                </>
              ) : (
                "Generate Bid"
              )}
            </Button>

            <Button
              variant="outline"
              size="lg"
              onClick={() => createAlertMutation.mutate({
                tender_id: tender.id,
                criteria: {
                  category: tender.category,
                  state: tender.state,
                  min_value: tender.value * 0.8
                }
              })}
              disabled={createAlertMutation.isPending}
            >
              {createAlertMutation.isPending ? "Setting alert..." : "Set Alert"}
            </Button>
          </div>

          {bidStatus && polling && (
            <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center">
                <MessageLoading />
                <span className="ml-2 text-blue-800">
                  Bid progress: {bidStatus.progress}%
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
