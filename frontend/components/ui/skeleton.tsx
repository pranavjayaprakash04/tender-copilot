"use client";
import React from "react";

interface SkeletonProps {
  className?: string;
  style?: React.CSSProperties;
  width?: number | string;
  height?: number | string;
  rounded?: boolean;
}

export function Skeleton({ className, style, width, height, rounded }: SkeletonProps) {
  return (
    <div
      className={className}
      style={{
        display: "inline-block",
        background: "linear-gradient(90deg, #e5e7eb 25%, #f3f4f6 50%, #e5e7eb 75%)",
        backgroundSize: "200% 100%",
        animation: "skeleton-shimmer 1.5s ease-in-out infinite",
        borderRadius: rounded ? 9999 : 6,
        width: width ?? "100%",
        height: height ?? 16,
        ...style,
      }}
    >
      <style>{`
        @keyframes skeleton-shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </div>
  );
}

export default Skeleton;
