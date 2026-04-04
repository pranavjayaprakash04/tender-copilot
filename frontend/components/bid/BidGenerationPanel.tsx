"use client";
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useTranslation } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { MessageLoading } from "@/components/ui/message-loading";
import { api } from "@/lib/api";

interface BidGenerationPanelProps {
  tenderId: string;
  tenderTitle: string;
  companyId: string;
}

export function BidGenerationPanel({ tenderId, tenderTitle, companyId }: BidGenerationPanelProps) {
  const { t, i18n } = useTranslation("common");
  const [taskId, setTaskId] = useState<string | null>(null);
  const [polling, setPolling] = useState(false);
  const [currentLang, setCurrentLang] = useState<"en" | "ta">(i18n.language as "en" | "ta");

  const generateBidMutation = useMutation({
    mutationFn: async (lang: "en" | "ta") => {
      const response = await api.bids.generate({ tender_id: tenderId, language: lang });
      setTaskId(response.task_id);
      setPolling(true);
      return response;
    }
  });

  const { data: bidStatus } = useQuery({
    queryKey: ["bid-status", taskId],
    queryFn: () => api.bids.getStatus(taskId!),
    enabled: !!taskId && polling,
    refetchInterval: polling ? 3000 : false
  });

  const handleLanguageToggle = () => {
    const newLang = currentLang === "en" ? "ta" : "en";
    setCurrentLang(newLang);
  };

  const handleGenerateBid = () => {
    generateBidMutation.mutate(currentLang);
  };

  if (bidStatus?.status === "completed") {
    setPolling(false);
    window.location.href = `/bids/${bidStatus.bid_id}`;
  }

  if (bidStatus?.status === "failed") {
    setPolling(false);
  }

  const getProgressColor = (progress: number) => {
    if (progress >= 80) return "bg-green-500";
    if (progress >= 50) return "bg-yellow-500";
    return "bg-blue-500";
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          {t("bids.generate_bid")}
        </h3>
        <Button
          variant="outline"
          size="sm"
          onClick={handleLanguageToggle}
          disabled={generateBidMutation.isPending || polling}
        >
          {currentLang === "en" ? "EN" : "தமிழ்"}
        </Button>
      </div>

      <div className="mb-4">
        <p className="text-sm text-gray-600 mb-2">
          {t("bids.tender_title")}: {tenderTitle}
        </p>
        <p className="text-sm text-gray-600">
          {t("bids.language")}: {currentLang === "en" ? "English" : "தமிழ்"}
        </p>
      </div>

      <Button
        variant="default"
        size="lg"
        onClick={handleGenerateBid}
        disabled={generateBidMutation.isPending || polling}
      >
        {generateBidMutation.isPending || polling ? (
          <>
            <MessageLoading />
            <span className="ml-2">{t("bids.generating")}</span>
          </>
        ) : (
          t("bids.generate")
        )}
      </Button>

      {bidStatus && polling && (
        <div className="mt-4 space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">{t("bids.progress")}</span>
            <span className="font-medium">{bidStatus.progress}%</span>
          </div>
          
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${getProgressColor(bidStatus.progress)}`}
              style={{ width: `${bidStatus.progress}%` }}
            />
          </div>

          <div className="flex items-center text-blue-600">
            <MessageLoading />
            <span className="ml-2 text-sm">
              {bidStatus.status === "processing" 
                ? t("bids.processing") 
                : t("bids.pending")
              }
            </span>
          </div>
        </div>
      )}

      {bidStatus?.status === "failed" && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800 text-sm mb-2">
            {t("bids.generation_failed")}
          </p>
          {bidStatus.error && (
            <p className="text-red-600 text-xs">{bidStatus.error}</p>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleGenerateBid}
          >
            {t("bids.retry")}
          </Button>
        </div>
      )}
    </div>
  );
}
