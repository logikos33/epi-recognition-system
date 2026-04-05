'use client'

import { AuthProtected } from '@/components/auth-protected'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <AuthProtected>{children}</AuthProtected>
}
