'use client';

import { Plus } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { QuestionBankCreateForm } from '@/components/assessments/authoring-forms';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

export function QuestionBankCreateDialog({ slug }: Readonly<{ slug: string }>) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  return (
    <Dialog onOpenChange={setOpen} open={open}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus data-icon="inline-start" /> Nuevo banco
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-3xl">
        <DialogHeader>
          <p className="academic-kicker">Biblioteca de preguntas</p>
          <DialogTitle>Crear banco</DialogTitle>
          <DialogDescription>
            Define una colección privada y reutilizable sin abandonar el
            inventario.
          </DialogDescription>
        </DialogHeader>
        <QuestionBankCreateForm
          onCreated={() => {
            setOpen(false);
            router.refresh();
          }}
          slug={slug}
        />
      </DialogContent>
    </Dialog>
  );
}
