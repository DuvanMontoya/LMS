import {
  ArrowRight,
  BookOpenCheck,
  Building2,
  CalendarRange,
  CheckCircle2,
  ClipboardList,
  GraduationCap,
  Layers3,
  LibraryBig,
  Route,
  ShieldCheck,
  Sparkles,
  UsersRound,
} from 'lucide-react';
import Link from 'next/link';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

type GuideStep = {
  capability?: string;
  description: string;
  example: string;
  href?: string;
  icon: typeof Route;
  result: string;
  title: string;
};

const concepts = [
  {
    name: 'Asignatura y curso',
    definition:
      'La asignatura organiza qué se enseña; el curso es el producto formativo que se construye y publica.',
    example: 'Asignatura: Álgebra · Curso: Álgebra I',
  },
  {
    name: 'Revisión y release',
    definition:
      'La revisión es editable. El release es la copia publicada, completa e inmutable que reciben los estudiantes.',
    example: 'Revisión R3 aprobada → release R3 publicado',
  },
  {
    name: 'Grupo y sección',
    definition:
      'El grupo es un padrón reutilizable; una sección ejecuta un curso, release y período concretos.',
    example: '8.º A → Álgebra I · 8.º A · P2 · R3',
  },
  {
    name: 'Matrícula y asignación',
    definition:
      'La matrícula concede el derecho individual a cursar; la asignación fija qué release y grupo recibe esa persona.',
    example: 'Ana queda matriculada y fijada a R3',
  },
  {
    name: 'Actividad curricular',
    definition:
      'Es cada paso ordenado del curso: una lección, una clase en vivo o una evaluación, con su propia finalización.',
    example: 'Lección → clase en vivo → quiz → lección',
  },
  {
    name: 'Progreso, nota y aprobación',
    definition:
      'El progreso mide recorrido; la nota mide resultados; la aprobación aplica una política académica explícita.',
    example: '75 % recorrido · 82 % nota · aprobación pendiente',
  },
] as const;

