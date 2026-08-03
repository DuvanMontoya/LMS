import { redirect } from 'next/navigation';

export default async function NewAssetPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  redirect(`/organizaciones/${slug}/recursos`);
}
