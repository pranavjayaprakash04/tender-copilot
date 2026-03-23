"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

// Matches backend TenderResponse field names exactly
interface TenderDetail {
  id: string;
  tender_id: string;
  title: string;
  procuring_entity: string;          // was: organization
  state: string | null;
  category: string | null;
  estimated_value: number | null;    // was: value (number, not string)
  bid_submission_deadline: string | null; // was: deadline
  published_date: string | null;     // was: posted_date
  description: string | null;
  source_url: string | null;
  status: string | null;
  emd_amount: number | null;         // number not string
  processing_fee: number | null;     // was: document_fee
}

export default function TenderDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();

  const { data: rawData, isLoading, error, refetch } = useQuery({
    queryKey: ["tender", params.id],
    queryFn: () => api.tenders.get(params.id),
    staleTime: 60_000,
  });

  // Defensively unwrap: handles both { data: {...} } and the object directly
  const tender: TenderDetail | null = rawData
    ? ((rawData as any).data ?? rawData) as TenderDetail
    : null;

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return "—";
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" });
  };

  const formatCurrency = (value: number | null | undefined) => {
    if (value === null || value === undefined) return "—";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(value);
  };

  const getDeadlineColor = (deadline: string | null | undefined) => {
    if (!deadline) return "text-gray-600";
    const d = new Date(deadline);
    if (isNaN(d.getTime())) return "text-gray-600";
    const days = Math.ceil((d.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
    if (days <= 3) return "text-red-600";
    if (days <= 7) return "text-orange-600";
    return "text-green-600";
  };

  const getDaysLeft = (deadline: string | null | undefined) => {
    if (!deadline) return null;
    const d = new Date(deadline);
    if (isNaN(d.getTime())) return null;
    const days = Math.ceil((d.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
    if (days < 0) return "Closed";
    if (days === 0) return "Due today";
    return `${days} days left`;
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-600">Loading tender...</p>
      </div>
    );
  }

  if (error || !tender) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">Failed to load tender</p>
          <Button onClick={() => refetch()}>Retry</Button>
          <button
            onClick={() => router.back()}
            className="ml-2 px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">

        {/* Back */}
        <button
          onClick={() => router.back()}
          className="text-sm text-gray-500 hover:text-gray-700 mb-6 flex items-center gap-1"
        >
          ← Back
        </button>

        {/* Header card */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex flex-col lg:flex-row lg:justify-between lg:items-start gap-4">
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-gray-900 mb-2">{tender.title}</h1>
              {/* procuring_entity replaces organization */}
              <p className="text-gray-600 text-lg mb-1">{tender.procuring_entity}</p>
              {tender.state && (
                <p className="text-gray-500 text-sm">📍 {tender.state}</p>
              )}
            </div>
            <div className="shrink-0 text-right">
              {/* estimated_value is now a number */}
              <p className="text-2xl font-bold text-gray-900">{formatCurrency(tender.estimated_value)}</p>
              {tender.bid_submission_deadline && (
                <p className={cn("text-sm font-medium mt-1", getDeadlineColor(tender.bid_submission_deadline))}>
                  {getDaysLeft(tender.bid_submission_deadline)}
                </p>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-2 mt-4">
            {tender.category && (
              <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium capitalize">
                {tender.category.replace('_', ' ')}
              </span>
            )}
            {tender.status && (
              <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm font-medium capitalize">
                {tender.status.replace('_', ' ')}
              </span>
            )}
          </div>
        </div>

        {/* Key details */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Key Details</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Posted</p>
              {/* published_date replaces posted_date */}
              <p className="font-medium text-gray-900">{formatDate(tender.published_date)}</p>
            </div>
            <div>
              <p className="text-gray-500">Deadline</p>
              {/* bid_submission_deadline replaces deadline */}
              <p className={cn("font-medium", getDeadlineColor(tender.bid_submission_deadline))}>
                {formatDate(tender.bid_submission_deadline)}
              </p>
            </div>
            <div>
              <p className="text-gray-500">Estimated Value</p>
              <p className="font-medium text-gray-900">{formatCurrency(tender.estimated_value)}</p>
            </div>
            <div>
              <p className="text-gray-500">EMD Amount</p>
              <p className="font-medium text-gray-900">{formatCurrency(tender.emd_amount)}</p>
            </div>
            <div>
              <p className="text-gray-500">Document Fee</p>
              {/* processing_fee replaces document_fee */}
              <p className="font-medium text-gray-900">{formatCurrency(tender.processing_fee)}</p>
            </div>
            <div>
              <p className="text-gray-500">Tender ID</p>
              <p className="font-medium text-gray-900 text-xs break-all">{tender.tender_id || tender.id}</p>
            </div>
          </div>
        </div>

        {/* Description */}
        {tender.description && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Description</h2>
            <p className="text-gray-700 leading-relaxed whitespace-pre-line">{tender.description}</p>
          </div>
        )}

        {/* Actions */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex flex-col sm:flex-row gap-3">
            {tender.source_url && (
              <a
                href={tender.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 transition-colors"
              >
                View on Source Site ↗
              </a>
            )}
            <Button variant="outline" onClick={() => router.back()}>
              Back to Tenders
            </Button>
          </div>
        </div>

      </div>
    </div>
  );
}
