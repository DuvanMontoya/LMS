import { redirect } from 'next/navigation';

import { resolvePostLoginDestination } from '@/lib/auth/post-login-destination';
import { getAccessContext } from '@/lib/organizations/server';

export default async function PostLoginContinuationPage({
  searchParams,
}: Readonly<{ searchParams: Promise<{ next?: string }> }>) {
  const [{ next }, context] = await Promise.all([
    searchParams,
    getAccessContext(),
  ]);
  redirect(resolvePostLoginDestination(next, context));
}
