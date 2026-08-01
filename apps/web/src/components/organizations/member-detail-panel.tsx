'use client';

import {
  BadgeCheck,
  CircleAlert,
  KeyRound,
  LoaderCircle,
  RotateCcw,
  Save,
  ShieldCheck,
  UserRoundX,
} from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
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
import type { components, operations } from '@/lib/api/generated/platform';
import {
  useReactivateMembership,
  useReplaceMembershipRoles,
  useRevokeMemberSessions,
  useRevokeMembership,
  useSendMemberPasswordRecovery,
  useSuspendMembership,
  useUpdateMemberProfile,
} from '@/lib/organizations/hooks';
import {
  hasCapability,
  roleLabel,
  sortRoles,
} from '@/lib/organizations/labels';
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

type Membership =
  operations['organizations_memberships_retrieve']['responses'][200]['content']['application/json'];
type MemberProfile =
  operations['organizations_memberships_profile_retrieve']['responses'][200]['content']['application/json'];
type MembershipEventList =
  operations['organizations_memberships_events_list']['responses'][200]['content']['application/json'];
type MembershipEvent = MembershipEventList['results'][number];
type Role = components['schemas']['OrganizationRole'];
type DocumentType = '' | components['schemas']['DocumentTypeEnum'];
type EducationLevel = '' | components['schemas']['EducationLevelEnum'];
type EducationStage = '' | components['schemas']['EducationStageEnum'];
type Gender = '' | components['schemas']['GenderEnum'];
type MemberType = '' | components['schemas']['MemberTypeEnum'];
type RegistrationReason = '' | components['schemas']['RegistrationReasonEnum'];
type SocioeconomicStratum =
  '' | components['schemas']['SocioeconomicStratumEnum'];
type ProfileValues = {
  address: string;
  administrative_notes: string;
  date_of_birth: string;
  department_code: string;
  document_number: string;
  document_type: DocumentType;
  education_institution: string;
  education_level: EducationLevel;
  education_stage: EducationStage;
  first_name: string;
  first_surname: string;
  gender: Gender;
  institutional_id: string;
  locale: string;
  member_type: MemberType;
  middle_name: string;
  municipality: string;
  phone: string;
  preferred_name: string;
  registration_reason: RegistrationReason;
  registration_reason_detail: string;
  second_surname: string;
  socioeconomic_stratum: SocioeconomicStratum;
  timezone: string;
  whatsapp: string;
};

const assignableRoles: Role[] = [
  'administrator',
  'author',
  'reviewer',
  'instructor',
  'learner',
];

function errorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : 'No fue posible guardar los cambios.';
}

function statusLabel(status: string | undefined) {
  const labels: Record<string, string> = {
    active: 'Activa',
    revoked: 'Revocada',
    suspended: 'Suspendida',
  };
  return status ? (labels[status] ?? status) : 'Sin estado';
}

function profileValues(profile: MemberProfile): ProfileValues {
  return {
    address: profile.address ?? '',
    administrative_notes: profile.administrative_notes ?? '',
    date_of_birth: profile.date_of_birth ?? '',
    department_code: profile.department_code ?? '',
    document_number: profile.document_number ?? '',
    document_type: profile.document_type ?? '',
    education_institution: profile.education_institution ?? '',
    education_level: profile.education_level ?? '',
    education_stage: profile.education_stage ?? '',
    first_name: profile.first_name ?? '',
    first_surname: profile.first_surname ?? '',
    gender: profile.gender ?? '',
    institutional_id: profile.institutional_id ?? '',
    locale: profile.locale ?? '',
    member_type: profile.member_type ?? '',
    middle_name: profile.middle_name ?? '',
    municipality: profile.municipality ?? '',
    phone: profile.phone ?? '',
    preferred_name: profile.preferred_name ?? '',
    registration_reason: profile.registration_reason ?? '',
    registration_reason_detail: profile.registration_reason_detail ?? '',
    second_surname: profile.second_surname ?? '',
    socioeconomic_stratum: profile.socioeconomic_stratum ?? '',
    timezone: profile.timezone ?? '',
    whatsapp: profile.whatsapp ?? '',
  };
}