export function AcademicHelpCenter({
  capabilities = [],
  organizationSlug,
  platformOperator = false,
}: Readonly<{
  organizationSlug?: string;
  capabilities?: readonly string[];
  platformOperator?: boolean;
}>) {
  const base = organizationSlug
    ? `/organizaciones/${organizationSlug}`
    : undefined;
  const steps: GuideStep[] = platformOperator
    ? [
        {
          description:
            'Crea el registro global y envía una invitación privada al propietario inicial. El operador no obtiene acceso institucional.',
          example: 'Colegio Horizonte · propietaria@colegio.edu',
          href: '/administracion/organizaciones',
          icon: Building2,
          result: 'Institución pendiente de activación',
          title: 'Crear e invitar',
        },
        {
          description:
            'La persona invitada crea su cuenta con el correo validado y verifica su identidad. Sólo entonces se activa la institución.',
          example: 'Invitación → cuenta → verificación',
          icon: ShieldCheck,
          result: 'Propietario institucional verificado',
          title: 'Activar con seguridad',
        },
        {
          description:
            'Desde ese momento, el propietario y los administradores gobiernan la institución. El operador conserva únicamente el plano global.',
          example: 'Sin membresía ni enlaces internos para el operador',
          href: '/administracion/configuracion',
          icon: UsersRound,
          result: 'Separación de responsabilidades',
          title: 'Entregar el gobierno',
        },
      ]
    : [
        {
          capability: 'catalog.view',
          description:
            'Define áreas, disciplinas, asignaturas, temas, conceptos, objetivos y prerrequisitos. Esta es la base pedagógica reutilizable.',
          example: 'Matemáticas → Matemática escolar → Álgebra',
          href: `${base}/curriculo`,
          icon: Layers3,
          result: 'Mapa curricular disponible',
          title: 'Definir el currículo',
        },
        {
          capability: 'learning.cohort.view',
          description:
            'Crea el marco temporal oficial antes de abrir grupos, programar actividades o consolidar calificaciones.',
          example: 'Año 2026 → Periodo 2',
          href: `${base}/aprendizaje/periodos`,
          icon: CalendarRange,
          result: 'Periodo académico vigente',
          title: 'Crear el periodo',
        },
        {
          capability: 'learning.cohort.view',
          description:
            'Registra las personas y prepara grupos reutilizables. Todavía no concedas acceso a un curso.',
          example: 'Grupo académico 8.º A',
          href: `${base}/aprendizaje/grupos`,
          icon: UsersRound,
          result: 'Padrón institucional preparado',
          title: 'Preparar personas y grupos',
        },
        {
          capability: 'course.authoring.manage',
          description:
            'Crea la identidad estable del curso y alinéala con las asignaturas y objetivos que realmente cubrirá.',
          example: 'Curso Álgebra I · asignatura principal Álgebra',
          href: `${base}/cursos/nuevo`,
          icon: GraduationCap,
          result: 'Revisión editable del curso',
          title: 'Crear y alinear el curso',
        },
        {
          capability: 'course.authoring.view',
          description:
            'Organiza módulos y una única secuencia de lecciones, clases en vivo y evaluaciones. Completa contenido, duración y alineaciones.',
          example: 'Lección 1 → clase en vivo → quiz → lección 2',
          href: `${base}/cursos/autoria`,
          icon: BookOpenCheck,
          result: 'Recorrido pedagógico completo',
          title: 'Construir la experiencia',
        },
        {
          capability: 'course.authoring.view',
          description:
            'Revisa los bloqueos, aprueba la revisión y publica un release. Aprobar no publica automáticamente.',
          example: 'Revisión R3 aprobada → release R3',
          href: `${base}/cursos/autoria`,
          icon: LibraryBig,
          result: 'Snapshot inmutable listo',
          title: 'Revisar y publicar',
        },
        {
          capability: 'learning.cohort.view',
          description:
            'Crea la ejecución concreta seleccionando curso, release, periodo, docentes y, si aplica, el grupo académico de origen.',
          example: 'Álgebra I · 8.º A · P2 · R3',
          href: `${base}/aprendizaje/cohortes`,
          icon: ClipboardList,
          result: 'Sección operativa',
          title: 'Abrir la sección',
        },
        {
          capability: 'learning.enrollment.view',
          description:
            'Sincroniza el roster con vista previa, confirma matrículas y opera calendario, actividades, progreso y gradebook dentro del grupo.',
          example: 'Ana → matrícula → R3 → progreso y nota',
          href: `${base}/aprendizaje/cohortes`,
          icon: CheckCircle2,
          result: 'Aprendizaje trazable e histórico',
          title: 'Matricular y operar',
        },
      ];

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-2xl border bg-card shadow-sm">
        <div className="grid gap-8 bg-[linear-gradient(135deg,color-mix(in_oklab,var(--primary)_10%,transparent),transparent_55%)] p-6 md:p-8 lg:grid-cols-[1.25fr_0.75fr] lg:items-center">
          <div>
            <Badge className="mb-4 rounded-full" variant="secondary">
              <Sparkles /> Centro de conocimiento
            </Badge>
            <h2 className="max-w-3xl text-2xl font-semibold tracking-tight md:text-3xl">
              {platformOperator
                ? 'Activa instituciones sin invadir su gobierno'
                : 'De una idea curricular a una experiencia de aprendizaje verificable'}
            </h2>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground md:text-base">
              {platformOperator
                ? 'El plano global crea, invita y observa la activación. La administración académica empieza únicamente cuando el propietario verificado toma el control.'
                : 'Sigue esta secuencia para que currículo, autoría, publicación, grupos, matrículas y resultados conserven un contexto académico único.'}
            </p>
          </div>
          <div className="rounded-xl border bg-background/85 p-5 backdrop-blur">
            <p className="text-xs font-semibold tracking-widest text-muted-foreground uppercase">
              Regla de oro
            </p>
            <p className="mt-2 text-sm font-medium leading-6">
              {platformOperator
                ? 'Crear una institución no convierte al operador en propietario ni le concede acceso a sus datos.'
                : 'Una publicación nueva nunca cambia el release, la nota, la asistencia ni el progreso históricos de un estudiante.'}
            </p>
          </div>
        </div>
      </section>

      <section aria-labelledby="creation-route">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="academic-kicker">Ruta recomendada</p>
            <h2 className="mt-1 text-xl font-semibold" id="creation-route">
              Créalo en este orden
            </h2>
          </div>
          <p className="max-w-xl text-sm text-muted-foreground">
            Cada paso deja lista una dependencia real del siguiente; no son
            formularios aislados.
          </p>
        </div>
        <ol className="grid gap-3 lg:grid-cols-2">
          {steps.map((step, index) => {
            const Icon = step.icon;
            const canOpen =
              !step.capability || capabilities.includes(step.capability);
            return (
              <li
                className="group rounded-xl border bg-card p-5 shadow-xs transition-colors hover:border-primary/30"
                key={step.title}
              >
                <div className="flex items-start gap-4">
                  <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
                    <Icon className="size-5" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-primary">
                        PASO {String(index + 1).padStart(2, '0')}
                      </span>
                      <span className="h-px flex-1 bg-border" />
                    </div>
                    <h3 className="mt-2 font-semibold">{step.title}</h3>
                    <p className="mt-1 text-sm leading-6 text-muted-foreground">
                      {step.description}
                    </p>
                    <div className="mt-3 rounded-lg bg-muted/45 px-3 py-2 text-xs">
                      <strong>Ejemplo:</strong> {step.example}
                    </div>
                    <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs font-medium text-emerald-700 dark:text-emerald-400">
                        Resultado: {step.result}
                      </span>
                      {step.href && canOpen ? (
                        <Button asChild size="sm" variant="ghost">
                          <Link href={step.href}>
                            Abrir <ArrowRight />
                          </Link>
                        </Button>
                      ) : step.href ? (
                        <span className="text-xs text-muted-foreground">
                          Consulta informativa · sin acceso operativo
                        </span>
                      ) : null}
                    </div>
                  </div>
                </div>
              </li>
            );
          })}
        </ol>
      </section>

      {!platformOperator ? (
        <>
          <section aria-labelledby="concepts">
            <p className="academic-kicker">Diccionario práctico</p>
            <h2 className="mt-1 text-xl font-semibold" id="concepts">
              Conceptos que no deben confundirse
            </h2>
            <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {concepts.map((concept) => (
                <article
                  className="rounded-xl border bg-card p-5"
                  key={concept.name}
                >
                  <h3 className="font-semibold">{concept.name}</h3>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {concept.definition}
                  </p>
                  <p className="mt-4 border-l-2 border-primary/35 pl-3 text-xs font-medium">
                    {concept.example}
                  </p>
                </article>
              ))}
            </div>
          </section>

          <section
            className="rounded-2xl border bg-card p-6 md:p-8"
            aria-labelledby="complete-example"
          >
            <div className="grid gap-7 lg:grid-cols-[0.8fr_1.2fr]">
              <div>
                <p className="academic-kicker">Ejemplo completo</p>
                <h2
                  className="mt-1 text-xl font-semibold"
                  id="complete-example"
                >
                  Colegio Horizonte · Álgebra I
                </h2>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">
                  Una historia académica coherente siempre puede reconstruir
                  curso, release, grupo, periodo, matrícula y actividad exacta.
                </p>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                {[
                  ['Currículo', 'Matemáticas → Álgebra'],
                  ['Periodo', '2026 → Periodo 2'],
                  ['Curso', 'Álgebra I · revisión R3'],
                  ['Publicación', 'Release R3 inmutable'],
                  ['Sección', 'Álgebra I · 8.º A · P2 · R3'],
                  ['Estudiante', 'Ana · matrícula fijada a R3'],
                ].map(([label, value]) => (
                  <div
                    className="rounded-lg border bg-muted/20 p-3"
                    key={label}
                  >
                    <p className="text-[0.6875rem] font-semibold tracking-wider text-muted-foreground uppercase">
                      {label}
                    </p>
                    <p className="mt-1 text-sm font-medium">{value}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section
            className="grid gap-3 lg:grid-cols-3"
            aria-label="Comprobaciones de coherencia"
          >
            {[
              [
                'Acceso',
                '¿Existe una matrícula efectiva y una asignación vigente al grupo y release?',
              ],
              [
                'Evidencia',
                '¿Qué actividad exacta produjo este avance, asistencia o resultado?',
              ],
              [
                'Historia',
                '¿Una publicación o corrección posterior conserva intacto lo ocurrido antes?',
              ],
            ].map(([title, question]) => (
              <article className="rounded-xl border bg-card p-5" key={title}>
                <ShieldCheck className="size-5 text-primary" />
                <h3 className="mt-3 font-semibold">{title}</h3>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  {question}
                </p>
              </article>
            ))}
          </section>
        </>
      ) : null}
    </div>
  );
}
