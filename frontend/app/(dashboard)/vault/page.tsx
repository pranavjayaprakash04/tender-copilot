"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

// ─── Types ────────────────────────────────────────────────────────────────────

type DocumentType =
  | "gst" | "pan" | "iso" | "udyam" | "trade_license" | "bank_guarantee"
  | "experience_certificate" | "financial_statement" | "tax_clearance"
  | "emolument_certificate" | "other";

interface VaultDocument {
  id: string;
  doc_type: DocumentType;
  filename: string;
  storage_path: string;
  version: number;
  expires_at: string | null;
  is_current: boolean;
  uploaded_at: string;
  is_expired: boolean;
  days_until_expiry: number | null;
  is_expiring_soon: boolean;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const DOC_TYPE_META: Record<DocumentType, { label: string; abbr: string; color: string; hasExpiry: boolean }> = {
  gst:                    { label: "GST Certificate",               abbr: "GST",  color: "#3B82F6", hasExpiry: true  },
  pan:                    { label: "PAN Card",                      abbr: "PAN",  color: "#8B5CF6", hasExpiry: false },
  iso:                    { label: "ISO / Quality Certificate",     abbr: "ISO",  color: "#10B981", hasExpiry: true  },
  udyam:                  { label: "MSME / Udyam Certificate",      abbr: "MSME", color: "#F59E0B", hasExpiry: true  },
  trade_license:          { label: "Trade License",                 abbr: "TL",   color: "#EF4444", hasExpiry: true  },
  bank_guarantee:         { label: "Bank Guarantee",                abbr: "BG",   color: "#06B6D4", hasExpiry: true  },
  experience_certificate: { label: "Work Experience / Past Orders", abbr: "EXP",  color: "#EC4899", hasExpiry: false },
  financial_statement:    { label: "Audited Balance Sheet / ITR",   abbr: "FIN",  color: "#84CC16", hasExpiry: true  },
  tax_clearance:          { label: "Tax Clearance Certificate",     abbr: "TAX",  color: "#F97316", hasExpiry: true  },
  emolument_certificate:  { label: "Emolument Certificate",         abbr: "EMO",  color: "#A78BFA", hasExpiry: true  },
  other:                  { label: "Other Document",                abbr: "OTH",  color: "#6B7280", hasExpiry: false },
};

const DOC_TYPES = Object.entries(DOC_TYPE_META) as [DocumentType, typeof DOC_TYPE_META[DocumentType]][];

// ─── PDF-only security validation ────────────────────────────────────────────

const MAX_FILE_BYTES = 10 * 1024 * 1024;

async function validatePdf(file: File): Promise<string | null> {
  if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf"))
    return "Only PDF files are accepted.";
  if (file.size > MAX_FILE_BYTES)
    return "File exceeds 10 MB limit.";

  const buf = await file.slice(0, 65536).arrayBuffer();
  const bytes = new Uint8Array(buf);
  const magic = String.fromCharCode(bytes[0], bytes[1], bytes[2], bytes[3]);
  if (magic !== "%PDF") return "File is not a valid PDF.";

  for (let i = 0; i < bytes.length - 1; i++) {
    if (bytes[i] === 0x4d && bytes[i + 1] === 0x5a) return "File contains embedded executable content.";
  }

  const text = new TextDecoder("ascii", { fatal: false }).decode(bytes);
  if (/\/JS\b|\/JavaScript\b|\/AA\b/.test(text)) return "PDF contains JavaScript — file rejected.";

  return null;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function getExpiryBadge(doc: VaultDocument): { label: string; cls: string } {
  if (!doc.expires_at)      return { label: "No Expiry",                      cls: "badge-neutral" };
  if (doc.is_expired)       return { label: "Expired",                         cls: "badge-red"     };
  if (doc.is_expiring_soon) return { label: `${doc.days_until_expiry}d left`, cls: "badge-amber"   };
  return                           { label: `${doc.days_until_expiry}d left`, cls: "badge-green"   };
}

// ─── Delete Confirm Dialog ────────────────────────────────────────────────────

function DeleteDialog({ filename, onConfirm, onCancel }: {
  filename: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="modal-overlay" onClick={onCancel} role="dialog" aria-modal="true" aria-label="Confirm deletion">
      <div className="confirm-card" onClick={(e) => e.stopPropagation()}>
        <div className="confirm-icon">🗑️</div>
        <h3 className="confirm-title">Delete Document?</h3>
        <p className="confirm-desc">
          <strong>{filename}</strong> will be permanently deleted and cannot be recovered.
        </p>
        <div className="confirm-actions">
          <Button variant="outline" onClick={onCancel}>Cancel</Button>
          <Button onClick={onConfirm} style={{ background: "#EF4444" }}>Delete</Button>
        </div>
      </div>
    </div>
  );
}

// ─── Upload Modal ─────────────────────────────────────────────────────────────

function UploadModal({ onClose }: { onClose: () => void }) {
  const [docType, setDocType]     = useState<DocumentType>("gst");
  const [file, setFile]           = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState("");
  const [dragOver, setDragOver]   = useState(false);
  const fileRef                   = useRef<HTMLInputElement>(null);
  const queryClient               = useQueryClient();
  const meta                      = DOC_TYPE_META[docType];

  const handleFile = useCallback(async (f: File) => {
    setFileError(null);
    const err = await validatePdf(f);
    if (err) { setFileError(err); setFile(null); return; }
    setFile(f);
  }, []);

  const upload = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("No file selected");
      const formData = new FormData();
      formData.append("file", file);
      if (expiresAt) formData.append("expires_at", new Date(expiresAt).toISOString());
      // Pass docType explicitly as second argument — it goes as ?doc_type= query param
      return api.compliance.upload(formData, docType);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vault"] });
      onClose();
    },
  });

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) handleFile(dropped);
  }, [handleFile]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Upload Document</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <div className="modal-body">
          <div className="field">
            <label className="field-label">Document Type</label>
            <div className="doc-type-grid">
              {DOC_TYPES.map(([key, m]) => (
                <button
                  key={key}
                  className={cn("doc-type-btn", docType === key && "doc-type-btn--active")}
                  style={docType === key ? { borderColor: m.color, background: m.color + "18" } : {}}
                  onClick={() => setDocType(key)}
                >
                  <span className="doc-type-abbr" style={{ color: m.color }}>{m.abbr}</span>
                  <span className="doc-type-name">{m.label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="field">
            <label className="field-label">File <span className="field-optional">(PDF only, max 10 MB)</span></label>
            <div
              className={cn("dropzone", dragOver && "dropzone--over", file && "dropzone--filled", fileError && "dropzone--error")}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileRef.current?.click()}
            >
              <input
                ref={fileRef}
                type="file"
                accept=".pdf,application/pdf"
                style={{ display: "none" }}
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
              />
              {file ? (
                <div className="dropzone-file">
                  <span className="dropzone-icon">📄</span>
                  <span className="dropzone-filename">{file.name}</span>
                  <span className="dropzone-size">{(file.size / 1024).toFixed(0)} KB</span>
                </div>
              ) : (
                <div className="dropzone-empty">
                  <span className="dropzone-icon">⬆</span>
                  <span>Drop PDF here or click to browse</span>
                  <span className="dropzone-hint">PDF only · Max 10 MB</span>
                </div>
              )}
            </div>
            {fileError && <div className="field-error">{fileError}</div>}
          </div>

          {meta.hasExpiry && (
            <div className="field">
              <label className="field-label">
                Expiry Date <span className="field-optional">(optional)</span>
              </label>
              <input
                type="date"
                className="field-input"
                value={expiresAt}
                min={new Date().toISOString().split("T")[0]}
                onChange={(e) => setExpiresAt(e.target.value)}
              />
            </div>
          )}

          {upload.isError && (
            <div className="error-banner">Upload failed. Please try again.</div>
          )}
        </div>

        <div className="modal-footer">
          <Button variant="outline" onClick={onClose} disabled={upload.isPending}>Cancel</Button>
          <Button
            onClick={() => upload.mutate()}
            disabled={!file || !!fileError || upload.isPending}
            style={{ background: meta.color }}
          >
            {upload.isPending ? "Uploading…" : "Upload Document"}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── Document Card ────────────────────────────────────────────────────────────

function DocCard({
  doc,
  onDelete,
  onDownload,
}: {
  doc: VaultDocument;
  onDelete: (id: string, filename: string) => void;
  onDownload: (id: string, filename: string) => void;
}) {
  const meta   = DOC_TYPE_META[doc.doc_type];
  const expiry = getExpiryBadge(doc);

  return (
    <div className={cn("doc-card", doc.is_expired && "doc-card--expired")}>
      <div className="doc-card-accent" style={{ background: meta.color }} />
      <div className="doc-card-inner">
        <div className="doc-card-header">
          <div className="doc-abbr" style={{ background: meta.color + "22", color: meta.color }}>
            {meta.abbr}
          </div>
          <div className="doc-info">
            <span className="doc-type-label">{meta.label}</span>
            <span className="doc-filename" title={doc.filename}>{doc.filename}</span>
          </div>
          <span className={cn("badge", expiry.cls)}>{expiry.label}</span>
        </div>

        <div className="doc-card-meta">
          <div className="doc-meta-item">
            <span className="meta-key">Uploaded</span>
            <span className="meta-val">{formatDate(doc.uploaded_at)}</span>
          </div>
          <div className="doc-meta-item">
            <span className="meta-key">Expires</span>
            <span className="meta-val">{formatDate(doc.expires_at)}</span>
          </div>
          <div className="doc-meta-item">
            <span className="meta-key">Version</span>
            <span className="meta-val">v{doc.version}</span>
          </div>
        </div>

        <div className="doc-card-actions">
          <button className="action-btn action-btn--download" onClick={() => onDownload(doc.id, doc.filename)}>
            ↓ Download
          </button>
          <button className="action-btn action-btn--delete" onClick={() => onDelete(doc.id, doc.filename)}>
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Stats Bar ────────────────────────────────────────────────────────────────

function StatsBar({ docs }: { docs: VaultDocument[] }) {
  const total        = docs.length;
  const expired      = docs.filter((d) => d.is_expired).length;
  const expiringSoon = docs.filter((d) => d.is_expiring_soon && !d.is_expired).length;
  const valid        = total - expired - expiringSoon;

  return (
    <div className="stats-bar">
      <div className="stat"><span className="stat-num">{total}</span><span className="stat-label">Total Documents</span></div>
      <div className="stat-divider" />
      <div className="stat"><span className="stat-num stat-num--green">{valid}</span><span className="stat-label">Valid</span></div>
      <div className="stat-divider" />
      <div className="stat"><span className="stat-num stat-num--amber">{expiringSoon}</span><span className="stat-label">Expiring Soon</span></div>
      <div className="stat-divider" />
      <div className="stat"><span className="stat-num stat-num--red">{expired}</span><span className="stat-label">Expired</span></div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function VaultPage() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  const [showUpload, setShowUpload]         = useState(false);
  const [filterType, setFilterType]         = useState<DocumentType | "all">("all");
  const [filterStatus, setFilterStatus]     = useState<"all" | "valid" | "expiring" | "expired">("all");
  const [deleteTarget, setDeleteTarget]     = useState<{ id: string; filename: string } | null>(null);
  const queryClient = useQueryClient();

  const { data: rawData, isLoading } = useQuery({
    queryKey: ["vault"],
    queryFn:  () => api.compliance.list(),
    staleTime: 0,
    enabled: mounted,
  });

  const docs: VaultDocument[] = Array.isArray(rawData)
    ? rawData
    : Array.isArray((rawData as any)?.data)
      ? (rawData as any).data
      : Array.isArray((rawData as any)?.documents)
        ? (rawData as any).documents
        : [];

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.compliance.delete(id),
    onSuccess:  () => {
      setDeleteTarget(null);
      queryClient.invalidateQueries({ queryKey: ["vault"] });
    },
  });

  const handleDownload = async (id: string, filename: string) => {
    try {
      const res = await api.compliance.download(id);
      const url = res?.url ?? res;
      if (!url) return;
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      requestAnimationFrame(() => {
        document.body.removeChild(a);
        if (url.startsWith("blob:")) URL.revokeObjectURL(url);
      });
    } catch { /* silent */ }
  };

  const filtered = docs.filter((d) => {
    if (filterType !== "all"       && d.doc_type !== filterType)                return false;
    if (filterStatus === "valid"    && (d.is_expired || d.is_expiring_soon))    return false;
    if (filterStatus === "expiring" && !d.is_expiring_soon)                     return false;
    if (filterStatus === "expired"  && !d.is_expired)                           return false;
    return true;
  });

  if (!mounted) {
    return (
      <div style={{ minHeight: "100vh", background: "#0F1117", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ width: 32, height: 32, border: "3px solid #3B82F6", borderTopColor: "transparent", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
      </div>
    );
  }

  return (
    <>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
        .vault-page{min-height:100vh;background:#0F1117;color:#E2E8F0;font-family:'DM Sans','Segoe UI',sans-serif;padding:32px 24px 64px;max-width:1200px;margin:0 auto}
        .vault-header{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:32px;gap:16px}
        .vault-title{font-size:28px;font-weight:700;letter-spacing:-0.5px;color:#F1F5F9;margin:0 0 4px}
        .vault-subtitle{font-size:14px;color:#64748B}
        .stats-bar{display:flex;align-items:center;background:#1E2130;border:1px solid #2D3148;border-radius:12px;padding:16px 24px;margin-bottom:24px}
        .stat{flex:1;text-align:center}
        .stat-divider{width:1px;height:36px;background:#2D3148;margin:0 8px}
        .stat-num{display:block;font-size:26px;font-weight:700;color:#F1F5F9}
        .stat-num--green{color:#10B981}.stat-num--amber{color:#F59E0B}.stat-num--red{color:#EF4444}
        .stat-label{font-size:11px;color:#64748B;text-transform:uppercase;letter-spacing:0.5px}
        .filters-row{display:flex;gap:8px;margin-bottom:24px;flex-wrap:wrap;align-items:center}
        .filter-chip{padding:6px 14px;border-radius:20px;border:1px solid #2D3148;background:transparent;color:#94A3B8;font-size:13px;cursor:pointer;transition:all .15s;white-space:nowrap}
        .filter-chip:hover{border-color:#4F5E8A;color:#E2E8F0}
        .filter-chip--active{background:#3B82F6;border-color:#3B82F6;color:#fff}
        .filter-sep{width:1px;height:24px;background:#2D3148;margin:0 4px}
        .doc-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px}
        .doc-card{background:#1E2130;border:1px solid #2D3148;border-radius:12px;overflow:hidden;transition:border-color .2s,transform .2s;display:flex}
        .doc-card:hover{border-color:#4F5E8A;transform:translateY(-2px)}
        .doc-card--expired{opacity:.7}
        .doc-card-accent{width:4px;flex-shrink:0}
        .doc-card-inner{flex:1;padding:16px}
        .doc-card-header{display:flex;align-items:flex-start;gap:12px;margin-bottom:12px}
        .doc-abbr{width:40px;height:40px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;flex-shrink:0;letter-spacing:.3px}
        .doc-info{flex:1;min-width:0}
        .doc-type-label{display:block;font-size:13px;font-weight:600;color:#E2E8F0}
        .doc-filename{display:block;font-size:11px;color:#64748B;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px}
        .badge{padding:3px 8px;border-radius:20px;font-size:11px;font-weight:600;flex-shrink:0}
        .badge-neutral{background:#2D3148;color:#94A3B8}
        .badge-green{background:#10B98122;color:#10B981}
        .badge-amber{background:#F59E0B22;color:#F59E0B}
        .badge-red{background:#EF444422;color:#EF4444}
        .doc-card-meta{display:flex;gap:16px;margin-bottom:14px}
        .doc-meta-item{display:flex;flex-direction:column;gap:2px}
        .meta-key{font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:.5px}
        .meta-val{font-size:12px;color:#94A3B8}
        .doc-card-actions{display:flex;gap:8px}
        .action-btn{flex:1;padding:7px 0;border-radius:7px;font-size:12px;font-weight:500;cursor:pointer;border:1px solid #2D3148;background:transparent;transition:all .15s}
        .action-btn--download{color:#60A5FA}.action-btn--download:hover{background:#3B82F620;border-color:#3B82F6}
        .action-btn--delete{color:#F87171}.action-btn--delete:hover{background:#EF444420;border-color:#EF4444}
        .empty-state{text-align:center;padding:80px 24px;background:#1E2130;border:1px dashed #2D3148;border-radius:16px;grid-column:1/-1}
        .empty-icon{font-size:48px;margin-bottom:16px}
        .empty-title{font-size:18px;font-weight:600;color:#E2E8F0;margin:0 0 8px}
        .empty-desc{font-size:14px;color:#64748B;max-width:400px;margin:0 auto 24px}
        .skeleton-card{background:#1E2130;border:1px solid #2D3148;border-radius:12px;height:160px;animation:pulse 1.5s ease-in-out infinite}
        .modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.7);backdrop-filter:blur(4px);z-index:50;display:flex;align-items:center;justify-content:center;padding:24px}
        .modal-card{background:#1E2130;border:1px solid #2D3148;border-radius:16px;width:100%;max-width:580px;max-height:85vh;overflow-y:auto;box-shadow:0 25px 60px rgba(0,0,0,.5)}
        .modal-header{display:flex;align-items:center;justify-content:space-between;padding:20px 24px 0}
        .modal-title{font-size:18px;font-weight:700;color:#F1F5F9}
        .modal-close{background:none;border:none;color:#64748B;cursor:pointer;font-size:18px;padding:4px}
        .modal-close:hover{color:#E2E8F0}
        .modal-body{padding:20px 24px}
        .modal-footer{display:flex;gap:10px;justify-content:flex-end;padding:0 24px 20px}
        .field{margin-bottom:20px}
        .field-label{display:block;font-size:12px;font-weight:600;color:#94A3B8;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
        .field-optional{font-weight:400;color:#475569;text-transform:none}
        .field-input{width:100%;padding:10px 12px;background:#0F1117;border:1px solid #2D3148;border-radius:8px;color:#E2E8F0;font-size:14px;outline:none;box-sizing:border-box}
        .field-input:focus{border-color:#3B82F6}
        .field-error{color:#FCA5A5;font-size:12px;margin-top:6px}
        .doc-type-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px}
        .doc-type-btn{display:flex;flex-direction:column;gap:4px;padding:10px 12px;background:#0F1117;border:1px solid #2D3148;border-radius:8px;cursor:pointer;transition:all .15s;text-align:left}
        .doc-type-btn:hover{border-color:#4F5E8A}
        .doc-type-abbr{font-size:11px;font-weight:700}
        .doc-type-name{font-size:11px;color:#94A3B8;line-height:1.3}
        .dropzone{border:2px dashed #2D3148;border-radius:10px;padding:28px;text-align:center;cursor:pointer;transition:all .15s;color:#64748B;font-size:13px}
        .dropzone:hover,.dropzone--over{border-color:#3B82F6;background:#3B82F608}
        .dropzone--filled{border-style:solid;border-color:#10B981;background:#10B98108}
        .dropzone--error{border-color:#EF4444;background:#EF444408}
        .dropzone-icon{display:block;font-size:24px;margin-bottom:8px}
        .dropzone-hint{display:block;font-size:11px;color:#475569;margin-top:4px}
        .dropzone-file{display:flex;align-items:center;gap:10px;justify-content:center}
        .dropzone-filename{color:#E2E8F0;font-weight:500}
        .dropzone-size{color:#64748B}
        .dropzone-empty{display:flex;flex-direction:column;align-items:center;gap:4px}
        .error-banner{background:#EF444420;border:1px solid #EF4444;color:#FCA5A5;padding:10px 14px;border-radius:8px;font-size:13px;margin-top:8px}
        .confirm-card{background:#1E2130;border:1px solid #2D3148;border-radius:16px;padding:32px 28px;max-width:400px;width:100%;text-align:center;box-shadow:0 25px 60px rgba(0,0,0,.5)}
        .confirm-icon{font-size:40px;margin-bottom:16px}
        .confirm-title{font-size:18px;font-weight:700;color:#F1F5F9;margin:0 0 10px}
        .confirm-desc{font-size:14px;color:#94A3B8;margin:0 0 24px;line-height:1.5}
        .confirm-actions{display:flex;gap:10px;justify-content:center}
      `}</style>

      <div className="vault-page">
        <div className="vault-header">
          <div>
            <h1 className="vault-title">Compliance Vault</h1>
            <p className="vault-subtitle">Store and manage your documents for instant use in tender applications.</p>
          </div>
          <Button onClick={() => setShowUpload(true)}>+ Upload Document</Button>
        </div>

        {!isLoading && docs.length > 0 && <StatsBar docs={docs} />}

        {docs.length > 0 && (
          <div className="filters-row">
            {(["all", "valid", "expiring", "expired"] as const).map((s) => (
              <button
                key={s}
                className={cn("filter-chip", filterStatus === s && "filter-chip--active")}
                onClick={() => setFilterStatus(s)}
              >
                {s === "all" ? "All Status" : s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
            <div className="filter-sep" />
            <button
              className={cn("filter-chip", filterType === "all" && "filter-chip--active")}
              onClick={() => setFilterType("all")}
            >
              All Types
            </button>
            {DOC_TYPES.map(([key, m]) => (
              <button
                key={key}
                className={cn("filter-chip", filterType === key && "filter-chip--active")}
                style={filterType === key ? { background: m.color, borderColor: m.color } : {}}
                onClick={() => setFilterType(key)}
              >
                {m.abbr}
              </button>
            ))}
          </div>
        )}

        <div className="doc-grid">
          {isLoading ? (
            Array.from({ length: 6 }).map((_, i) => <div key={i} className="skeleton-card" />)
          ) : filtered.length === 0 && docs.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">🗂️</div>
              <h3 className="empty-title">No documents yet</h3>
              <p className="empty-desc">Upload your compliance documents once and reuse them across all tender applications.</p>
              <Button onClick={() => setShowUpload(true)}>Upload your first document</Button>
            </div>
          ) : filtered.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">🔍</div>
              <h3 className="empty-title">No documents match filters</h3>
              <p className="empty-desc">Try adjusting the status or type filter above.</p>
            </div>
          ) : (
            filtered.map((doc) => (
              <DocCard
                key={doc.id}
                doc={doc}
                onDelete={(id, filename) => setDeleteTarget({ id, filename })}
                onDownload={handleDownload}
              />
            ))
          )}
        </div>
      </div>

      {showUpload && <UploadModal onClose={() => setShowUpload(false)} />}

      {deleteTarget && (
        <DeleteDialog
          filename={deleteTarget.filename}
          onConfirm={() => deleteMutation.mutate(deleteTarget.id)}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </>
  );
}
