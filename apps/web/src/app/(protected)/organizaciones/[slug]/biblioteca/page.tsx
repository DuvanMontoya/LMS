import { redirect } from 'next/navigation';

export default async function LegacyLibraryPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  redirect(`/organizaciones/${slug}/cursos`);
}
