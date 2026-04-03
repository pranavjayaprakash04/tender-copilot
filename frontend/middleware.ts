import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Paths that do NOT require authentication
const PUBLIC_PATHS = [
  "/",
  "/login",
  "/register",
  "/auth",
  "/auth/callback",
  "/auth/confirm",
  "/auth/reset-password",
];

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.some(
    (p) => pathname === p || pathname.startsWith(p + "/")
  );
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Always allow public paths — this is the fix for the /register 307 redirect
  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  // NOTE: Full session enforcement requires @supabase/ssr which stores the
  // session in cookies accessible in middleware. The current setup uses
  // localStorage-based auth via @supabase/supabase-js, so we pass all
  // requests through and let API errors handle the unauth state.
  return NextResponse.next();
}

export const config = {
  matcher: [
    // Skip Next.js internals and static files
    "/((?!_next/static|_next/image|favicon.ico|api/).*)",
  ],
};
