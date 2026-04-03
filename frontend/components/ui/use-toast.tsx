"use client";

import { useState, useCallback, useEffect } from "react";

type ToastType = "success" | "error" | "info" | "warning";

interface Toast {
  id: string;
  message: string;
  type: ToastType;
}

const COLORS: Record<ToastType, { bg: string; border: string; color: string }> = {
  success: { bg: "#10B98115", border: "#10B981", color: "#059669" },
  error:   { bg: "#EF444415", border: "#EF4444", color: "#DC2626" },
  warning: { bg: "#F59E0B15", border: "#F59E0B", color: "#B45309" },
  info:    { bg: "#3B82F615", border: "#3B82F6", color: "#1D4ED8" },
};

const ICONS: Record<ToastType, string> = {
  success: "✓",
  error: "✕",
  warning: "⚠",
  info: "ℹ",
};

// Simple global store
let _toasts: Toast[] = [];
let _listeners: Array<(toasts: Toast[]) => void> = [];

function notify() {
  _listeners.forEach((l) => l([..._toasts]));
}

export function toast(message: string, type: ToastType = "info") {
  const id = Math.random().toString(36).slice(2);
  _toasts = [..._toasts, { id, message, type }];
  notify();
  setTimeout(() => {
    _toasts = _toasts.filter((t) => t.id !== id);
    notify();
  }, 4000);
}

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const listener = (t: Toast[]) => setToasts(t);
    _listeners.push(listener);
    return () => {
      _listeners = _listeners.filter((l) => l !== listener);
    };
  }, []);

  const dismiss = useCallback((id: string) => {
    _toasts = _toasts.filter((t) => t.id !== id);
    notify();
  }, []);

  return { toasts, dismiss };
}

export function ToastContainer() {
  const { toasts, dismiss } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div
      style={{
        position: "fixed",
        bottom: 24,
        right: 24,
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        gap: 8,
        maxWidth: 380,
      }}
    >
      {toasts.map((t) => {
        const c = COLORS[t.type];
        return (
          <div
            key={t.id}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "12px 16px",
              borderRadius: 10,
              background: c.bg,
              border: `1px solid ${c.border}`,
              color: c.color,
              fontSize: 14,
              fontWeight: 500,
              boxShadow: "0 4px 20px rgba(0,0,0,0.12)",
              animation: "toast-in 0.25s ease",
            }}
          >
            <style>{`@keyframes toast-in { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:none; } }`}</style>
            <span style={{ fontSize: 16, flexShrink: 0 }}>{ICONS[t.type]}</span>
            <span style={{ flex: 1 }}>{t.message}</span>
            <button
              onClick={() => dismiss(t.id)}
              style={{ background: "none", border: "none", cursor: "pointer", color: c.color, fontSize: 16, padding: 0, opacity: 0.6 }}
            >
              ✕
            </button>
          </div>
        );
      })}
    </div>
  );
}
