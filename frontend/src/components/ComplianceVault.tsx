import React, { useState, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, File, AlertCircle, CheckCircle, Clock, Trash2, Eye, Download, Filter, Search } from 'lucide-react';
import { format } from 'date-fns';
import { api } from '@/lib/api';
import { createClient } from '@supabase/supabase-js';

export const dynamic = 'force-dynamic';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

interface Document {
  id: string;
  filename: string;
  doc_type: string;
  version: number;
  expires_at?: string;
  is_current: boolean;
  uploaded_at: string;
  file_size?: number;
  download_url?: string;
}

interface DocumentStats {
  total_documents: number;
  current_documents: number;
  expired_documents: number;
  expiring_soon_documents: number;
  by_type: Record<string, number>;
  upcoming_expiries: Document[];
}

const ComplianceVault: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [stats, setStats] = useState<DocumentStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch documents and stats on mount
  React.useEffect(() => {
    fetchDocuments();
    fetchStats();
  }, []);

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const data = await api.compliance.getDocuments();
      setDocuments(data || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch documents');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      // For now, we'll calculate stats from documents
      // This endpoint might need to be implemented in the backend
      if (documents.length > 0) {
        const total = documents.length;
        const current = documents.filter(doc => doc.is_current).length;
        const expired = documents.filter(doc => 
          doc.expires_at && new Date(doc.expires_at) < new Date()
        ).length;
        const expiringSoon = documents.filter(doc => 
          doc.expires_at && 
          new Date(doc.expires_at) <= new Date(Date.now() + 30 * 24 * 60 * 60 * 1000) &&
          new Date(doc.expires_at) > new Date()
        ).length;
        
        setStats({
          total_documents: total,
          current_documents: current,
          expired_documents: expired,
          expiring_soon_documents: expiringSoon,
          by_type: documents.reduce((acc, doc) => {
            acc[doc.doc_type] = (acc[doc.doc_type] || 0) + 1;
            return acc;
          }, {} as Record<string, number>),
          upcoming_expiries: documents
            .filter(doc => doc.expires_at && new Date(doc.expires_at) > new Date())
            .sort((a, b) => new Date(a.expires_at!).getTime() - new Date(b.expires_at!).getTime())
            .slice(0, 5)
        });
      }
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;
    
    setUploading(true);
    setError(null);
    
    for (const file of acceptedFiles) {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setError('Only PDF files are supported');
        setUploading(false);
        return;
      }
      
      if (file.size > 10 * 1024 * 1024) {
        setError('File size exceeds 10MB limit');
        setUploading(false);
        return;
      }
      
      try {
        // Upload the file using the API
        await api.compliance.uploadDocument(file);
        
        setSuccess(`Successfully uploaded ${file.name}`);
        fetchDocuments();
      } catch (err) {
        setError(err instanceof Error ? err.message : `Failed to upload ${file.name}`);
      }
    }
    
    setUploading(false);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    multiple: true,
    disabled: uploading
  });

  const deleteDocument = async (docId: string) => {
    if (!confirm('Are you sure you want to delete this document?')) return;
    
    try {
      // This endpoint might need to be implemented in the backend
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/compliance/documents/${docId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`,
        }
      });
      
      if (!response.ok) throw new Error('Failed to delete document');
      
      setSuccess('Document deleted successfully');
      fetchDocuments();
      fetchStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document');
    }
  };

  const downloadDocument = async (docId: string, filename: string) => {
    try {
      // This endpoint might need to be implemented in the backend
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/compliance/documents/${docId}/download`, {
        headers: {
          'Authorization': `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`,
        }
      });
      
      if (!response.ok) throw new Error('Failed to get download URL');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to download document');
    }
  };

  const filteredDocuments = documents.filter(doc => {
    const matchesSearch = doc.filename.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = filterType === 'all' || doc.doc_type === filterType;
    const matchesStatus = filterStatus === 'all' || 
      (filterStatus === 'current' && doc.is_current) ||
      (filterStatus === 'expired' && new Date(doc.expires_at || '') < new Date()) ||
      (filterStatus === 'expiring' && doc.expires_at && 
       new Date(doc.expires_at) <= new Date(Date.now() + 30 * 24 * 60 * 60 * 1000));
    
    return matchesSearch && matchesType && matchesStatus;
  });

  const getDocumentTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      gst: 'GST Certificate',
      pan: 'PAN Card',
      iso: 'ISO Certification',
      udyam: 'Udyam Registration',
      trade_license: 'Trade License',
      bank_guarantee: 'Bank Guarantee',
      experience_certificate: 'Experience Certificate',
      financial_statement: 'Financial Statement',
      tax_clearance: 'Tax Clearance',
      emolument_certificate: 'Emolument Certificate',
      other: 'Other'
    };
    return labels[type] || type;
  };

  const getStatusColor = (doc: Document) => {
    if (!doc.is_current) return 'bg-gray-100 text-gray-800';
    if (!doc.expires_at) return 'bg-green-100 text-green-800';
    if (new Date(doc.expires_at) < new Date()) return 'bg-red-100 text-red-800';
    if (new Date(doc.expires_at) <= new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)) {
      return 'bg-yellow-100 text-yellow-800';
    }
    return 'bg-green-100 text-green-800';
  };

  const getStatusText = (doc: Document) => {
    if (!doc.is_current) return 'Superseded';
    if (!doc.expires_at) return 'Valid';
    if (new Date(doc.expires_at) < new Date()) return 'Expired';
    if (new Date(doc.expires_at) <= new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)) {
      return 'Expiring Soon';
    }
    return 'Valid';
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Compliance Vault</h1>
        <p className="text-gray-600 mt-2">Manage your compliance documents and certificates</p>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <File className="h-8 w-8 text-blue-600" />
              <div className="ml-4">
                <p className="text-sm text-gray-600">Total Documents</p>
                <p className="text-2xl font-bold text-gray-900">{stats.total_documents}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <CheckCircle className="h-8 w-8 text-green-600" />
              <div className="ml-4">
                <p className="text-sm text-gray-600">Current</p>
                <p className="text-2xl font-bold text-gray-900">{stats.current_documents}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <Clock className="h-8 w-8 text-yellow-600" />
              <div className="ml-4">
                <p className="text-sm text-gray-600">Expiring Soon</p>
                <p className="text-2xl font-bold text-gray-900">{stats.expiring_soon_documents}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <AlertCircle className="h-8 w-8 text-red-600" />
              <div className="ml-4">
                <p className="text-sm text-gray-600">Expired</p>
                <p className="text-2xl font-bold text-gray-900">{stats.expired_documents}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Upload Area */}
      <div className="bg-white rounded-lg shadow mb-8">
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            isDragActive
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400'
          } ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <input {...getInputProps()} />
          <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          {uploading ? (
            <p className="text-gray-600">Uploading...</p>
          ) : isDragActive ? (
            <p className="text-blue-600">Drop the files here...</p>
          ) : (
            <div>
              <p className="text-gray-600 mb-2">Drag & drop PDF files here, or click to select</p>
              <p className="text-sm text-gray-500">Maximum file size: 10MB</p>
            </div>
          )}
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex items-center">
          <AlertCircle className="h-5 w-5 text-red-600 mr-3" />
          <p className="text-red-800">{error}</p>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-red-600 hover:text-red-800"
          >
            ×
          </button>
        </div>
      )}

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6 flex items-center">
          <CheckCircle className="h-5 w-5 text-green-600 mr-3" />
          <p className="text-green-800">{success}</p>
          <button
            onClick={() => setSuccess(null)}
            className="ml-auto text-green-600 hover:text-green-800"
          >
            ×
          </button>
        </div>
      )}

      {/* Filters and Search */}
      <div className="bg-white rounded-lg shadow mb-6 p-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search documents..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg w-full focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Types</option>
            <option value="gst">GST Certificate</option>
            <option value="pan">PAN Card</option>
            <option value="iso">ISO Certification</option>
            <option value="udyam">Udyam Registration</option>
            <option value="trade_license">Trade License</option>
            <option value="bank_guarantee">Bank Guarantee</option>
            <option value="experience_certificate">Experience Certificate</option>
            <option value="financial_statement">Financial Statement</option>
            <option value="tax_clearance">Tax Clearance</option>
            <option value="emolument_certificate">Emolument Certificate</option>
            <option value="other">Other</option>
          </select>
          
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Status</option>
            <option value="current">Current</option>
            <option value="expiring">Expiring Soon</option>
            <option value="expired">Expired</option>
          </select>
        </div>
      </div>

      {/* Documents List */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            Documents ({filteredDocuments.length})
          </h2>
        </div>
        
        {loading ? (
          <div className="p-8 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-2 text-gray-600">Loading documents...</p>
          </div>
        ) : filteredDocuments.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <File className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <p>No documents found</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {filteredDocuments.map((doc) => (
              <div key={doc.id} className="p-6 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <File className="h-8 w-8 text-gray-400" />
                    <div>
                      <h3 className="text-sm font-medium text-gray-900">{doc.filename}</h3>
                      <p className="text-sm text-gray-500">
                        {getDocumentTypeLabel(doc.doc_type)} • Version {doc.version}
                      </p>
                      <p className="text-xs text-gray-400">
                        Uploaded {format(new Date(doc.uploaded_at), 'MMM d, yyyy')}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-4">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(doc)}`}>
                      {getStatusText(doc)}
                    </span>
                    
                    {doc.expires_at && (
                      <p className="text-sm text-gray-500">
                        Expires {format(new Date(doc.expires_at), 'MMM d, yyyy')}
                      </p>
                    )}
                    
                    <div className="flex space-x-2">
                      <button
                        onClick={() => downloadDocument(doc.id, doc.filename)}
                        className="p-2 text-gray-600 hover:text-blue-600 transition-colors"
                        title="Download"
                      >
                        <Download className="h-4 w-4" />
                      </button>
                      
                      <button
                        onClick={() => deleteDocument(doc.id)}
                        className="p-2 text-gray-600 hover:text-red-600 transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ComplianceVault;
