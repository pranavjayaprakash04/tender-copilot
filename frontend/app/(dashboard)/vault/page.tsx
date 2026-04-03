"use client";

export const dynamic = 'force-dynamic';

import ComplianceVault from '@/src/components/ComplianceVault';

export default function VaultPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <ComplianceVault />
      </div>
    </div>
  );
}
