'use client';

import { CheckCircle2, LoaderCircle, UserPlus, UsersRound } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { useHydrated } from '@/hooks/use-hydrated';
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
import {
  ageFromBirthDate,
  departmentOptions,
  documentTypeOptions,
  educationInstitutionApplies,
  educationLevelOptions,
  educationStageOptions,
  genderOptions,
  memberTypeOptions,
  registrationReasonOptions,
  socioeconomicStratumOptions,
  suggestedDocument,
} from './member-profile-options';

type Role = components['schemas']['OrganizationRole'];
type OnboardingMode = 'invitation' | 'managed';
type DocumentType = '' | components['schemas']['DocumentTypeEnum'];
type EducationLevel = '' | components['schemas']['EducationLevelEnum'];
type EducationStage = '' | components['schemas']['EducationStageEnum'];
type Gender = '' | components['schemas']['GenderEnum'];
type MemberType = components['schemas']['MemberTypeEnum'];
type RegistrationReason = '' | components['schemas']['RegistrationReasonEnum'];
type SocioeconomicStratum =
  '' | components['schemas']['SocioeconomicStratumEnum'];

const assignableRoles: Role[] = [
  'administrator',
  'author',
  'reviewer',
  'instructor',
  'learner',
];

type PersonFields = {
  address: string;
  dateOfBirth: string;
  departmentCode: string;
  documentNumber: string;
  documentType: DocumentType;
  educationInstitution: string;
  educationLevel: EducationLevel;
  educationStage: EducationStage;
  email: string;
  familyName: string;
  gender: Gender;
  givenName: string;
  institutionalId: string;
  locale: string;
  memberType: MemberType;
  middleName: string;
  municipality: string;
  preferredName: string;
  registrationReason: RegistrationReason;
  registrationReasonDetail: string;
  secondFamilyName: string;
  socioeconomicStratum: SocioeconomicStratum;
  timezone: string;
  whatsapp: string;
};

