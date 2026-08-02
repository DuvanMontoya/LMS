'use client';

import { Building2, CheckCircle2, LoaderCircle, Plus } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useProvisionPlatformOrganization } from '@/lib/organizations/hooks';

type Organization = {
  id: string;
  name: string;
  slug: string;
};

export function PlatformOrganizationProvisioner({
  membershipOrganizationSlugs,
  organizations,
}: Readonly<{
  membershipOrganizationSlugs: readonly string[];
  organizations: readonly Organization[];
}>) {
  const provision = useProvisionPlatformOrganization();
  const [name, setName] = useState('');
  const [ownerEmail, setOwnerEmail] = useState('');
  const [created, setCreated] = useState<Organization | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreated(null);
    try {
      const organization = await provision.mutateAsync({
        name: name.trim(),
        owner_email: ownerEmail.trim(),
      });
      setCreated(organization);
      setName('');
      setOwnerEmail('');
    } catch {
      // The normalized API error is rendered below.
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <Card>
        <CardHeader>
          <CardTitle>Crear institución</CardTitle>
          <p className="text-sm leading-6 text-muted-foreground">
            Indica el nombre y el correo de la persona propietaria. La
            plataforma genera el código institucional y deja una membresía real
            y trazable sólo a esa persona; tu cuenta conserva el control global
            sin acceso automático a los datos institucionales.
          </p>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={(event) => void submit(event)}>
            <div className="space-y-2">
              <Label htmlFor="organization-name">
                Nombre de la institución
              </Label>
              <Input
                autoComplete="organization"
                id="organization-name"
                maxLength={160}
                onChange={(event) => setName(event.target.value)}
                placeholder="Ej. Academia Gauss"
                required
                value={name}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="organization-owner-email">
                Correo de la persona propietaria
              </Label>
              <Input
                autoComplete="email"
                id="organization-owner-email"
                onChange={(event) => setOwnerEmail(event.target.value)}
                placeholder="responsable@institucion.edu.co"
                required
                type="email"
                value={ownerEmail}
              />
              <p className="text-xs leading-5 text-muted-foreground">
                Debe corresponder a una cuenta activa con el correo ya
                verificado. Esa persona configurará la institución y podrá
                delegar después.
              </p>
            </div>
            {provision.error instanceof Error ? (
              <Alert variant="destructive">
                <AlertTitle>No se creó la institución</AlertTitle>
                <AlertDescription>{provision.error.message}</AlertDescription>
              </Alert>
            ) : null}
            {created ? (
              <Alert className="border-emerald-600/20 bg-emerald-500/5">
                <CheckCircle2 className="text-emerald-700" />
                <AlertTitle>Institución creada</AlertTitle>
                <AlertDescription>
                  El código institucional generado es{' '}
                  <strong>{created.slug}</strong>. La persona propietaria ya
                  tiene su acceso institucional; este directorio no concede
                  acceso adicional a tu cuenta.
                </AlertDescription>
              </Alert>
            ) : null}
            <Button
              disabled={
                provision.isPending || !name.trim() || !ownerEmail.trim()
              }
              type="submit"
            >
              {provision.isPending ? (
                <LoaderCircle className="animate-spin" />
              ) : (
                <Plus />
              )}
              Crear institución
            </Button>
          </form>
        </CardContent>
      </Card>

      <aside className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Building2 className="size-4 text-primary" />
              Después de crearla
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm leading-6 text-muted-foreground">
            <p>1. La persona indicada recibe la membresía propietaria real.</p>
            <p>2. Esa persona configura las reglas e incorpora a su equipo.</p>
            <p>
              3. Tú conservas el directorio y las reglas globales, sin acceso
              implícito a los datos de la institución.
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Instituciones activas</CardTitle>
          </CardHeader>
          <CardContent>
            {organizations.length ? (
              <ul className="space-y-2">
                {organizations.map((organization) => (
                  <li key={organization.id}>
                    {membershipOrganizationSlugs.includes(organization.slug) ? (
                      <Button
                        asChild
                        className="h-auto w-full justify-start py-2 text-left"
                        variant="ghost"
                      >
                        <Link href={`/organizaciones/${organization.slug}`}>
                          <Building2 />
                          <span className="min-w-0 truncate">
                            {organization.name}
                          </span>
                        </Link>
                      </Button>
                    ) : (
                      <div className="flex min-h-11 items-center gap-2 px-3 text-sm text-muted-foreground">
                        <Building2 />
                        <span className="min-w-0 truncate">
                          {organization.name}
                        </span>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">
                Aún no hay instituciones creadas.
              </p>
            )}
            <p className="mt-4 text-xs leading-5 text-muted-foreground">
              Este directorio no concede acceso a datos ni administración de una
              institución. Para abrirla necesitas una membresía institucional
              activa.
            </p>
          </CardContent>
        </Card>
      </aside>
    </div>
  );
}
