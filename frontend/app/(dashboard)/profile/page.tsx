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

  const Field = ({
    label,
    field,
    placeholder,
    type = "text",
  }: {
    label: string;
    field: keyof CompanyProfile;
    placeholder?: string;
    type?: string;
  }) => (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {isEditing ? (
        <input
          type={type}
          value={formData[field] || ""}
          onChange={(e) => handleChange(field, e.target.value)}
          placeholder={placeholder}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
        />
      ) : (
        <p className="text-sm text-gray-900 py-2">
          {formData[field] || <span className="text-gray-400">Not set</span>}
        </p>
      )}
    </div>
  );

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

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Profile</h1>
          <div className="flex gap-2 items-center">
            {saved && (
              <span className="text-green-600 text-sm font-medium">
                ✓ Saved successfully
              </span>
            )}
            {isEditing ? (
              <>
                <Button variant="outline" onClick={() => setIsEditing(false)}>
                  Cancel
                </Button>
                <Button
                  onClick={() => mutation.mutate(formData)}
                  disabled={mutation.isPending}
                >
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
            <Field label="Company Name" field="company_name" placeholder="Pynevera Technologies Pvt Ltd" />
            <Field label="Business Type" field="business_type" placeholder="Private Limited" />
            <Field label="Industry" field="industry" placeholder="IT / Software" />
            <Field label="Annual Turnover" field="annual_turnover" placeholder="e.g. 50 Lakhs" />
            <Field label="Employee Count" field="employee_count" placeholder="e.g. 10" />
            <Field label="Website" field="website" placeholder="https://yourcompany.com" type="url" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Tax & Registration</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Field label="GSTIN" field="gstin" placeholder="22AAAAA0000A1Z5" />
            <Field label="PAN" field="pan" placeholder="AAAAA0000A" />
            <Field label="Registration Number" field="registration_number" placeholder="CIN / MSME No." />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Contact & Address</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Field label="Contact Email" field="contact_email" placeholder="contact@yourcompany.com" type="email" />
            <Field label="Contact Phone" field="contact_phone" placeholder="+91 98765 43210" />
            <Field label="Address" field="address" placeholder="Street address" />
            <Field label="City" field="city" placeholder="Coimbatore" />
            <Field label="State" field="state" placeholder="Tamil Nadu" />
            <Field label="Pincode" field="pincode" placeholder="641001" />
          </div>
        </div>

        <p className="text-xs text-gray-400 mt-4 text-center">
          Completing your profile improves tender match scores and AI eligibility analysis.
        </p>
      </div>
    </div>
  );
}
