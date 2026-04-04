"use client";
export const dynamic = "force-dynamic";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

interface CompanyProfile {
  company_name?: string;
  gstin?: string;
  pan?: string;
  registration_number?: string;
  business_type?: string;
  industry?: string;
  annual_turnover?: string;
  employee_count?: string;
  address?: string;
  city?: string;
  state?: string;
  pincode?: string;
  contact_email?: string;
  contact_phone?: string;
  website?: string;
}

// Field MUST be outside ProfilePage — if defined inside, it remounts on every
// keystroke causing the input to lose focus after each character typed.
function Field({
  label,
  field,
  value,
  placeholder,
  type = "text",
  isEditing,
  onChange,
}: {
  label: string;
  field: keyof CompanyProfile;
  value: string;
  placeholder?: string;
  type?: string;
  isEditing: boolean;
  onChange: (field: keyof CompanyProfile, value: string) => void;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {isEditing ? (
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(field, e.target.value)}
          placeholder={placeholder}
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
  const queryClient = useQueryClient();
  const [saved, setSaved] = useState(false);
  const [formData, setFormData] = useState<CompanyProfile>({});
  const [isEditing, setIsEditing] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["company-profile"],
    queryFn: () => api.company.getProfile(),
  });

  useEffect(() => {
    if (data) {
      setFormData((data as CompanyProfile) || {});
    }
  }, [data]);

  const mutation = useMutation({
    mutationFn: (d: CompanyProfile) =>
      api.company.updateProfile(d as Record<string, unknown>),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["company-profile"] });
      setSaved(true);
      setIsEditing(false);
      setTimeout(() => setSaved(false), 3000);
    },
  });

  const handleChange = (field: keyof CompanyProfile, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-6">Profile</h1>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 animate-pulse">
            <div className="space-y-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="h-10 bg-gray-200 rounded" />
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  const f = (field: keyof CompanyProfile, label: string, placeholder?: string, type = "text") => (
    <Field
      key={field}
      label={label}
      field={field}
      value={formData[field] || ""}
      placeholder={placeholder}
      type={type}
      isEditing={isEditing}
      onChange={handleChange}
    />
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Profile</h1>
          <div className="flex gap-2 items-center">
            {saved && (
              <span className="text-green-600 text-sm font-medium">✓ Saved</span>
            )}
            {isEditing ? (
              <>
                <Button variant="outline" onClick={() => setIsEditing(false)}>Cancel</Button>
                <Button onClick={() => mutation.mutate(formData)} disabled={mutation.isPending}>
                  {mutation.isPending ? "Saving..." : "Save Changes"}
                </Button>
              </>
            ) : (
              <Button onClick={() => setIsEditing(true)}>Edit Profile</Button>
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Company Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {f("company_name", "Company Name", "Pynevera Technologies Pvt Ltd")}
            {f("business_type", "Business Type", "Private Limited")}
            {f("industry", "Industry", "IT / Software")}
            {f("annual_turnover", "Annual Turnover", "e.g. 50 Lakhs")}
            {f("employee_count", "Employee Count", "e.g. 10")}
            {f("website", "Website", "https://yourcompany.com", "url")}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Tax & Registration</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {f("gstin", "GSTIN", "22AAAAA0000A1Z5")}
            {f("pan", "PAN", "AAAAA0000A")}
            {f("registration_number", "Registration Number", "CIN / MSME No.")}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Contact & Address</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {f("contact_email", "Contact Email", "contact@yourcompany.com", "email")}
            {f("contact_phone", "Contact Phone", "+91 98765 43210")}
            {f("address", "Address", "Street address")}
            {f("city", "City", "Coimbatore")}
            {f("state", "State", "Tamil Nadu")}
            {f("pincode", "Pincode", "641001")}
          </div>
        </div>

        <p className="text-xs text-gray-400 mt-4 text-center">
          Completing your profile improves tender match scores and AI eligibility analysis.
        </p>
      </div>
    </div>
  );
}
