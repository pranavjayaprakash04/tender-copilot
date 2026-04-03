"use client";
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
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

const SECTIONS: { key: keyof Bid; title: string }[] = [
  { key: "executive_summary", title: "Executive Summary" },
  { key: "technical_approach", title: "Technical Approach" },
  { key: "financial_proposal", title: "Financial Proposal" },
  { key: "compliance_statement", title: "Compliance Statement" },
];

export function BidPreviewPanel({ bidId }: BidPreviewPanelProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState<Partial<Bid>>({});

  const { data: bid, isLoading, error } = useQuery<Bid>({
    queryKey: ["bid", bidId],
    queryFn: () => api.bids.get(bidId),
  });

  const updateBidMutation = useMutation({
    mutationFn: (data: Partial<Bid>) => api.bids.update(bidId, data),
    onSuccess: () => {
      setIsEditing(false);
      setEditData({});
    },
  });

  const handleEdit = () => {
    if (!bid) return;
    setEditData({
      executive_summary: bid.executive_summary || "",
      technical_approach: bid.technical_approach || "",
      financial_proposal: bid.financial_proposal || "",
      compliance_statement: bid.compliance_statement || "",
    });
    setIsEditing(true);
  };

  const handleFieldChange = (field: keyof Bid, value: string) => {
    setEditData((prev) => ({ ...prev, [field]: value }));
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse">
        <div className="space-y-4">
          {[...Array(4)].map((_, i) => (
            <div key={i}>
              <div className="h-4 bg-gray-200 rounded w-1/4 mb-2" />
              <div className="h-20 bg-gray-100 rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error || !bid) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 text-center">
        <p className="text-red-600 mb-4 text-sm">Could not load bid content.</p>
        <Button onClick={() => window.location.reload()}>Retry</Button>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200">
      <div className="p-5 border-b border-gray-200 flex items-center justify-between">
        <h3 className="text-base font-semibold text-gray-900">Bid Content</h3>
        <div className="flex gap-2">
          {isEditing ? (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => { setIsEditing(false); setEditData({}); }}
                disabled={updateBidMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={() => updateBidMutation.mutate(editData)}
                disabled={updateBidMutation.isPending}
              >
                {updateBidMutation.isPending ? "Saving…" : "Save"}
              </Button>
            </>
          ) : (
            <Button variant="outline" size="sm" onClick={handleEdit}>
              Edit
            </Button>
          )}
        </div>
      </div>

      <div className="p-5 space-y-5">
        {SECTIONS.map((section) => (
          <div key={String(section.key)}>
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              {section.title}
            </h4>
            {isEditing ? (
              <textarea
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none resize-none"
                rows={5}
                value={String(editData[section.key] ?? "")}
                onChange={(e) => handleFieldChange(section.key, e.target.value)}
                placeholder={`Enter ${section.title.toLowerCase()}…`}
              />
            ) : (
              <div className="bg-gray-50 rounded-lg px-4 py-3 text-sm text-gray-700 whitespace-pre-wrap leading-relaxed min-h-[60px]">
                {String(bid[section.key] || "") || (
                  <span className="text-gray-400 italic">No content yet.</span>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
