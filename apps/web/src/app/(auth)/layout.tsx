import { redirect } from 'next/navigation';

import { getServerAuthSession } from '@/lib/auth/server-session';

export default async function AuthLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const session = await getServerAuthSession();
  if (session) redirect('/estudiar');
  return children;
}
