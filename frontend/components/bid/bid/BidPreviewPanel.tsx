"use client";
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useTranslation } from "@/lib/i18n";
import { Button } from "@/components/ui/button";
import { MessageLoading } from "@/components/ui/message-loading";
import { api } from "@/lib/api";

interface Bid {
  id: string;
  tender_id: string;
  company_id: string;
  status: "draft" | "reviewing" | "submitted" | "won" | "lost" | "withdrawn";
  executive_summary: string;
  technical_approach: string;
  financial_proposal: string;
  compliance_statement: string;
  created_at: string;
  updated_at: string;
}

interface BidPreviewPanelProps {
  bidId: string;
}

export function BidPreviewPanel({ bidId }: BidPreviewPanelProps) {
  const { t } = useTranslation("common");
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState<Partial<Bid>>({});

  const { data: bid, isLoading, error } = useQuery({
    queryKey: ["bid", bidId],
    queryFn: () => api.bids.get(bidId)
  });

  const updateBidMutation = useMutation({
    mutationFn: (data: Partial<Bid>) => api.bids.update(bidId, data),
    onSuccess: () => {
      setIsEditing(false);
      setEditData({});
    }
  });

  const exportBidMutation = useMutation({
    mutationFn: () => api.bids.export(bidId)
  });

  const handleEdit = () => {
    setEditData({
      executive_summary: bid?.executive_summary || "",
      technical_approach: bid?.technical_approach || "",
      financial_proposal: bid?.financial_proposal || "",
      compliance_statement: bid?.compliance_statement || ""
    });
    setIsEditing(true);
  };

  const handleSave = () => {
    updateBidMutation.mutate(editData);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditData({});
  };

  const handleExport = () => {
    exportBidMutation.mutate();
  };

  const handleFieldChange = (field: keyof Bid, value: string) => {
    setEditData(prev => ({ ...prev, [field]: value }));
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-center py-8">
          <MessageLoading />
          <span className="ml-2 text-gray-600">{t("bids.loading")}</span>
        </div>
      </div>
    );
  }

  if (error || !bid) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="text-center py-8">
          <p className="text-red-600 mb-4">{t("bids.error_loading")}</p>
          <Button onClick={() => window.location.reload()}>{t("common.retry")}</Button>
        </div>
      </div>
    );
  }

  const sections = [
    {
      key: "executive_summary" as keyof Bid,
      title: t("bids.executive_summary"),
      value: bid.executive_summary
    },
    {
      key: "technical_approach" as keyof Bid,
      title: t("bids.technical_approach"),
      value: bid.technical_approach
    },
    {
      key: "financial_proposal" as keyof Bid,
      title: t("bids.financial_proposal"),
      value: bid.financial_proposal
    },
    {
      key: "compliance_statement" as keyof Bid,
      title: t("bids.compliance_statement"),
      value: bid.compliance_statement
    }
  ];

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      <div className="p-6 border-b border-gray-200">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-900">
            {t("bids.preview")}
          </h3>
          <div className="flex gap-2">
            {isEditing ? (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCancel}
                  disabled={updateBidMutation.isPending}
                >
                  {t("common.cancel")}
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleSave}
                  disabled={updateBidMutation.isPending}
                >
                  {updateBidMutation.isPending ? (
                    <>
                      <MessageLoading />
                      <span className="ml-2">{t("bids.saving")}</span>
                    </>
                  ) : (
                    t("bids.save")
                  )}
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleExport}
                  disabled={exportBidMutation.isPending}
                >
                  {exportBidMutation.isPending ? (
                    <>
                      <MessageLoading />
                      <span className="ml-2">{t("bids.downloading")}</span>
                    </>
                  ) : (
                    t("bids.download")
                  )}
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleEdit}
                >
                  {t("bids.edit")}
                </Button>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {sections.map((section) => (
          <div key={section.key} className="space-y-2">
            <h4 className="text-md font-medium text-gray-900">
              {section.title}
            </h4>
            {isEditing ? (
              <textarea
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                rows={6}
                value={editData[section.key] || ""}
                onChange={(e) => handleFieldChange(section.key, e.target.value)}
                placeholder={t("bids.edit_placeholder")}
              />
            ) : (
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-gray-700 whitespace-pre-wrap">
                  {section.value || t("bids.no_content")}
                </p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
