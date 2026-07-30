'use client';

import { BookOpen, Layers3, Network, Plus } from 'lucide-react';
import { useState } from 'react';

import { AreaForm } from '@/components/catalog/area-form';
import { StructureForms } from '@/components/catalog/structure-forms';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import type { components } from '@/lib/api/generated/platform';

type Area = components['schemas']['Area'];
type Discipline = components['schemas']['Discipline'];

export function CurriculumCreateActions({
  areas,
  disciplines,
  slug,
}: Readonly<{
  areas: readonly Area[];
  disciplines: readonly Discipline[];
  slug: string;
}>) {
  const [areaOpen, setAreaOpen] = useState(false);
  const [disciplineOpen, setDisciplineOpen] = useState(false);
  const [subjectOpen, setSubjectOpen] = useState(false);

  return (
    <div className="flex flex-wrap items-center gap-2">
      <CreationDialog
        description="Crea el nivel superior que agrupa disciplinas relacionadas."
        icon={Layers3}
        label="Área"
        onOpenChange={setAreaOpen}
        open={areaOpen}
        title="Nueva área de conocimiento"
      >
        <AreaForm embedded onCreated={() => setAreaOpen(false)} slug={slug} />
      </CreationDialog>
      <CreationDialog
        description="Vincula una disciplina a un área institucional existente."
        disabled={areas.length === 0}
        icon={Network}
        label="Disciplina"
        onOpenChange={setDisciplineOpen}
        open={disciplineOpen}
        title="Nueva disciplina"
      >
        <StructureForms
          areas={areas}
          disciplines={disciplines}
          embedded
          mode="discipline"
          onCreated={() => setDisciplineOpen(false)}
          slug={slug}
        />
      </CreationDialog>
      <CreationDialog
        description="Crea una asignatura dentro de una disciplina existente."
        disabled={disciplines.length === 0}
        icon={BookOpen}
        label="Asignatura"
        onOpenChange={setSubjectOpen}
        open={subjectOpen}
        title="Nueva asignatura"
      >
        <StructureForms
          areas={areas}
          disciplines={disciplines}
          embedded
          mode="subject"
          onCreated={() => setSubjectOpen(false)}
          slug={slug}
        />
      </CreationDialog>
    </div>
  );
}

function CreationDialog({
  children,
  description,
  disabled = false,
  icon: Icon,
  label,
  onOpenChange,
  open,
  title,
}: Readonly<{
  children: React.ReactNode;
  description: string;
  disabled?: boolean;
  icon: typeof Layers3;
  label: string;
  onOpenChange: (open: boolean) => void;
  open: boolean;
  title: string;
}>) {
  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogTrigger asChild>
        <Button disabled={disabled} size="sm" variant="outline">
          <Plus data-icon="inline-start" />
          {label}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <div className="mb-2 grid size-9 place-items-center rounded-md bg-primary/10 text-primary">
            <Icon className="size-4" />
          </div>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        {children}
      </DialogContent>
    </Dialog>
  );
}
