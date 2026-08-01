'use client';

import { CheckCircle2, LoaderCircle, UserPlus, UsersRound } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { components } from '@/lib/api/generated/platform';
import {
  useCreateManagedAccount,
  useCreateOrganizationInvitation,
} from '@/lib/organizations/hooks';
import { roleLabel } from '@/lib/organizations/labels';

type Role = components['schemas']['OrganizationRole'];
type OnboardingMode = 'invitation' | 'managed';

const assignableRoles: Role[] = [
  'administrator',
  'author',
  'reviewer',
  'instructor',
  'learner',
];

type PersonFields = {
  email: string;
  familyName: string;
  givenName: string;
  institutionalId: string;
  locale: string;
  memberType: string;
  phone: string;
  preferredName: string;
  timezone: string;
};

const initialPerson: PersonFields = {
  email: '',
  familyName: '',
  givenName: '',
  institutionalId: '',
  locale: 'es',
  memberType: '',
  phone: '',
  preferredName: '',
  timezone: 'America/Bogota',
};

function apiError(error: unknown) {
  return error instanceof Error
    ? error.message
    : 'No fue posible completar la incorporación.';
}

export function MemberOnboardingForm({
  initialRole = 'learner',
  slug,
}: Readonly<{
  initialRole?: Role;
  slug: string;
}>) {
  const invitation = useCreateOrganizationInvitation(slug);
  const managedAccount = useCreateManagedAccount(slug);
  const [mode, setMode] = useState<OnboardingMode>('managed');
  const [person, setPerson] = useState<PersonFields>(initialPerson);
  const [roles, setRoles] = useState<Role[]>([initialRole]);
  const [success, setSuccess] = useState<{
    email: string;
    mode: OnboardingMode;
  }>();
  const pending = invitation.isPending || managedAccount.isPending;

  function updateField(field: keyof PersonFields, value: string) {
    setPerson((current) => ({ ...current, [field]: value }));
  }

  function toggleRole(role: Role, checked: boolean) {
    setRoles((current) => {
      if (checked) return current.includes(role) ? current : [...current, role];
      return current.filter((candidate) => candidate !== role);
    });
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSuccess(undefined);
    if (roles.length === 0) return;
    const payload = {
      email: person.email.trim(),
      roles,
      given_name: person.givenName.trim(),
      family_name: person.familyName.trim(),
      preferred_name: person.preferredName.trim(),
      member_type: person.memberType.trim(),
      institutional_id: person.institutionalId.trim(),
      phone: person.phone.trim(),
      locale: person.locale.trim() || 'es',
      timezone_name: person.timezone.trim() || 'America/Bogota',
    };
    try {
      if (mode === 'managed') {
        await managedAccount.mutateAsync(payload);
      } else {
        await invitation.mutateAsync(payload);
      }
      setSuccess({ email: payload.email, mode });
      setPerson(initialPerson);
    } catch {
      // The structured API response is rendered below.
    }
  }

  const error = invitation.error ?? managedAccount.error;

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_19rem]">
      <Card>
        <CardHeader>
          <CardTitle>Registrar una persona</CardTitle>
          <CardDescription>
            Crea una incorporación trazable para estudiantes, docentes y
            personal. Los roles se vuelven efectivos únicamente al finalizar la
            activación; no se simula una membresía antes de tiempo.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-6"
            noValidate
            onSubmit={(event) => void submit(event)}
          >
            <fieldset className="space-y-3">
              <legend className="text-sm font-medium">Cómo se incorpora</legend>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="flex cursor-pointer gap-3 rounded-lg border p-4 has-[:checked]:border-primary has-[:checked]:bg-primary/5">
                  <input
                    checked={mode === 'managed'}
                    className="mt-0.5 size-4 accent-primary"
                    name="onboarding-mode"
                    onChange={() => setMode('managed')}
                    type="radio"
                  />
                  <span>
                    <span className="block text-sm font-semibold">
                      Crear cuenta administrada
                    </span>
                    <span className="mt-1 block text-xs leading-5 text-muted-foreground">
                      Crea ahora el usuario institucional inactivo y le envía un
                      enlace para que establezca su propia contraseña.
                    </span>
                  </span>
                </label>
                <label className="flex cursor-pointer gap-3 rounded-lg border p-4 has-[:checked]:border-primary has-[:checked]:bg-primary/5">
                  <input
                    checked={mode === 'invitation'}
                    className="mt-0.5 size-4 accent-primary"
                    name="onboarding-mode"
                    onChange={() => setMode('invitation')}
                    type="radio"
                  />
                  <span>
                    <span className="block text-sm font-semibold">
                      Invitar a una cuenta
                    </span>
                    <span className="mt-1 block text-xs leading-5 text-muted-foreground">
                      Envía un enlace de un solo uso. La persona usa su cuenta
                      existente o crea y verifica una nueva.
                    </span>
                  </span>
                </label>
              </div>
            </fieldset>

            <fieldset className="space-y-4">
              <legend className="text-sm font-medium">
                Datos de la persona
              </legend>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field
                  label="Nombres"
                  onChange={(value) => updateField('givenName', value)}
                  required={mode === 'managed'}
                  value={person.givenName}
                />
                <Field
                  label="Apellidos"
                  onChange={(value) => updateField('familyName', value)}
                  required={mode === 'managed'}
                  value={person.familyName}
                />
                <Field
                  label="Nombre visible"
                  onChange={(value) => updateField('preferredName', value)}
                  value={person.preferredName}
                />
                <Field
                  label="Tipo de miembro"
                  onChange={(value) => updateField('memberType', value)}
                  placeholder="Estudiante, docente, contratista..."
                  required={mode === 'managed'}
                  value={person.memberType}
                />
                <Field
                  inputMode="email"
                  label="Correo institucional o personal"
                  onChange={(value) => updateField('email', value)}
                  required
                  type="email"
                  value={person.email}
                />
                <Field
                  label="ID institucional"
                  onChange={(value) => updateField('institutionalId', value)}
                  value={person.institutionalId}
                />
                <Field
                  label="Teléfono"
                  onChange={(value) => updateField('phone', value)}
                  type="tel"
                  value={person.phone}
                />
                <Field
                  label="Idioma"
                  onChange={(value) => updateField('locale', value)}
                  placeholder="es"
                  required
                  value={person.locale}
                />
                <Field
                  label="Zona horaria"
                  onChange={(value) => updateField('timezone', value)}
                  placeholder="America/Bogota"
                  required
                  value={person.timezone}
                />
              </div>
            </fieldset>

            <fieldset className="space-y-3">
              <legend className="text-sm font-medium">
                Roles institucionales
              </legend>
              <p className="text-xs leading-5 text-muted-foreground">
                Asigna solo lo que la persona necesita. Un estudiante puede
                combinarse con otros roles cuando existe una responsabilidad
                real; el rol propietario nunca se incorpora desde este flujo.
              </p>
              <div className="grid overflow-hidden rounded-lg border sm:grid-cols-2">
                {assignableRoles.map((role) => (
                  <label
                    className="flex min-h-11 items-center gap-3 border-b px-3 text-sm last:border-b-0 hover:bg-muted/30 sm:odd:border-r sm:nth-last-[-n+2]:border-b-0"
                    key={role}
                  >
                    <input
                      checked={roles.includes(role)}
                      className="size-4 accent-primary"
                      onChange={(event) =>
                        toggleRole(role, event.target.checked)
                      }
                      type="checkbox"
                    />
                    {roleLabel(role)}
                  </label>
                ))}
              </div>
              {roles.length === 0 ? (
                <p className="text-sm text-destructive">
                  Selecciona al menos un rol.
                </p>
              ) : null}
            </fieldset>

            {error ? (
              <Alert variant="destructive">
                <AlertTitle>No se pudo registrar a la persona</AlertTitle>
                <AlertDescription>{apiError(error)}</AlertDescription>
              </Alert>
            ) : null}
            {success ? (
              <Alert className="border-emerald-600/20 bg-emerald-500/5">
                <CheckCircle2 className="text-emerald-700" />
                <AlertTitle>Incorporación creada</AlertTitle>
                <AlertDescription>
                  {success.mode === 'managed'
                    ? `Se creó la cuenta inactiva de ${success.email} y se envió su activación.`
                    : `Se envió la invitación a ${success.email}.`}{' '}
                  Puedes seguir su aceptación, reenvío o revocación en
                  <Link
                    className="ml-1 font-medium underline"
                    href={`/organizaciones/${slug}/miembros/invitaciones`}
                  >
                    Invitaciones
                  </Link>
                  .
                </AlertDescription>
              </Alert>
            ) : null}
            <div className="flex flex-wrap gap-3">
              <Button disabled={pending || roles.length === 0} type="submit">
                {pending ? (
                  <LoaderCircle className="animate-spin" />
                ) : (
                  <UserPlus />
                )}
                {mode === 'managed'
                  ? 'Crear cuenta y activación'
                  : 'Enviar invitación'}
              </Button>
              <Button asChild type="button" variant="outline">
                <Link href={`/organizaciones/${slug}/miembros`}>Cancelar</Link>
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <aside className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <UsersRound className="size-4 text-primary" />
              Qué ocurre después
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>
              1. Se registra una invitación auditable con sus datos y roles.
            </p>
            <p>
              2. La persona verifica el correo y crea o activa su contraseña.
            </p>
            <p>3. El servidor crea la membresía activa y guarda el evento.</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Atajos de gestión</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Button asChild size="sm" variant="outline">
              <Link href={`/organizaciones/${slug}/miembros/invitaciones`}>
                Ver invitaciones
              </Link>
            </Button>
            <Button asChild size="sm" variant="outline">
              <Link href={`/organizaciones/${slug}/miembros/solicitudes`}>
                Ver solicitudes
              </Link>
            </Button>
          </CardContent>
        </Card>
      </aside>
    </div>
  );
}

function Field({
  inputMode,
  label,
  onChange,
  placeholder,
  required = false,
  type = 'text',
  value,
}: Readonly<{
  inputMode?: React.HTMLAttributes<HTMLInputElement>['inputMode'];
  label: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  type?: React.HTMLInputTypeAttribute;
  value: string;
}>) {
  const id = `member-${label.toLowerCase().replaceAll(/[^a-z0-9]+/g, '-')}`;
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        inputMode={inputMode}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        required={required}
        type={type}
        value={value}
      />
    </div>
  );
}
