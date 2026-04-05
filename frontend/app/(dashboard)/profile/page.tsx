"use client";
export const dynamic = "force-dynamic";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useLang } from "@/src/components/LanguageContext";

interface CompanyProfile {
  name?: string;
  industry?: string;
  location?: string;
  contact_email?: string;
  contact_phone?: string;
  website?: string;
  description?: string;
  capabilities_text?: string;
  gstin?: string;
  udyam_number?: string;
  turnover_range?: string;
}

function Field({
  label, field, value, placeholder, type = "text", isEditing, onChange, required,
}: {
  label: string; field: keyof CompanyProfile; value: string;
  placeholder?: string; type?: string; isEditing: boolean;
  onChange: (field: keyof CompanyProfile, value: string) => void; required?: boolean;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}{required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {isEditing ? (
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(field, e.target.value)}
          placeholder={placeholder}
          required={required}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
        />
      ) : (
        <p className="text-sm text-gray-900 py-2">
          {value || <span className="text-gray-400">Not set</span>}
        </p>
      )}
    </div>
  );
}

export default function ProfilePage() {
  const { t } = useLang();
  const queryClient = useQueryClient();
  const [saved, setSaved] = useState(false);
  const [formData, setFormData] = useState<CompanyProfile>({});
  const [isEditing, setIsEditing] = useState(false);
  const [noProfile, setNoProfile] = useState(false);
  const [validationError, setValidationError] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["company-profile"],
    queryFn: () => api.company.getProfile().catch(() => null),
  });

  useEffect(() => {
    if (data) {
      setFormData((data as CompanyProfile) || {});
      setNoProfile(false);
    } else if (data === null) {
      setNoProfile(true);
    }
  }, [data]);

  const mutation = useMutation({
    mutationFn: async (d: CompanyProfile) => {
      if (noProfile) {
        return (api.company as any).createProfile(d);
      }
      return api.company.updateProfile(d as Record<string, unknown>);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["company-profile"] });
      setSaved(true);
      setIsEditing(false);
      setNoProfile(false);
      setValidationError("");
      setTimeout(() => setSaved(false), 3000);
    },
    onError: (err: any) => {
      setValidationError(err?.message || "Save failed");
    },
  });

  const handleChange = (field: keyof CompanyProfile, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    setValidationError("");
    // Validate required fields
    if (!formData.name?.trim()) { setValidationError("Company Name is required"); return; }
    if (!formData.industry?.trim()) { setValidationError("Industry is required"); return; }
    if (!formData.location?.trim()) { setValidationError("Location is required"); return; }
    if (!formData.contact_email?.trim()) { setValidationError("Contact Email is required"); return; }
    mutation.mutate(formData);
  };

  const f = (field: keyof CompanyProfile, label: string, placeholder?: string, type = "text", required = false) => (
    <Field
      key={field} label={label} field={field}
      value={formData[field] || ""} placeholder={placeholder}
      type={type} isEditing={isEditing} onChange={handleChange} required={required}
    />
  );

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-6">Profile</h1>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 animate-pulse">
            <div className="space-y-4">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-10 bg-gray-200 rounded" />)}</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Profile</h1>
          <div className="flex gap-2 items-center">
            {saved && <span className="text-green-600 text-sm font-medium">✓ Saved</span>}
            {isEditing ? (
              <>
                <Button variant="outline" onClick={() => { setIsEditing(false); setValidationError(""); }}>Cancel</Button>
                <Button onClick={handleSave} disabled={mutation.isPending}>
                  {mutation.isPending ? t("Saving...","சேமிக்கிறது...") : t("Save Changes","மாற்றங்களை சேமி")}
                </Button>
              </>
            ) : (
              <Button onClick={() => setIsEditing(true)}>Edit Profile</Button>
            )}
          </div>
        </div>

        {validationError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm text-red-700">
            ⚠ {validationError}
          </div>
        )}

        {noProfile && !isEditing && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 text-sm text-blue-800">
            No company profile yet. Click <strong>Edit Profile</strong> to create one.
          </div>
        )}

        {/* Contact first — required fields visible immediately */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Contact <span className="text-xs text-gray-400 font-normal">(required to save)</span></h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {f("contact_email", t("Contact Email","தொடர்பு மின்னஞ்சல்"), "contact@yourcompany.com", "email", true)}
            {f("contact_phone", t("Contact Phone","தொடர்பு தொலைபேசி"), "+91 98765 43210")}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Company Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {f("name", t("Company Name","நிறுவன பெயர்"), "Pynevera Technologies Pvt Ltd", "text", true)}
            {f("industry", t("Industry","தொழில்"), "IT / Software", "text", true)}
            {f("location", t("Location / State","இடம் / மாநிலம்"), "Coimbatore, Tamil Nadu", "text", true)}
            {f("turnover_range", t("Turnover Range","வருவாய் வரம்பு"), "Below ₹40L")}
            {f("website", t("Website","இணையதளம்"), "https://yourcompany.com", "url")}
            {f("description", t("Description","விளக்கம்"), "Brief company description")}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Registration</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {f("gstin", t("GSTIN","GSTIN"), "22AAAAA0000A1Z5")}
            {f("udyam_number", t("Udyam Number","உத்யம் எண்"), "UDYAM-TN-00-0000000")}
            {f("capabilities_text", t("Capabilities","திறன்கள்"), "e.g. Software development, AI, Cloud")}
          </div>
        </div>

        <p className="text-xs text-gray-400 mt-4 text-center">
          Fields marked * are required. Completing your profile improves tender match scores.
        </p>
      </div>
    </div>
  );
}
