import { createClient } from '@supabase/supabase-js'
import { NextResponse, type NextRequest } from 'next/server'

const PUBLIC_PATHS = ['/', '/login', '/signup', '/auth/callback', '/auth/confirm']

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Allow public paths through without auth check
  if (PUBLIC_PATHS.some(path => pathname === path || pathname.startsWith(path + '/'))) {
    return NextResponse.next()
  }

  // Get token from cookie — Supabase stores it as sb-<project>-auth-token
  const cookieHeader = request.headers.get('cookie') || ''
  const tokenMatch = cookieHeader.match(/sb-[^=]+-auth-token=([^;]+)/)
  let accessToken: string | null = null

  if (tokenMatch) {
    try {
      const decoded = decodeURIComponent(tokenMatch[1])
      const parsed = JSON.parse(decoded)
      accessToken = parsed?.access_token ?? null
    } catch {
      accessToken = null
    }
  }

  // Fallback: check Authorization header
  if (!accessToken) {
    const authHeader = request.headers.get('authorization') || ''
    if (authHeader.startsWith('Bearer ')) {
      accessToken = authHeader.slice(7)
    }
  }

  // No token — redirect to login
  if (!accessToken) {
    const loginUrl = request.nextUrl.clone()
    loginUrl.pathname = '/login'
    loginUrl.searchParams.set('redirectTo', pathname)
    return NextResponse.redirect(loginUrl)
  }

  // Verify token with Supabase
  try {
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    )

    const { data: { user }, error } = await supabase.auth.getUser(accessToken)

    if (error || !user) {
      const loginUrl = request.nextUrl.clone()
      loginUrl.pathname = '/login'
      loginUrl.searchParams.set('redirectTo', pathname)
      return NextResponse.redirect(loginUrl)
    }
  } catch {
    const loginUrl = request.nextUrl.clone()
    loginUrl.pathname = '/login'
    loginUrl.searchParams.set('redirectTo', pathname)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}
