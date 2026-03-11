"use client";
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useTranslation } from "next-i18next";
import { Button } from "@/components/ui/button";
import { MessageLoading } from "@/components/ui/message-loading";
import { BidPreviewPanel } from "@/components/bid/BidPreviewPanel";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Bid {
  id: string;
  tender_id: string;
  tender_title: string;
  company_id: string;
  status: "draft" | "reviewing" | "submitted" | "won" | "lost" | "withdrawn";
  executive_summary: string;
  technical_approach: string;
  financial_proposal: string;
  compliance_statement: string;
  created_at: string;
  updated_at: string;
}

interface OutcomeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (outcome: "won" | "lost", ourPrice: number, winningPrice?: number) => void;
  loading: boolean;
}

function OutcomeModal({ isOpen, onClose, onSubmit, loading }: OutcomeModalProps) {
  const { t } = useTranslation("common");
  const [outcome, setOutcome] = useState<"won" | "lost">("won");
  const [ourPrice, setOurPrice] = useState("");
  const [winningPrice, setWinningPrice] = useState("");

  const handleOutcomeSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!ourPrice) return;
    
    onSubmit(
      outcome,
      parseFloat(ourPrice),
      outcome === "lost" && winningPrice ? parseFloat(winningPrice) : undefined
    );
  };

  const handleButtonClick = () => {
    if (!ourPrice) return;
    onSubmit(
      outcome,
      parseFloat(ourPrice),
      outcome === "lost" && winningPrice ? parseFloat(winningPrice) : undefined
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-md w-full p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          {t("bids.outcome.record")}
        </h3>
        
        <form onSubmit={handleOutcomeSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t("bids.outcome.result")}
            </label>
            <div className="flex gap-4">
              <label className="flex items-center">
                <input
                  type="radio"
                  value="won"
                  checked={outcome === "won"}
                  onChange={(e) => setOutcome(e.target.value as "won" | "lost")}
                  className="mr-2"
                />
                {t("bids.outcome.won")}
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  value="lost"
                  checked={outcome === "lost"}
                  onChange={(e) => setOutcome(e.target.value as "won" | "lost")}
                  className="mr-2"
                />
                {t("bids.outcome.lost")}
              </label>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t("bids.outcome.our_price")}
            </label>
            <input
              type="number"
              step="0.01"
              value={ourPrice}
              onChange={(e) => setOurPrice(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="0.00"
              required
            />
          </div>

          {outcome === "lost" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t("bids.outcome.winning_price")}
              </label>
              <input
                type="number"
                step="0.01"
                value={winningPrice}
                onChange={(e) => setWinningPrice(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="0.00"
              />
            </div>
          )}

          <div className="flex gap-3 pt-4">
            <Button
              variant="outline"
              onClick={onClose}
              disabled={loading}
            >
              {t("common.cancel")}
            </Button>
            <Button
              variant="default"
              onClick={handleButtonClick}
              disabled={loading || !ourPrice}
            >
              {loading ? (
                <>
                  <MessageLoading />
                  <span className="ml-2">{t("bids.saving")}</span>
                </>
              ) : (
                t("bids.outcome.submit")
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function BidDetailPage({ params }: { params: { id: string } }) {
  const { t, i18n } = useTranslation("common");
  const [currentLang, setCurrentLang] = useState<"en" | "ta">(i18n.language as "en" | "ta");
  const [showOutcomeModal, setShowOutcomeModal] = useState(false);

  const { data: bid, isLoading, error } = useQuery({
    queryKey: ["bid", params.id],
    queryFn: () => api.bids.get(params.id)
  });

  const updateStatusMutation = useMutation({
    mutationFn: (status: string) => api.bids.updateStatus(params.id, status),
    onSuccess: () => {
      window.location.reload();
    }
  });

  const recordOutcomeMutation = useMutation({
    mutationFn: (data: { outcome: "won" | "lost"; our_price: number; winning_price?: number }) =>
      api.bids.recordOutcome(params.id, data),
    onSuccess: () => {
      setShowOutcomeModal(false);
      window.location.reload();
    }
  });

  const handleLanguageToggle = () => {
    const newLang = currentLang === "en" ? "ta" : "en";
    setCurrentLang(newLang);
  };

  const handleStatusUpdate = (newStatus: string) => {
    updateStatusMutation.mutate(newStatus);
  };

  const handleOutcomeSubmit = (outcome: "won" | "lost", ourPrice: number, winningPrice?: number) => {
    recordOutcomeMutation.mutate({
      outcome,
      our_price: ourPrice,
      winning_price: winningPrice
    });
  };

  const getStatusColor = (status: string) => {
    const colors = {
      draft: "bg-gray-100 text-gray-800",
      reviewing: "bg-yellow-100 text-yellow-800",
      submitted: "bg-blue-100 text-blue-800",
      won: "bg-green-100 text-green-800",
      lost: "bg-red-100 text-red-800",
      withdrawn: "bg-gray-100 text-gray-600"
    };
    return colors[status as keyof typeof colors] || "bg-gray-100 text-gray-800";
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(
      currentLang === "ta" ? "ta-IN" : "en-IN",
      { 
        year: "numeric", 
        month: "long", 
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit"
      }
    );
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="flex items-center justify-center py-12">
            <MessageLoading />
            <span className="ml-2 text-gray-600">{t("bids.loading")}</span>
          </div>
        </div>
      </div>
    );
  }

  if (error || !bid) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="text-center py-12">
            <p className="text-red-600 mb-4">{t("bids.error_loading")}</p>
            <Button onClick={() => window.location.reload()}>{t("common.retry")}</Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.location.href = "/bids"}
            >
              ← {t("common.back")}
            </Button>
            <h1 className="text-3xl font-bold text-gray-900">
              {t("bids.detail_title")}
            </h1>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleLanguageToggle}
          >
            {currentLang === "en" ? "EN" : "தமிழ்"}
          </Button>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                {bid.tender_title}
              </h2>
              <div className="flex flex-wrap gap-4 text-sm text-gray-600">
                <span>{t("bids.created")}: {formatDate(bid.created_at)}</span>
                <span>{t("bids.updated")}: {formatDate(bid.updated_at)}</span>
              </div>
            </div>
            
            <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
              <span
                className={cn(
                  "px-3 py-1 rounded-full text-sm font-medium",
                  getStatusColor(bid.status)
                )}
              >
                {t(`bids.status.${bid.status}`)}
              </span>
              
              <div className="flex gap-2">
                {bid.status === "draft" && (
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => handleStatusUpdate("reviewing")}
                    disabled={updateStatusMutation.isPending}
                  >
                    {updateStatusMutation.isPending ? (
                      <>
                        <MessageLoading />
                        <span className="ml-2">{t("bids.updating")}</span>
                      </>
                    ) : (
                      t("bids.submit_review")
                    )}
                  </Button>
                )}
                
                {bid.status === "reviewing" && (
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => handleStatusUpdate("submitted")}
                    disabled={updateStatusMutation.isPending}
                  >
                    {updateStatusMutation.isPending ? (
                      <>
                        <MessageLoading />
                        <span className="ml-2">{t("bids.updating")}</span>
                      </>
                    ) : (
                      t("bids.submit_bid")
                    )}
                  </Button>
                )}
                
                {bid.status === "submitted" && (
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => setShowOutcomeModal(true)}
                  >
                    {t("bids.outcome.record")}
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>

        <BidPreviewPanel bidId={params.id} />

        <OutcomeModal
          isOpen={showOutcomeModal}
          onClose={() => setShowOutcomeModal(false)}
          onSubmit={handleOutcomeSubmit}
          loading={recordOutcomeMutation.isPending}
        />
      </div>
    </div>
  );
}
