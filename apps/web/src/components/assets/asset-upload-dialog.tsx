'use client';

import { Plus } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { AssetUploadForm } from '@/components/assets/asset-upload-form';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

export function AssetUploadDialog({ slug }: Readonly<{ slug: string }>) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  return (
    <Dialog onOpenChange={setOpen} open={open}>
      <DialogTrigger asChild>
        <Button>
          <Plus data-icon="inline-start" />
          Cargar recurso
        </Button>
      </DialogTrigger>
      <DialogContent className="asset-library-dialog max-h-[92vh] overflow-y-auto sm:max-w-3xl">
        <DialogHeader>
          <p className="academic-kicker">Nueva carga</p>
          <DialogTitle>Cargar a Recursos</DialogTitle>
          <DialogDescription>
            Selecciona el tipo y el archivo. La carga permanece privada mientras
            se verifica y procesa.
          </DialogDescription>
        </DialogHeader>
        <AssetUploadForm
          compact
          onReady={() => {
            setOpen(false);
            router.refresh();
          }}
          readyActionLabel="Finalizar carga"
          slug={slug}
        />
      </DialogContent>
    </Dialog>
  );
}