function membershipResponse(
  membership: components['schemas']['Membership'],
): Membership {
  return membership as unknown as Membership;
}

export function MemberDetailPanel({
  capabilities,
  events,
  initialMember,
  initialProfile,
  slug,
}: Readonly<{
  capabilities: readonly string[];
  events: MembershipEventList | undefined;
  initialMember: Membership;
  initialProfile: MemberProfile;
  slug: string;
}>) {
  const [member, setMember] = useState(initialMember);
  const [profile, setProfile] = useState(() => profileValues(initialProfile));
  const [roles, setRoles] = useState<Role[]>(member.roles as Role[]);
  const updateProfile = useUpdateMemberProfile(slug);
  const replaceRoles = useReplaceMembershipRoles(slug);
  const suspend = useSuspendMembership(slug);
  const reactivate = useReactivateMembership(slug);
  const revoke = useRevokeMembership(slug);
  const revokeSessions = useRevokeMemberSessions(slug);
  const passwordRecovery = useSendMemberPasswordRecovery(slug);
  const canEditProfile = hasCapability(
    capabilities,
    'membership.profile.manage',
  );
  const canAssignRoles = hasCapability(capabilities, 'role.assign');
  const canSuspend = hasCapability(capabilities, 'membership.suspend');
  const canReactivate = hasCapability(capabilities, 'membership.reactivate');
  const canRevoke = hasCapability(capabilities, 'membership.revoke');
  const canRevokeSessions = hasCapability(
    capabilities,
    'membership.sessions.revoke',
  );
  const canSendRecovery = hasCapability(
    capabilities,
    'membership.recovery.send',
  );
  const canManageOwner = hasCapability(capabilities, 'role.assign_owner');
  const targetIsOwner = member.roles.includes('owner');
  const canManageTarget = !targetIsOwner || canManageOwner;
  const [notice, setNotice] = useState('');

  function updateProfileField<K extends keyof ProfileValues>(
    field: K,
    value: string,
  ) {
    setProfile((current) => ({
      ...current,
      [field]: value as ProfileValues[K],
    }));
  }

  function toggleRole(role: Role, checked: boolean) {
    setRoles((current) =>
      checked
        ? current.includes(role)
          ? current
          : [...current, role]
        : current.filter((candidate) => candidate !== role),
    );
  }

  async function saveProfile(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice('');
    try {
      const saved = await updateProfile.mutateAsync({
        membershipId: member.membership_id,
        profile: {
          address: profile.address,
          date_of_birth: profile.date_of_birth || null,
          department_code: profile.department_code,
          document_number: profile.document_number,
          document_type: profile.document_type,
          education_institution: profile.education_institution,
          education_level: profile.education_level,
          education_stage: profile.education_stage,
          first_name: profile.first_name,
          first_surname: profile.first_surname,
          gender: profile.gender,
          member_type: profile.member_type,
          institutional_id: profile.institutional_id,
          preferred_name: profile.preferred_name,
          phone: profile.phone,
          middle_name: profile.middle_name,
          municipality: profile.municipality,
          registration_reason: profile.registration_reason,
          registration_reason_detail: profile.registration_reason_detail,
          second_surname: profile.second_surname,
          socioeconomic_stratum: profile.socioeconomic_stratum,
          whatsapp: profile.whatsapp,
          locale: profile.locale,
          timezone: profile.timezone,
          ...(canEditProfile
            ? { administrative_notes: profile.administrative_notes ?? '' }
            : {}),
        },
      });
      setProfile(profileValues(saved as unknown as MemberProfile));
      setNotice('Perfil institucional guardado.');
    } catch {
      // The mutation error is rendered in the form.
    }
  }

  async function saveRoles() {
    setNotice('');
    try {
      const saved = await replaceRoles.mutateAsync({
        membershipId: member.membership_id,
        roles,
      });
      setMember(
        membershipResponse(
          saved as unknown as components['schemas']['Membership'],
        ),
      );
      setRoles(saved.roles as Role[]);
      setNotice('Roles institucionales actualizados.');
    } catch {
      // The mutation error is rendered in the form.
    }
  }

  async function changeStatus(action: 'suspend' | 'reactivate' | 'revoke') {
    setNotice('');
    try {
      const service =
        action === 'suspend'
          ? suspend
          : action === 'reactivate'
            ? reactivate
            : revoke;
      const saved = await service.mutateAsync(member.membership_id);
      setMember(
        membershipResponse(
          saved as unknown as components['schemas']['Membership'],
        ),
      );
      setNotice(
        action === 'suspend'
          ? 'La membresía fue suspendida.'
          : action === 'reactivate'
            ? 'La membresía fue reactivada.'
            : 'La membresía fue revocada.',
      );
    } catch {
      // The mutation error is rendered below.
    }
  }

  async function endSessions() {
    setNotice('');
    try {
      const result = await revokeSessions.mutateAsync(member.membership_id);
      const count =
        result && typeof result === 'object' && 'revoked_sessions' in result
          ? Number(result.revoked_sessions)
          : 0;
      setNotice(
        `${count} ${count === 1 ? 'sesión fue cerrada' : 'sesiones fueron cerradas'}.`,
      );
    } catch {
      // The mutation error is rendered below.
    }
  }

  async function requestRecovery() {
    setNotice('');
    try {
      await passwordRecovery.mutateAsync(member.membership_id);
      setNotice(
        'Se enviaron instrucciones de recuperación al correo registrado.',
      );
    } catch {
      // The mutation error is rendered below.
    }
  }

  const error =
    updateProfile.error ??
    replaceRoles.error ??
    suspend.error ??
    reactivate.error ??
    revoke.error ??
    revokeSessions.error ??
    passwordRecovery.error;

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="space-y-6">
        {notice ? (
          <Alert className="border-emerald-600/20 bg-emerald-500/5">
            <BadgeCheck className="text-emerald-700" />
            <AlertTitle>Actualización aplicada</AlertTitle>
            <AlertDescription>{notice}</AlertDescription>
          </Alert>
        ) : null}
        {error ? (
          <Alert variant="destructive">
            <CircleAlert />
            <AlertTitle>No se pudo completar la operación</AlertTitle>
            <AlertDescription>{errorMessage(error)}</AlertDescription>
          </Alert>
        ) : null}

        <Card>
          <CardHeader className="gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <CardTitle>{member.user.display}</CardTitle>
              <CardDescription className="mt-1 break-all">
                {member.user.email}
              </CardDescription>
            </div>
            <Badge
              className="rounded"
              variant={member.status === 'active' ? 'secondary' : 'outline'}
            >
              {statusLabel(member.status)}
            </Badge>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Miembro desde {new Date(member.joined_at).toLocaleString('es-CO')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Perfil institucional</CardTitle>
            <CardDescription>
              Los datos pertenecen a esta organización y no se mezclan con el
              perfil global de la cuenta.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form
              className="space-y-4"
              onSubmit={(event) => void saveProfile(event)}
            >
              <div className="grid gap-4 sm:grid-cols-2">
                <ProfileField
                  disabled={!canEditProfile}
                  label="Primer nombre"
                  onChange={(value) => updateProfileField('first_name', value)}
                  value={profile.first_name}
                />
                <ProfileField
                  disabled={!canEditProfile}
                  label="Segundo nombre"
                  onChange={(value) => updateProfileField('middle_name', value)}
                  value={profile.middle_name}
                />
                <ProfileField
                  disabled={!canEditProfile}
                  label="Primer apellido"
                  onChange={(value) =>
                    updateProfileField('first_surname', value)
                  }
                  value={profile.first_surname}
                />
                <ProfileField
                  disabled={!canEditProfile}
                  label="Segundo apellido"
                  onChange={(value) =>
                    updateProfileField('second_surname', value)
                  }
                  value={profile.second_surname}
                />
                <ProfileSelectField
                  disabled={!canEditProfile}
                  label="Tipo de miembro"
                  onChange={(value) => updateProfileField('member_type', value)}
                  options={[['', 'Sin seleccionar'], ...memberTypeOptions]}
                  value={profile.member_type}
                />
                <ProfileField
                  disabled={!canEditProfile}
                  label="ID institucional"
                  onChange={(value) =>
                    updateProfileField('institutional_id', value)
                  }
                  value={profile.institutional_id}
                />
                <ProfileField
                  disabled={!canEditProfile}
                  label="Nombre visible"
                  onChange={(value) =>
                    updateProfileField('preferred_name', value)
                  }
                  value={profile.preferred_name}
                />
                <ProfileField
                  disabled={!canEditProfile}
                  label="WhatsApp"
                  onChange={(value) => updateProfileField('whatsapp', value)}
                  type="tel"
                  value={profile.whatsapp}
                />
                <div className="space-y-2">
                  <ProfileField
                    disabled={!canEditProfile}
                    label="Fecha de nacimiento"
                    onChange={(value) => {
                      const documentType = suggestedDocument(
                        ageFromBirthDate(value),
                      ) as DocumentType;
                      setProfile((current) => ({
                        ...current,
                        date_of_birth: value,
                        document_type: documentType,
                      }));
                    }}
                    type="date"
                    value={profile.date_of_birth}
                  />
                  {ageFromBirthDate(profile.date_of_birth) !== null ? (
                    <p className="text-xs text-muted-foreground">
                      Edad calculada: {ageFromBirthDate(profile.date_of_birth)}{' '}
                      años
                    </p>
                  ) : null}
                </div>
                <ProfileSelectField
                  disabled={!canEditProfile}
                  label="Tipo de documento"
                  onChange={(value) =>
                    updateProfileField('document_type', value)
                  }
                  options={documentTypeOptions}
                  value={profile.document_type}
                />
                <ProfileField
                  disabled={!canEditProfile}
                  label="Número de documento"
                  onChange={(value) =>
                    updateProfileField('document_number', value)
                  }
                  value={profile.document_number}
                />
                <ProfileSelectField
                  disabled={!canEditProfile}
                  label="Género"
                  onChange={(value) => updateProfileField('gender', value)}
                  options={genderOptions}
                  value={profile.gender}
                />
                <ProfileSelectField
                  disabled={!canEditProfile}
                  label="Situación educativa"
                  onChange={(value) => {
                    setProfile((current) => ({
                      ...current,
                      education_stage: value as EducationStage,
                      education_institution: educationInstitutionApplies(value)
                        ? current.education_institution
                        : '',
                    }));
                  }}
                  options={educationStageOptions}
                  value={profile.education_stage}
                />
                {educationInstitutionApplies(profile.education_stage) ? (
                  <ProfileField
                    disabled={!canEditProfile}
                    label="Institución educativa"
                    onChange={(value) =>
                      updateProfileField('education_institution', value)
                    }
                    value={profile.education_institution}
                  />
                ) : null}
                <ProfileSelectField
                  disabled={!canEditProfile}
                  label="Grado o nivel"
                  onChange={(value) =>
                    updateProfileField('education_level', value)
                  }
                  options={educationLevelOptions}
                  value={profile.education_level}
                />
                <ProfileSelectField
                  disabled={!canEditProfile}
                  label="Departamento"
                  onChange={(value) =>
                    updateProfileField('department_code', value)
                  }
                  options={departmentOptions}
                  value={profile.department_code}
                />
                <ProfileField
                  disabled={!canEditProfile}
                  label="Municipio o ciudad"
                  onChange={(value) =>
                    updateProfileField('municipality', value)
                  }
                  value={profile.municipality}
                />
                <ProfileField
                  disabled={!canEditProfile}
                  label="Dirección"
                  onChange={(value) => updateProfileField('address', value)}
                  value={profile.address}
                />
                <ProfileSelectField
                  disabled={!canEditProfile}
                  label="Estrato"
                  onChange={(value) =>
                    updateProfileField('socioeconomic_stratum', value)
                  }
                  options={socioeconomicStratumOptions}
                  value={profile.socioeconomic_stratum}
                />
                <ProfileSelectField
                  disabled={!canEditProfile}
                  label="Motivo de registro"
                  onChange={(value) => {
                    setProfile((current) => ({
                      ...current,
                      registration_reason: value as RegistrationReason,
                      registration_reason_detail:
                        value === 'other'
                          ? current.registration_reason_detail
                          : '',
                    }));
                  }}
                  options={registrationReasonOptions}
                  value={profile.registration_reason}
                />
                {profile.registration_reason === 'other' ? (
                  <ProfileField
                    disabled={!canEditProfile}
                    label="Detalle del motivo"
                    onChange={(value) =>
                      updateProfileField('registration_reason_detail', value)
                    }
                    value={profile.registration_reason_detail}
                  />
                ) : null}
                <ProfileSelectField
                  disabled={!canEditProfile}
                  label="Idioma"
                  onChange={(value) => updateProfileField('locale', value)}
                  options={[
                    ['es', 'Español'],
                    ['es-CO', 'Español (Colombia)'],
                  ]}
                  value={profile.locale}
                />
                <ProfileSelectField
                  disabled={!canEditProfile}
                  label="Zona horaria"
                  onChange={(value) => updateProfileField('timezone', value)}
                  options={[
                    ['America/Bogota', 'Colombia (Bogotá)'],
                    ['UTC', 'UTC'],
                  ]}
                  value={profile.timezone}
                />
              </div>
              {canEditProfile ? (
                <div className="space-y-2">
                  <Label htmlFor="administrative-notes">
                    Notas administrativas
                  </Label>
                  <textarea
                    className="min-h-24 w-full rounded-md border bg-transparent px-3 py-2 text-sm shadow-xs"
                    id="administrative-notes"
                    onChange={(event) =>
                      updateProfileField(
                        'administrative_notes',
                        event.target.value,
                      )
                    }
                    value={profile.administrative_notes ?? ''}
                  />
                </div>
              ) : null}
              {canEditProfile ? (
                <Button disabled={updateProfile.isPending} type="submit">
                  {updateProfile.isPending ? (
                    <LoaderCircle className="animate-spin" />
                  ) : (
                    <Save />
                  )}
                  Guardar perfil
                </Button>
              ) : null}
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Roles y acceso</CardTitle>
            <CardDescription>
              Los cambios pasan por la política institucional; no existe un rol
              editable en el navegador.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-1.5">
              {sortRoles(member.roles as Role[]).map((role) => (
                <Badge className="rounded" key={role} variant="outline">
                  {roleLabel(role)}
                </Badge>
              ))}
            </div>
            {canAssignRoles &&
            canManageTarget &&
            member.status !== 'revoked' ? (
              <>
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
                <Button
                  disabled={replaceRoles.isPending || roles.length === 0}
                  onClick={() => void saveRoles()}
                  type="button"
                  variant="outline"
                >
                  {replaceRoles.isPending ? (
                    <LoaderCircle className="animate-spin" />
                  ) : (
                    <ShieldCheck />
                  )}
                  Guardar roles
                </Button>
              </>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Actividad institucional</CardTitle>
            <CardDescription>
              Historial de cambios de membresía disponible para auditoría.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {events?.results.length ? (
              <ol className="space-y-3 border-l pl-4">
                {events.results.map((event) => (
                  <EventItem event={event} key={event.id} />
                ))}
              </ol>
            ) : (
              <p className="text-sm text-muted-foreground">
                No hay eventos visibles para tu nivel de acceso.
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <aside className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Acciones de acceso</CardTitle>
            <CardDescription>
              Estas acciones se registran y se vuelven a autorizar en el
              servidor.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {member.status === 'active' && canSuspend && canManageTarget ? (
              <Button
                disabled={suspend.isPending}
                onClick={() => void changeStatus('suspend')}
                type="button"
                variant="outline"
              >
                <UserRoundX />
                Suspender membresía
              </Button>
            ) : null}
            {member.status === 'suspended' &&
            canReactivate &&
            canManageTarget ? (
              <Button
                disabled={reactivate.isPending}
                onClick={() => void changeStatus('reactivate')}
                type="button"
              >
                <RotateCcw />
                Reactivar membresía
              </Button>
            ) : null}
            {member.status !== 'revoked' && canRevoke && canManageTarget ? (
              <Button
                disabled={revoke.isPending}
                onClick={() => void changeStatus('revoke')}
                type="button"
                variant="destructive"
              >
                <UserRoundX />
                Revocar membresía
              </Button>
            ) : null}
            {canRevokeSessions ? (
              <Button
                disabled={revokeSessions.isPending}
                onClick={() => void endSessions()}
                type="button"
                variant="outline"
              >
                <KeyRound />
                Cerrar sesiones
              </Button>
            ) : null}
            {canSendRecovery ? (
              <Button
                disabled={passwordRecovery.isPending}
                onClick={() => void requestRecovery()}
                type="button"
                variant="outline"
              >
                <KeyRound />
                Enviar instrucciones
              </Button>
            ) : null}
          </CardContent>
        </Card>
        <Button asChild className="w-full" variant="outline">
          <Link href={`/organizaciones/${slug}/miembros`}>
            Volver al directorio
          </Link>
        </Button>
      </aside>
    </div>
  );
}

function ProfileField({
  disabled,
  label,
  onChange,
  type = 'text',
  value,
}: Readonly<{
  disabled: boolean;
  label: string;
  onChange: (value: string) => void;
  type?: React.HTMLInputTypeAttribute;
  value: string;
}>) {
  const id = `profile-${label.toLowerCase().replaceAll(/[^a-z0-9]+/g, '-')}`;
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Input
        disabled={disabled}
        id={id}
        onChange={(event) => onChange(event.target.value)}
        type={type}
        value={value}
      />
    </div>
  );
}

function ProfileSelectField({
  disabled,
  label,
  onChange,
  options,
  value,
}: Readonly<{
  disabled: boolean;
  label: string;
  onChange: (value: string) => void;
  options: ReadonlyArray<readonly [string, string]>;
  value: string;
}>) {
  const id = `profile-${label.toLowerCase().replaceAll(/[^a-z0-9]+/g, '-')}`;
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <select
        className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm disabled:cursor-not-allowed disabled:opacity-50"
        disabled={disabled}
        id={id}
        onChange={(event) => onChange(event.target.value)}
        value={value}
      >
        {options.map(([optionValue, optionLabel]) => (
          <option key={optionValue || 'blank'} value={optionValue}>
            {optionLabel}
          </option>
        ))}
      </select>
    </div>
  );
}

function EventItem({ event }: Readonly<{ event: MembershipEvent }>) {
  return (
    <li className="relative text-sm before:absolute before:-left-[1.34rem] before:top-1.5 before:size-2 before:rounded-full before:bg-primary">
      <p className="font-medium">
        {event.event_type.replaceAll('_', ' ')}
        {event.role ? ` · ${roleLabel(event.role as Role)}` : ''}
      </p>
      <p className="mt-0.5 text-xs text-muted-foreground">
        {new Date(event.created_at).toLocaleString('es-CO')}
      </p>
    </li>
  );
}
