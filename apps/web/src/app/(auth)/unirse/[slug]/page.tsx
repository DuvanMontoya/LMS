import { PublicJoin } from '@/components/organizations/public-join';

export default async function PublicJoinPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  return (
    <main
      className="mx-auto w-full max-w-5xl px-5 py-12"
      id="contenido-principal"
    >
      <PublicJoin slug={slug} />
    </main>
  );
}
