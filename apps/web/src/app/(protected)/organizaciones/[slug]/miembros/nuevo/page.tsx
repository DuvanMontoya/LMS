import { MemberOnboardingForm } from '@/components/organizations/member-onboarding-form';
import { PageHeader } from '@/components/platform/page-header';
import { getOrganizationForPage } from '@/lib/organizations/server';
import { notFound } from 'next/navigation';

const supportedRoles = new Set([
  'administrator',
  'author',
  'reviewer',
  'instructor',
  'learner',
]);

export default async function NewMemberPage({
  params,
  searchParams,
}: Readonly<{
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ rol?: string }>;
}>) {
  const [{ slug }, { rol }] = await Promise.all([params, searchParams]);
  const { access, organization } = await getOrganizationForPage(slug);
  if (!access.capabilities.includes('membership.invite')) notFound();
  const initialRole = supportedRoles.has(rol ?? '')
    ? (rol as
        'administrator' | 'author' | 'reviewer' | 'instructor' | 'learner')
    : 'learner';
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { href: `/organizaciones/${slug}/miembros`, label: 'Miembros' },
          { label: 'Registrar persona' },
        ]}
        description="Crea una incorporación verificable y asigna los roles institucionales desde el principio."
        eyebrow="Miembros"
        title={rol === 'learner' ? 'Registrar estudiante' : 'Registrar persona'}
      />
      <div className="mt-6">
        <MemberOnboardingForm initialRole={initialRole} slug={slug} />
      </div>
    </main>
  );
}
