import { redirect } from 'next/navigation';

import { getServerAuthSession } from '@/lib/auth/server-session';

export default async function StudyLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const session = await getServerAuthSession();
  if (!session) redirect('/auth/iniciar-sesion?next=/estudiar');
  return children;
}
