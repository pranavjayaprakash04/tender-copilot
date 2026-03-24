"use client";
export const dynamic = "force-dynamic";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { createClient } from "@supabase/supabase-js";
import api from "@/lib/api";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

type CompanyProfile = {
  id?: string;
  name?: string;
  registration_number?: string;
  gstin?: string;
  industry?: string;
  state?: string;
  website?: string;
  contact_email?: string;
  contact_phone?: string;
  [key: string]: any;
};

const INDUSTRIES = [
  "Construction", "IT & Software", "Consulting", "Manufacturing",
  "Healthcare", "Education", "Infrastructure", "Defense", "Other",
];

const INDIAN_STATES = [
  "Andhra Pradesh", "Assam", "Bihar", "Chhattisgarh", "Delhi", "Goa",
  "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
  "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
  "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
  "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
  "West Bengal",
];

function InitialAvatar({ name, email }: { name?: string; email?: string }) {
  const letter = (name || email || "?")[0].toUpperCase();
  return (
    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center text-white text-2xl font-bold shadow-lg">
      {letter}
    </div>
  );
}

export default function ProfilePage() {
  const qc = useQueryClient();
  const [user, setUser] = useState<any>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<CompanyProfile>({});
  const [saved, setSaved] = useState(false);

  // Load Supabase user
  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => setUser(data.user));
  }, []);

  // Load company profile
  const { data: profile, isLoading } = useQuery<CompanyProfile>({
    queryKey: ["company-profile"],
    queryFn: async () => {
      try {
        return await api.companies.getProfile();
      } catch {
        return {};
      }
    },
    retry: 1,
  });

  useEffect(() => {
    if (profile) setForm(profile);
  }, [profile]);

  const updateProfile = useMutation({
    mutationFn: (data: CompanyProfile) => api.companies.updateProfile(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["company-profile"] });
      setEditing(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
  });

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    window.location.href = "/";
  };

  const field = (key: keyof CompanyProfile) => ({
    value: form[key] ?? "",
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value })),
  });

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">

        {/* Header */}
        <h1 className="text-3xl font-bold text-gray-900">Profile</h1>

        {/* Account card */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-4">Account</h2>
          <div className="flex items-center gap-4">
            <InitialAvatar name={user?.user_metadata?.full_name} email={user?.email} />
            <div>
              <p className="font-semibold text-gray-900 text-lg">
                {user?.user_metadata?.full_name || "Your Account"}
              </p>
              <p className="text-gray-500 text-sm">{user?.email}</p>
              <p className="text-gray-400 text-xs mt-0.5">
                Joined {user?.created_at ? new Date(user.created_at).toLocaleDateString("en-IN", { month: "long", year: "numeric" }) : "—"}
              </p>
            </div>
          </div>
        </div>

        {/* Company profile card */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">Company Profile</h2>
            {!editing && (
              <button
                onClick={() => setEditing(true)}
                className="text-sm font-medium text-blue-600 hover:text-blue-700"
              >
                Edit
              </button>
            )}
          </div>

          {isLoading ? (
            <div className="space-y-3 animate-pulse">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-10 bg-gray-100 rounded-lg" />
              ))}
            </div>
          ) : editing ? (
            <form
              onSubmit={(e) => { e.preventDefault(); updateProfile.mutate(form); }}
              className="space-y-4"
            >
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <InputField label="Company Name" {...field("name")} />
                <InputField label="Registration Number" {...field("registration_number")} />
                <InputField label="GSTIN" {...field("gstin")} placeholder="22AAAAA0000A1Z5" />
                <InputField label="Website" {...field("website")} placeholder="https://" />
                <InputField label="Contact Email" type="email" {...field("contact_email")} />
                <InputField label="Contact Phone" {...field("contact_phone")} placeholder="+91" />

                <div className="flex flex-col gap-1">
                  <label className="text-xs font-medium text-gray-500">Industry</label>
                  <select
                    {...field("industry")}
                    className="border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                  >
                    <option value="">Select industry</option>
                    {INDUSTRIES.map((i) => <option key={i}>{i}</option>)}
                  </select>
                </div>

                <div className="flex flex-col gap-1">
                  <label className="text-xs font-medium text-gray-500">State</label>
                  <select
                    {...field("state")}
                    className="border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                  >
                    <option value="">Select state</option>
                    {INDIAN_STATES.map((s) => <option key={s}>{s}</option>)}
                  </select>
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  disabled={updateProfile.isPending}
                  className="px-5 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 disabled:opacity-50 transition-colors"
                >
                  {updateProfile.isPending ? "Saving…" : "Save Changes"}
                </button>
                <button
                  type="button"
                  onClick={() => { setEditing(false); setForm(profile ?? {}); }}
                  className="px-5 py-2 border border-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
              </div>

              {updateProfile.isError && (
                <p className="text-sm text-red-600">Failed to save. Please try again.</p>
              )}
            </form>
          ) : (
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
              <ProfileField label="Company Name" value={profile?.name} />
              <ProfileField label="Registration Number" value={profile?.registration_number} />
              <ProfileField label="GSTIN" value={profile?.gstin} />
              <ProfileField label="Industry" value={profile?.industry} />
              <ProfileField label="State" value={profile?.state} />
              <ProfileField label="Website" value={profile?.website} />
              <ProfileField label="Contact Email" value={profile?.contact_email} />
              <ProfileField label="Contact Phone" value={profile?.contact_phone} />
            </dl>
          )}

          {saved && (
            <div className="mt-4 flex items-center gap-2 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-4 py-2">
              <span>✓</span> Profile saved successfully
            </div>
          )}
        </div>

        {/* Danger zone */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-4">Account Actions</h2>
          <button
            onClick={handleSignOut}
            className="px-5 py-2 border border-red-200 text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 transition-colors"
          >
            Sign out
          </button>
        </div>

      </div>
    </div>
  );
}

function InputField({
  label, type = "text", placeholder, value, onChange,
}: {
  label: string; type?: string; placeholder?: string;
  value: string; onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-gray-500">{label}</label>
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        className="border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-900 placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
  );
}

function ProfileField({ label, value }: { label: string; value?: string }) {
  return (
    <div>
      <dt className="text-xs font-medium text-gray-400 mb-0.5">{label}</dt>
      <dd className="text-sm font-medium text-gray-800">{value || <span className="text-gray-300 font-normal">Not set</span>}</dd>
    </div>
  );
}
