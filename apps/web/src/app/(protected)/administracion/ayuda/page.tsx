import { AcademicHelpCenter } from '@/components/help/academic-help-center';
import { PageHeader } from '@/components/platform/page-header';

export default function PlatformHelpPage() {
  return (
    <main className="academic-page">
      <PageHeader
        description="Alcance del plano global y secuencia segura para entregar el gobierno de una institución."
        eyebrow="Ayuda y conocimiento"
        title="Operación de la plataforma"
      />
      <div className="mt-6">
        <AcademicHelpCenter platformOperator />
      </div>
    </main>
  );
}
