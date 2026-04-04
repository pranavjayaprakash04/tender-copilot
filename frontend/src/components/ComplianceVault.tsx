'use client';

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Upload, File, AlertCircle, CheckCircle, Clock,
  Trash2, Download, Search, X, Loader2, ShieldCheck,
} from 'lucide-react';
import { format } from 'date-fns';
import { createClient } from '@supabase/supabase-js';
import { api } from '@/lib/api';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
);

const fetchBlob = async (endpoint: string): Promise<Blob> => {
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://tender-copilot.onrender.com';
  const res = await fetch(`${apiUrl}${endpoint}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error(`Download failed (${res.status})`);
  return res.blob();
};

interface Document {
  id: string;
  filename: string;
  doc_type: string;
  version: number;
  expires_at?: string;
  is_current: boolean;
  uploaded_at: string;
  file_size?: number;
}

interface DocumentStats {
  total_documents: number;
  current_documents: number;
  expired_documents: number;
  expiring_soon_documents: number;
}

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;

const DOC_TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: 'gst',                    label: 'GST Certificate' },
  { value: 'pan',                    label: 'PAN Card' },
  { value: 'iso',                    label: 'ISO Certification' },
  { value: 'udyam',                  label: 'Udyam Registration' },
  { value: 'trade_license',          label: 'Trade License' },
  { value: 'bank_guarantee',         label: 'Bank Guarantee' },
  { value: 'experience_certificate', label: 'Experience Certificate' },
  { value: 'financial_statement',    label: 'Financial Statement' },
  { value: 'tax_clearance',          label: 'Tax Clearance' },
  { value: 'emolument_certificate',  label: 'Emolument Certificate' },
  { value: 'other',                  label: 'Other' },
];

const DOC_TYPE_LABEL: Record<string, string> = Object.fromEntries(
  DOC_TYPE_OPTIONS.map(({ value, label }) => [value, label]),
);

const deriveStats = (docs: Document[]): DocumentStats => {
  const now = Date.now();
  const soon = now + 30 * 24 * 60 * 60 * 1000;
  return {
    total_documents:          docs.length,
    current_documents:        docs.filter(d => d.is_current).length,
    expired_documents:        docs.filter(d => d.expires_at && new Date(d.expires_at).getTime() < now).length,
    expiring_soon_documents:  docs.filter(d => {
      if (!d.expires_at) return false;
      const t = new Date(d.expires_at).getTime();
      return t > now && t <= soon;
    }).length,
  };
};

const getDocumentStatus = (doc: Document): 'superseded' | 'expired' | 'expiring' | 'valid' => {
  if (!doc.is_current) return 'superseded';
  if (!doc.expires_at) return 'valid';
  const t = new Date(doc.expires_at).getTime();
  const now = Date.now();
  if (t < now) return 'expired';
  if (t <= now + 30 * 24 * 60 * 60 * 1000) return 'expiring';
  return 'valid';
};

const STATUS_CONFIG = {
  superseded: { label: 'Superseded',    classes: 'bg-gray-100 text-gray-700' },
  expired:    { label: 'Expired',       classes: 'bg-red-100 text-red-700' },
  expiring:   { label: 'Expiring Soon', classes: 'bg-yellow-100 text-yellow-700' },
  valid:      { label: 'Valid',         classes: 'bg-green-100 text-green-700' },
};

const friendlyError = (err: unknown, fallback: string): string => {
  if (!(err instanceof Error)) return fallback;
  const msg = err.message;
  if (msg.length < 120 && !/\bat\b|\bsql\b|Error:/i.test(msg)) return msg;
  return fallback;
};

interface ConfirmDialogProps {
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}

const ConfirmDialog: React.FC<ConfirmDialogProps> = ({ message, onConfirm, onCancel }) => (
  <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
    <div className="bg-white rounded-xl shadow-2xl p-6 max-w-sm w-full mx-4">
      <div className="flex items-start gap-3 mb-4">
        <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
        <p className="text-gray-800 text-sm">{message}</p>
      </div>
      <div className="flex justify-end gap-3">
        <button onClick={onCancel} className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50">Cancel</button>
        <button onClick={onConfirm} className="px-4 py-2 text-sm text-white bg-red-600 hover:bg-red-700 rounded-lg">Delete</button>
      </div>
    </div>
  </div>
);

const ComplianceVault: React.FC = () => {
  const [documents, setDocuments]           = useState<Document[]>([]);
  const [stats, setStats]                   = useState<DocumentStats | null>(null);
  const [loading, setLoading]               = useState(false);
  const [uploading, setUploading]           = useState(false);
  const [error, setError]                   = useState<string | null>(null);
  const [success, setSuccess]               = useState<string | null>(null);
  const [searchTerm, setSearchTerm]         = useState('');
  const [filterType, setFilterType]         = useState('all');
  const [filterStatus, setFilterStatus]     = useState('all');
  const [pendingDocType, setPendingDocType] = useState('other');
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const successTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const showSuccess = (msg: string) => {
    setSuccess(msg);
    if (successTimer.current) clearTimeout(successTimer.current);
    successTimer.current = setTimeout(() => setSuccess(null), 4000);
  };

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.compliance.getDocuments();
      const docs: Document[] = Array.isArray(data) ? data
        : Array.isArray(data?.documents) ? data.documents
        : Array.isArray(data?.data) ? data.data : [];
      setDocuments(docs);
      setStats(deriveStats(docs));
    } catch (err) {
      setError(friendlyError(err, 'Failed to load documents. Please try again.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
    return () => { if (successTimer.current) clearTimeout(successTimer.current); };
  }, [fetchDocuments]);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;
    setUploading(true);
    setError(null);

    for (const file of acceptedFiles) {
      if (file.size > MAX_FILE_SIZE_BYTES) {
        setError(`"${file.name}" exceeds the 10 MB limit.`);
        setUploading(false);
        return;
      }
      try {
        // Send file + doc_type as query param (backend requires this)
        await (api.compliance.uploadDocument as any)(file, pendingDocType);
        showSuccess(`Uploaded "${file.name}" successfully.`);
      } catch (err) {
        setError(friendlyError(err, `Failed to upload "${file.name}". Please try again.`));
        setUploading(false);
        return;
      }
    }
    setUploading(false);
    fetchDocuments();
  }, [pendingDocType, fetchDocuments]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: true,
    disabled: uploading,
  });

  const requestDelete = (docId: string) => setConfirmDeleteId(docId);

  const confirmDelete = async () => {
    if (!confirmDeleteId) return;
    const docId = confirmDeleteId;
    setConfirmDeleteId(null);
    setError(null);
    try {
      await api.compliance.delete(docId);
      showSuccess('Document deleted.');
      fetchDocuments();
    } catch (err) {
      setError(friendlyError(err, 'Failed to delete the document. Please try again.'));
    }
  };

  const downloadDocument = async (docId: string, filename: string) => {
    setError(null);
    try {
      const blob = await fetchBlob(`/api/v1/vault/${docId}/download`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      requestAnimationFrame(() => { URL.revokeObjectURL(url); document.body.removeChild(a); });
    } catch (err) {
      setError(friendlyError(err, 'Failed to download the document. Please try again.'));
    }
  };

  const filteredDocuments = documents.filter(doc => {
    const matchesSearch = doc.filename.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType   = filterType === 'all' || doc.doc_type === filterType;
    const status        = getDocumentStatus(doc);
    const matchesStatus =
      filterStatus === 'all' ||
      (filterStatus === 'current'  && status === 'valid') ||
      (filterStatus === 'expiring' && status === 'expiring') ||
      (filterStatus === 'expired'  && status === 'expired');
    return matchesSearch && matchesType && matchesStatus;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {confirmDeleteId && (
        <ConfirmDialog
          message="Delete this document permanently? This action cannot be undone."
          onConfirm={confirmDelete}
          onCancel={() => setConfirmDeleteId(null)}
        />
      )}

      <div className="mb-8 flex items-center gap-3">
        <ShieldCheck className="h-8 w-8 text-indigo-600" />
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Compliance Vault</h1>
          <p className="text-gray-500 mt-1">Manage your compliance documents and certificates</p>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Total',         value: stats.total_documents,         icon: File,        color: 'text-blue-600' },
            { label: 'Current',       value: stats.current_documents,       icon: CheckCircle, color: 'text-green-600' },
            { label: 'Expiring Soon', value: stats.expiring_soon_documents, icon: Clock,       color: 'text-yellow-600' },
            { label: 'Expired',       value: stats.expired_documents,       icon: AlertCircle, color: 'text-red-600' },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 flex items-center gap-4">
              <Icon className={`h-7 w-7 flex-shrink-0 ${color}`} />
              <div>
                <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
                <p className="text-2xl font-bold text-gray-900">{value}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm mb-8 p-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Upload Document</h2>
        <div className="mb-4 flex items-center gap-3">
          <label htmlFor="upload-doc-type" className="text-sm text-gray-600 flex-shrink-0">
            Document type <span className="text-red-500">*</span>
          </label>
          <select
            id="upload-doc-type"
            value={pendingDocType}
            onChange={e => setPendingDocType(e.target.value)}
            className="flex-1 max-w-xs px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-400"
          >
            {DOC_TYPE_OPTIONS.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer
            ${isDragActive ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200 hover:border-gray-300'}
            ${uploading ? 'opacity-50 cursor-not-allowed pointer-events-none' : ''}`}
        >
          <input {...getInputProps()} />
          {uploading ? (
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="h-10 w-10 text-indigo-500 animate-spin" />
              <p className="text-sm text-gray-500">Uploading…</p>
            </div>
          ) : isDragActive ? (
            <p className="text-indigo-600 font-medium">Drop files here…</p>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <Upload className="h-10 w-10 text-gray-300" />
              <p className="text-sm text-gray-600">Drag & drop PDF files here, or <span className="text-indigo-600 font-medium">browse</span></p>
              <p className="text-xs text-gray-400">PDF only · Max 10 MB per file</p>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div role="alert" className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-5 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-800 flex-1">{error}</p>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-700"><X className="h-4 w-4" /></button>
        </div>
      )}
      {success && (
        <div role="status" className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 mb-5 flex items-start gap-3">
          <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-green-800 flex-1">{success}</p>
          <button onClick={() => setSuccess(null)} className="text-green-400 hover:text-green-700"><X className="h-4 w-4" /></button>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm mb-6 p-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="search" placeholder="Search documents…" value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-lg w-full focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>
          <select value={filterType} onChange={e => setFilterType(e.target.value)}
            className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-400">
            <option value="all">All Types</option>
            {DOC_TYPE_OPTIONS.map(({ value, label }) => <option key={value} value={value}>{label}</option>)}
          </select>
          <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
            className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-400">
            <option value="all">All Status</option>
            <option value="current">Current</option>
            <option value="expiring">Expiring Soon</option>
            <option value="expired">Expired</option>
          </select>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-sm font-semibold text-gray-700">
            Documents <span className="ml-2 text-gray-400 font-normal">({filteredDocuments.length})</span>
          </h2>
        </div>
        {loading ? (
          <div className="p-12 flex flex-col items-center gap-3 text-gray-400">
            <Loader2 className="h-8 w-8 animate-spin" />
            <p className="text-sm">Loading documents…</p>
          </div>
        ) : filteredDocuments.length === 0 ? (
          <div className="p-12 flex flex-col items-center gap-3 text-gray-400">
            <File className="h-10 w-10" />
            <p className="text-sm">No documents found</p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-50">
            {filteredDocuments.map(doc => {
              const status = getDocumentStatus(doc);
              const cfg = STATUS_CONFIG[status];
              return (
                <li key={doc.id} className="flex items-center gap-4 px-6 py-4 hover:bg-gray-50 transition-colors">
                  <File className="h-8 w-8 text-gray-300 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{doc.filename}</p>
                    <p className="text-xs text-gray-500">{DOC_TYPE_LABEL[doc.doc_type] ?? doc.doc_type} · v{doc.version}</p>
                    <p className="text-xs text-gray-400">
                      Uploaded {format(new Date(doc.uploaded_at), 'dd MMM yyyy')}
                      {doc.expires_at && ` · Expires ${format(new Date(doc.expires_at), 'dd MMM yyyy')}`}
                    </p>
                  </div>
                  <span className={`px-2 py-0.5 text-xs font-medium rounded-full flex-shrink-0 ${cfg.classes}`}>{cfg.label}</span>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <button onClick={() => downloadDocument(doc.id, doc.filename)} title="Download"
                      className="p-2 rounded-lg text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors">
                      <Download className="h-4 w-4" />
                    </button>
                    <button onClick={() => requestDelete(doc.id)} title="Delete"
                      className="p-2 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
};

export default ComplianceVault;
