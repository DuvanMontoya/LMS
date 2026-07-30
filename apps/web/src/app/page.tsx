import {
  ArrowRight,
  BookOpenCheck,
  Braces,
  Building2,
  GraduationCap,
} from 'lucide-react';
import Link from 'next/link';

import { LoginResearchField } from '@/components/auth/login-research-field';
import { Button } from '@/components/ui/button';

const capabilities = [
  {
    icon: Building2,
    title: 'Gobierno institucional',
    description:
      'Organizaciones, membresías y capacidades explícitas para cada contexto académico.',
  },
  {
    icon: BookOpenCheck,
    title: 'Currículo y cursos conectados',
    description:
      'Taxonomías, objetivos, prerrequisitos y estructuras de curso con trazabilidad.',
  },
  {
    icon: Braces,
    title: 'Contenido semántico',
    description:
      'Documentos académicos versionados con matemáticas, código y bloques pedagógicos.',
  },
];

export default function Home() {
  return (
    <main className="relative isolate min-h-svh overflow-hidden bg-[#e3e6e9] text-[#172129]">
      <LoginResearchField />
      <header className="relative mx-auto flex h-16 max-w-[90rem] items-center border-b border-slate-700/15 px-4 sm:px-6 lg:px-10">
        <Link
          className="flex items-center gap-3 text-sm font-semibold tracking-tight"
          href="/"
        >
          <span className="grid size-8 place-items-center border border-slate-700/25 bg-white/50 text-primary">
            <GraduationCap className="size-4" />
          </span>
          Plataforma académica
        </Link>
        <nav className="ml-auto flex items-center gap-2" aria-label="Acceso">
          <Button asChild className="rounded-none" variant="ghost">
            <Link href="/auth/iniciar-sesion">Ingresar</Link>
          </Button>
          <Button asChild className="hidden rounded-none sm:inline-flex">
            <Link href="/auth/registro">
              Crear cuenta
              <ArrowRight data-icon="inline-end" />
            </Link>
          </Button>
        </nav>
      </header>

      <section className="relative mx-auto grid min-h-[calc(100svh-4rem)] max-w-[90rem] items-center gap-14 px-4 py-14 sm:px-6 lg:grid-cols-[minmax(0,1fr)_minmax(23rem,30rem)] lg:px-10">
        <div>
          <p className="font-mono text-[0.65rem] font-bold tracking-[0.15em] text-slate-600 uppercase">
            Infraestructura académica institucional
          </p>
          <h1 className="mt-6 max-w-4xl font-serif text-5xl leading-[0.92] font-normal tracking-[-0.055em] text-balance sm:text-7xl lg:text-[6.2rem]">
            Conocimiento con estructura.
          </h1>
          <p className="mt-7 max-w-xl text-base leading-7 text-slate-600">
            Currículo, autoría y contenido semántico dentro de un entorno
            institucional trazable.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button asChild className="rounded-none" size="lg">
              <Link href="/auth/iniciar-sesion">
                Abrir mi espacio
                <ArrowRight data-icon="inline-end" />
              </Link>
            </Button>
          </div>
        </div>

        <aside className="border border-slate-700/25 bg-white/65 shadow-[0_30px_90px_rgb(20_31_40_/_0.12)] backdrop-blur-xl">
          <header className="border-b border-slate-700/15 px-6 py-5 text-center">
            <p className="text-xs font-bold tracking-[0.14em] uppercase">
              Sistema académico
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Gobierno, currículo y autoría
            </p>
          </header>
          <div className="divide-y divide-slate-700/15">
            {capabilities.map(({ description, icon: Icon, title }, index) => (
              <article
                className="grid grid-cols-[2rem_minmax(0,1fr)] gap-4 px-6 py-5"
                key={title}
              >
                <span className="font-mono text-xs font-semibold text-primary">
                  0{index + 1}
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <Icon className="size-4 text-primary" />
                    <h2 className="text-sm font-semibold">{title}</h2>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    {description}
                  </p>
                </div>
              </article>
            ))}
          </div>
          <footer className="border-t border-slate-700/15 px-6 py-4 text-[0.65rem] text-slate-500">
            Acceso por membresía · sesión protegida · trazabilidad
          </footer>
        </aside>
      </section>
    </main>
  );
}