const initialPerson: PersonFields = {
  address: '',
  dateOfBirth: '',
  departmentCode: '',
  documentNumber: '',
  documentType: '',
  educationInstitution: '',
  educationLevel: '',
  educationStage: '',
  email: '',
  familyName: '',
  gender: '',
  givenName: '',
  institutionalId: '',
  locale: 'es',
  memberType: 'learner',
  middleName: '',
  municipality: '',
  preferredName: '',
  registrationReason: 'course',
  registrationReasonDetail: '',
  secondFamilyName: '',
  socioeconomicStratum: 'not_reported',
  timezone: 'America/Bogota',
  whatsapp: '+57 ',
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
  const isHydrated = useHydrated();
  const pending = invitation.isPending || managedAccount.isPending;

  function updateField<K extends keyof PersonFields>(field: K, value: string) {
    setPerson((current) => ({
      ...current,
      [field]: value as PersonFields[K],
    }));
  }

  function toggleRole(role: Role, checked: boolean) {
    setRoles((current) => {
      if (checked) return current.includes(role) ? current : [...current, role];
      return current.filter((candidate) => candidate !== role);
    });
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isHydrated) return;
    setSuccess(undefined);
    if (roles.length === 0) return;
    const payload: components['schemas']['ManagedAccountCreate'] = {
      email: person.email.trim(),
      roles,
      given_name: person.givenName.trim(),
      middle_name: person.middleName.trim(),
      family_name: person.familyName.trim(),
      second_family_name: person.secondFamilyName.trim(),
      preferred_name: person.preferredName.trim(),
      member_type: person.memberType,
      institutional_id: person.institutionalId.trim(),
      whatsapp: person.whatsapp.trim(),
      date_of_birth: person.dateOfBirth || null,
      document_type: person.documentType,
      document_number: person.documentNumber.trim(),
      gender: person.gender,
      education_stage: person.educationStage,
      education_institution: person.educationInstitution.trim(),
      education_level: person.educationLevel,
      department_code: person.departmentCode,
      municipality: person.municipality.trim(),
      address: person.address.trim(),
      socioeconomic_stratum: person.socioeconomicStratum,
      registration_reason: person.registrationReason,
      registration_reason_detail: person.registrationReasonDetail.trim(),
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
            aria-busy={!isHydrated || pending}
            className="space-y-6"
            noValidate
            onSubmit={(event) => void submit(event)}
          >
            <fieldset className="contents" disabled={!isHydrated || pending}>
              {!isHydrated ? (
                <p className="text-sm text-muted-foreground" role="status">
                  Preparando formulario seguro…
                </p>
              ) : null}
              <fieldset className="space-y-3">
                <legend className="text-sm font-medium">
                  Cómo se incorpora
                </legend>
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
                        Crea ahora el usuario institucional inactivo y le envía
                        un enlace para que establezca su propia contraseña.
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
                <p className="text-xs leading-5 text-muted-foreground">
                  Para iniciar bastan estos datos. La persona completa su perfil
                  después de activar el acceso; no hace falta repetir un
                  formulario largo para incorporarla.
                </p>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field
                    inputMode="email"
                    label="Correo institucional o personal"
                    onChange={(value) => updateField('email', value)}
                    required
                    type="email"
                    value={person.email}
                  />
                  <Field
                    label="Primer nombre"
                    onChange={(value) => updateField('givenName', value)}
                    required={mode === 'managed'}
                    value={person.givenName}
                  />
                  <Field
                    label="Primer apellido"
                    onChange={(value) => updateField('familyName', value)}
                    required={mode === 'managed'}
                    value={person.familyName}
                  />
                  <SelectField
                    label="Tipo de miembro"
                    onChange={(value) => updateField('memberType', value)}
                    options={memberTypeOptions}
                    required={mode === 'managed'}
                    value={person.memberType}
                  />
                </div>
              </fieldset>

              <details className="rounded-lg border bg-muted/20 p-4">
                <summary className="cursor-pointer text-sm font-medium marker:text-primary">
                  Añadir datos personales opcionales
                </summary>
                <p className="mt-2 text-xs leading-5 text-muted-foreground">
                  Puedes completarlos ahora si los necesitas para tu operación;
                  ninguno bloquea la invitación ni la activación.
                </p>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <Field
                    label="Segundo nombre"
                    onChange={(value) => updateField('middleName', value)}
                    value={person.middleName}
                  />
                  <Field
                    label="Segundo apellido"
                    onChange={(value) => updateField('secondFamilyName', value)}
                    value={person.secondFamilyName}
                  />
                  <Field
                    label="Nombre visible"
                    onChange={(value) => updateField('preferredName', value)}
                    value={person.preferredName}
                  />
                  <Field
                    label="ID institucional"
                    onChange={(value) => updateField('institutionalId', value)}
                    value={person.institutionalId}
                  />
                  <Field
                    label="WhatsApp"
                    onChange={(value) => updateField('whatsapp', value)}
                    type="tel"
                    value={person.whatsapp}
                  />
                  <div className="space-y-2">
                    <Field
                      label="Fecha de nacimiento"
                      onChange={(value) => {
                        const age = ageFromBirthDate(value);
                        setPerson((current) => ({
                          ...current,
                          dateOfBirth: value,
                          documentType: suggestedDocument(age),
                        }));
                      }}
                      type="date"
                      value={person.dateOfBirth}
                    />
                    {ageFromBirthDate(person.dateOfBirth) !== null ? (
                      <p className="text-xs text-muted-foreground">
                        Edad calculada: {ageFromBirthDate(person.dateOfBirth)}{' '}
                        años.
                      </p>
                    ) : null}
                  </div>
                  <SelectField
                    label="Tipo de documento"
                    onChange={(value) => updateField('documentType', value)}
                    options={documentTypeOptions}
                    value={person.documentType}
                  />
                  <Field
                    label="Número de documento"
                    onChange={(value) => updateField('documentNumber', value)}
                    value={person.documentNumber}
                  />
                  <SelectField
                    label="Género"
                    onChange={(value) => updateField('gender', value)}
                    options={genderOptions}
                    value={person.gender}
                  />
                </div>
              </details>

              <details className="rounded-lg border bg-muted/20 p-4">
                <summary className="cursor-pointer text-sm font-medium marker:text-primary">
                  Añadir contexto académico y de ubicación
                </summary>
                <p className="text-xs leading-5 text-muted-foreground">
                  Estos datos ayudan a organizar grupos, cursos y
                  acompañamiento. Sólo solicita lo pertinente.
                </p>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <SelectField
                    label="Situación educativa"
                    onChange={(value) => updateField('educationStage', value)}
                    options={educationStageOptions}
                    value={person.educationStage}
                  />
                  {educationInstitutionApplies(person.educationStage) ? (
                    <Field
                      label="Institución educativa"
                      onChange={(value) =>
                        updateField('educationInstitution', value)
                      }
                      required
                      value={person.educationInstitution}
                    />
                  ) : null}
                  <SelectField
                    label="Grado o nivel"
                    onChange={(value) => updateField('educationLevel', value)}
                    options={educationLevelOptions}
                    value={person.educationLevel}
                  />
                  <SelectField
                    label="Departamento"
                    onChange={(value) => updateField('departmentCode', value)}
                    options={departmentOptions}
                    value={person.departmentCode}
                  />
                  <Field
                    label="Municipio o ciudad"
                    onChange={(value) => updateField('municipality', value)}
                    value={person.municipality}
                  />
                  <Field
                    label="Dirección"
                    onChange={(value) => updateField('address', value)}
                    value={person.address}
                  />
                  <SelectField
                    label="Estrato"
                    onChange={(value) =>
                      updateField('socioeconomicStratum', value)
                    }
                    options={socioeconomicStratumOptions}
                    value={person.socioeconomicStratum}
                  />
                  <SelectField
                    label="Motivo de registro"
                    onChange={(value) =>
                      updateField('registrationReason', value)
                    }
                    options={registrationReasonOptions}
                    value={person.registrationReason}
                  />
                  {person.registrationReason === 'other' ? (
                    <Field
                      label="Describe el motivo"
                      onChange={(value) =>
                        updateField('registrationReasonDetail', value)
                      }
                      value={person.registrationReasonDetail}
                    />
                  ) : null}
                </div>
              </details>

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
                <Button
                  disabled={!isHydrated || pending || roles.length === 0}
                  type="submit"
                >
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
                  <Link href={`/organizaciones/${slug}/miembros`}>
                    Cancelar
                  </Link>
                </Button>
              </div>
            </fieldset>
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

function SelectField({
  label,
  onChange,
  options,
  required = false,
  value,
}: Readonly<{
  label: string;
  onChange: (value: string) => void;
  options: ReadonlyArray<readonly [string, string]>;
  required?: boolean;
  value: string;
}>) {
  const id = `member-${label.toLowerCase().replaceAll(/[^a-z0-9]+/g, '-')}`;
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <select
        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs"
        id={id}
        onChange={(event) => onChange(event.target.value)}
        required={required}
        value={value}
      >
        {options.map(([optionValue, optionLabel]) => (
          <option key={`${id}-${optionValue || 'empty'}`} value={optionValue}>
            {optionLabel}
          </option>
        ))}
      </select>
    </div>
  );
}
