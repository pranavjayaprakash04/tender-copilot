import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Safe redirectTo — never redirect to /register or /login after auth
function getSafeRedirect(redirectTo: string | null): string {
  const blocked = ['/register', '/login', '/auth'];
  if (!redirectTo) return '/tenders';
  if (blocked.some(b => redirectTo.startsWith(b))) return '/tenders';
  return redirectTo;
}

export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')
  const rawRedirect = searchParams.get('redirectTo')
  const redirectTo = getSafeRedirect(rawRedirect)

  if (code) {
    const cookieStore = cookies()
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll() {
            return cookieStore.getAll()
          },
          setAll(cookiesToSet: { name: string; value: string; options?: any }[]) {
            try {
              cookiesToSet.forEach(({ name, value, options }) =>
                cookieStore.set(name, value, options)
              )
            } catch {
              // Cookie setting may fail in some environments — non-fatal
            }
          },
        },
      }
    )

    const { error } = await supabase.auth.exchangeCodeForSession(code)
    if (!error) {
      // Always redirect to stable production URL after auth
      const stableOrigin = process.env.NEXT_PUBLIC_SITE_URL || origin
      return NextResponse.redirect(`${stableOrigin}${redirectTo}`)
    }
  }

  // Auth failed — back to login with error flag
  return NextResponse.redirect(`${origin}/login?error=auth_failed`)
}
