'use client';

import {
  Award,
  BarChart3,
  BookOpenCheck,
  Building2,
  CalendarDays,
  CircleHelp,
  ChevronDown,
  ClipboardCheck,
  FileCheck2,
  GraduationCap,
  Images,
  LayoutDashboard,
  LibraryBig,
  Search,
  Settings2,
  NotebookTabs,
  Plus,
  RefreshCcw,
  Send,
  SquarePen,
  UserRound,
  Users,
  Video,
} from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { LogoutButton } from '@/components/auth/logout-button';
import { NotificationBadge } from '@/components/notifications/notification-badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
  useSidebar,
} from '@/components/ui/sidebar';
import {
  roleLabel,
  sortRoles,
  type OrganizationRole,
} from '@/lib/organizations/labels';
import { primaryWorkspaceHref } from '@/lib/organizations/workspace-route';

type ShellOrganization = {
  id: string;
  membership_id: string;
  name: string;
  slug: string;
  roles: readonly OrganizationRole[];
  capabilities: readonly string[];
};

type NavigationItem = {
  activePrefixes?: readonly string[];
  children?: readonly NavigationChild[];
  exact?: boolean;
  href: string;
  icon: typeof LayoutDashboard;
  label: string;
  visible?: boolean;
};

type NavigationChild = Omit<NavigationItem, 'children' | 'icon'> & {
  icon?: typeof LayoutDashboard;
};

export function PlatformShell({
  children,
  displayName,
  isPlatformOperator,
  organizations,
}: Readonly<{
  children: React.ReactNode;
  displayName: string;
  isPlatformOperator: boolean;
  organizations: readonly ShellOrganization[];
}>) {
  const pathname = usePathname();
  const activeOrganization =
    organizations.find((organization) =>
      pathname.startsWith(`/organizaciones/${organization.slug}`),
    ) ?? (pathname === '/estudiar' ? organizations[0] : undefined);
  const organizationBase = activeOrganization
    ? `/organizaciones/${activeOrganization.slug}`
    : undefined;
  const learningPlayerActive =
    organizationBase !== undefined &&
    isImmersiveLearningPath(pathname, organizationBase);

  if (learningPlayerActive) {
    return <div className="learning-player-frame">{children}</div>;
  }

  return (
    <SidebarProvider>
      <PlatformSidebar
        activeOrganization={activeOrganization}
        isPlatformOperator={isPlatformOperator}
        organizations={organizations}
        pathname={pathname}
      />
      <SidebarInset className="min-w-0 bg-background">
        <header className="platform-topbar">
          <SidebarTrigger
            aria-label="Mostrar u ocultar navegación"
            className="-ml-1"
          />
          <div className="platform-topbar__divider" aria-hidden="true" />
          <div className="ml-auto flex items-center gap-2">
            {activeOrganization?.capabilities.some((capability) =>
              ['search.authoring.use', 'search.institutional.use'].includes(
                capability,
              ),
            ) ? (
              <Link
                aria-label="Buscar en la institución"
                className="grid size-9 place-items-center rounded-full border bg-background text-muted-foreground shadow-xs transition-colors hover:bg-muted hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                href={`/organizaciones/${activeOrganization.slug}/buscar`}
                title="Buscar"
              >
                <Search className="size-4" />
              </Link>
            ) : null}
            {activeOrganization ? (
              <NotificationBadge
                href={`/organizaciones/${activeOrganization.slug}/notificaciones`}
              />
            ) : null}
            <AccountMenu
              displayName={displayName}
              isPlatformOperator={isPlatformOperator}
              organization={activeOrganization}
            />
          </div>
        </header>
        <div className="platform-content min-w-0 flex-1">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  );
}

export function isImmersiveLearningPath(
  pathname: string,
  organizationBase: string,
) {
  const base = escapeRegExp(organizationBase);
  return [
    new RegExp(`^${base}/aprender/[^/]+/(?:unidades|actividades)/[^/]+/?$`),
    new RegExp(`^${base}/evaluaciones/intentos/[^/]+/?$`),
  ].some((pattern) => pattern.test(pathname));
}

function PlatformSidebar({
  activeOrganization,
  isPlatformOperator,
  organizations,
  pathname,
}: Readonly<{
  activeOrganization?: ShellOrganization | undefined;
  isPlatformOperator: boolean;
  organizations: readonly ShellOrganization[];
  pathname: string;
}>) {
  const capabilities = new Set(activeOrganization?.capabilities ?? []);
  const roles = new Set(activeOrganization?.roles ?? []);
  const ownerGovernance = roles.has('owner');
  const institutionOperations = roles.has('administrator');
  const institutionGovernance = ownerGovernance || institutionOperations;
  const contentWorkspace = roles.has('author') || roles.has('reviewer');
  const teachingWorkspace = roles.has('instructor');
  const learnerWorkspace = roles.has('learner');
  const organizationBase = activeOrganization
    ? `/organizaciones/${activeOrganization.slug}`
    : undefined;
  const academicGroupLabel = institutionOperations
    ? 'Operación académica'
    : teachingWorkspace && contentWorkspace
      ? 'Trabajo académico'
      : teachingWorkspace
        ? 'Docencia'
        : 'Autoría y contenido';
  const platformAdministrationNavigation: NavigationItem[] = isPlatformOperator
    ? [
        {
          href: '/administracion/organizaciones',
          icon: Building2,
          label: 'Instituciones',
          exact: true,
        },
        {
          activePrefixes: ['/administracion/configuracion/'],
          href: '/administracion/configuracion',
          icon: Settings2,
          label: 'Registro y acceso',
          exact: true,
        },
      ]
    : [];
  const learnerNavigation: NavigationItem[] = organizationBase
    ? [
        {
          activePrefixes: [`${organizationBase}/aprender/`],
          exact: true,
          href: `${organizationBase}/aprendizaje`,
          icon: NotebookTabs,
          label: 'Mi aprendizaje',
          visible: learnerWorkspace,
        },
        {
          href: `${organizationBase}/calendario`,
          icon: CalendarDays,
          label: 'Mi calendario',
          visible: learnerWorkspace && !teachingWorkspace,
        },
        {
          activePrefixes: [`${organizationBase}/clases/`],
          exact: true,
          href: `${organizationBase}/clases`,
          icon: Video,
          label: 'Mis clases en vivo',
          visible: learnerWorkspace && !teachingWorkspace,
        },
      ]
    : [];
  const academicNavigation: NavigationItem[] = organizationBase
    ? [
        {
          href: `${organizationBase}/aprendizaje/mis-asignaturas`,
          icon: LibraryBig,
          label: 'Mis asignaturas',
          exact: true,
          visible: teachingWorkspace,
        },
        {
          href: `${organizationBase}/aprendizaje/cohortes`,
          icon: GraduationCap,
          label: 'Mis grupos',
          visible: teachingWorkspace,
        },
        {
          activePrefixes: [`${organizationBase}/curriculo/asignaturas/`],
          href: `${organizationBase}/curriculo`,
          icon: LibraryBig,
          label: 'Currículo',
          visible:
            (institutionOperations || contentWorkspace) &&
            capabilities.has('catalog.view'),
        },
        {
          href: `${organizationBase}/aprendizaje/mis-asignaturas`,
          icon: Users,
          label: 'Responsabilidades docentes',
          exact: true,
          visible:
            institutionOperations &&
            capabilities.has('catalog.teaching_responsibility.manage'),
        },
        {
          activePrefixes: [`${organizationBase}/cursos/`],
          exact: true,
          href: capabilities.has('course.published.view')
            ? `${organizationBase}/cursos`
            : `${organizationBase}/cursos/autoria`,
          icon: BookOpenCheck,
          label: 'Cursos',
          visible:
            (institutionOperations || contentWorkspace || teachingWorkspace) &&
            (capabilities.has('course.authoring.view') ||
              capabilities.has('course.approved.view')),
        },
      ]
    : [];
  const academicToolsNavigation: NavigationItem[] = organizationBase
    ? [
        {
          href: `${organizationBase}/calendario`,
          icon: CalendarDays,
          label:
            teachingWorkspace && !institutionOperations
              ? 'Mi calendario'
              : 'Calendario',
          visible: institutionOperations || teachingWorkspace,
        },
        {
          activePrefixes: [`${organizationBase}/clases/`],
          exact: true,
          href: `${organizationBase}/clases`,
          icon: Video,
          label:
            teachingWorkspace && !institutionOperations
              ? 'Mis clases en vivo'
              : 'Clases en vivo',
          visible: institutionOperations || teachingWorkspace,
        },
        {
          href: `${organizationBase}/recursos`,
          icon: Images,
          label: 'Recursos',
          visible:
            (institutionOperations || contentWorkspace || teachingWorkspace) &&
            capabilities.has('asset.library.view'),
        },
      ]
    : [];
  const assessmentNavigation: NavigationItem[] = organizationBase
    ? [
        {
          href: `${organizationBase}/evaluaciones`,
          icon: ClipboardCheck,
          label: 'Panel de evaluaciones',
          exact: true,
          visible: capabilities.has('assessment.authoring.view'),
        },
        {
          href: `${organizationBase}/evaluaciones/nueva`,
          icon: Plus,
          label: 'Nueva evaluación',
          exact: true,
          visible: capabilities.has('assessment.authoring.manage'),
        },
        {
          href: `${organizationBase}/evaluaciones/bancos`,
          icon: NotebookTabs,
          label: 'Bancos de preguntas',
          visible:
            capabilities.has('assessment.bank.view') ||
            capabilities.has('assessment.question.view'),
        },
        {
          href: `${organizationBase}/evaluaciones/entregas`,
          icon: Send,
          label: 'Entregas',
          visible: capabilities.has('assessment.delivery.view'),
        },
        {
          href: `${organizationBase}/evaluaciones/resultados`,
          icon: FileCheck2,
          label: 'Resultados',
          visible: capabilities.has('assessment.results.view'),
        },
        {
          href: `${organizationBase}/evaluaciones/calificacion-manual`,
          icon: SquarePen,
          label: 'Calificación manual',
          visible: capabilities.has('assessment.grading.manage'),
        },
        {
          href: `${organizationBase}/evaluaciones/regrading`,
          icon: RefreshCcw,
          label: 'Recalificación',
          visible: capabilities.has('assessment.regrading.view'),
        },
        {
          href: `${organizationBase}/evaluaciones/gradebooks`,
          icon: BookOpenCheck,
          label: 'Libros de calificaciones',
          visible: capabilities.has('assessment.gradebook.view'),
        },
        {
          href: `${organizationBase}/evaluaciones/analitica`,
          icon: BarChart3,
          label: 'Analítica de ítems',
          visible: capabilities.has('assessment.analytics.view'),
        },
        {
          href: `${organizationBase}/evaluaciones/asignadas`,
          icon: GraduationCap,
          label: 'Mis evaluaciones',
          visible: learnerWorkspace && capabilities.has('assessment.attempt'),
        },
        {
          href: `${organizationBase}/evaluaciones/calificaciones`,
          icon: Award,
          label: 'Mis calificaciones',
          visible: learnerWorkspace && capabilities.has('assessment.attempt'),
        },
      ]
    : [];
  const preparationNavigation: NavigationItem[] =
    organizationBase && institutionGovernance
      ? [
          {
            href: `${organizationBase}/miembros`,
            icon: Users,
            label: 'Personas',
            visible: capabilities.has('membership.view'),
          },
          {
            href: `${organizationBase}/aprendizaje/periodos`,
            icon: CalendarDays,
            label: 'Períodos',
            visible: capabilities.has('learning.cohort.view'),
          },
          {
            href: `${organizationBase}/aprendizaje/grupos`,
            icon: Users,
            label: 'Grupos',
            visible: capabilities.has('learning.cohort.view'),
          },
        ]
      : [];
  const executionNavigation: NavigationItem[] =
    organizationBase && institutionGovernance
      ? [
          {
            href: `${organizationBase}/aprendizaje/cohortes`,
            icon: GraduationCap,
            label: 'Secciones',
            visible: capabilities.has('learning.cohort.view'),
          },
          {
            href: `${organizationBase}/aprendizaje/matriculas`,
            icon: Users,
            label: 'Matrículas individuales',
            visible: capabilities.has('learning.enrollment.view'),
          },
        ]
      : [];
  const orderedAcademicNavigation = orderNavigation(
    academicNavigation,
    institutionOperations
      ? ['Currículo', 'Responsabilidades docentes', 'Cursos']
      : contentWorkspace
        ? ['Currículo', 'Cursos']
        : ['Mis asignaturas', 'Mis grupos'],
  );
  return (
    <Sidebar collapsible="icon" variant="sidebar">
      <SidebarHeader className="border-b border-sidebar-border p-3">
        <SidebarMenu>
          <SidebarMenuItem className="relative">
            <SidebarMenuButton
              asChild
              className="h-11 data-[slot=sidebar-menu-button]:p-2"
              size="lg"
              tooltip={activeOrganization?.name ?? 'Control de plataforma'}
            >
              <Link
                href={
                  activeOrganization
                    ? primaryWorkspaceHref(
                        activeOrganization.slug,
                        activeOrganization.roles,
                      )
                    : '/administracion/organizaciones'
                }
              >
                <span className="grid size-8 shrink-0 place-items-center rounded-md border border-sidebar-border bg-white text-primary shadow-xs">
                  {activeOrganization ? (
                    <Building2 className="size-4.5" />
                  ) : (
                    <GraduationCap className="size-4.5" />
                  )}
                </span>
                {activeOrganization ? (
                  <OrganizationIdentity organization={activeOrganization} />
                ) : (
                  <span className="grid min-w-0 flex-1 text-left leading-tight">
                    <span className="truncate font-semibold">
                      Control de plataforma
                    </span>
                    <span className="truncate text-xs text-sidebar-foreground/70">
                      Superadministrador
                    </span>
                  </span>
                )}
              </Link>
            </SidebarMenuButton>
            {activeOrganization && organizations.length > 1 ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <SidebarMenuButton
                    aria-label="Cambiar organización"
                    className="absolute top-5 right-4 size-7 group-data-[collapsible=icon]:hidden"
                    size="sm"
                    tooltip="Cambiar organización"
                  >
                    <ChevronDown />
                  </SidebarMenuButton>
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  align="start"
                  className="min-w-72"
                  side="right"
                >
                  <DropdownMenuLabel>Cambiar organización</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {organizations.map((organization) => (
                    <DropdownMenuItem asChild key={organization.id}>
                      <Link
                        href={primaryWorkspaceHref(
                          organization.slug,
                          organization.roles,
                        )}
                      >
                        <Building2 />
                        <OrganizationIdentity organization={organization} />
                      </Link>
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            ) : null}
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {platformAdministrationNavigation.some(
          (item) => item.visible !== false,
        ) ? (
          <SidebarGroup>
            <SidebarGroupLabel>Control de plataforma</SidebarGroupLabel>
            <SidebarGroupContent>
              <NavigationList
                items={platformAdministrationNavigation}
                pathname={pathname}
              />
            </SidebarGroupContent>
          </SidebarGroup>
        ) : null}

        {learnerNavigation.some((item) => item.visible !== false) ? (
          <SidebarGroup>
            <SidebarGroupLabel>Mi aprendizaje</SidebarGroupLabel>
            <SidebarGroupContent>
              <NavigationList items={learnerNavigation} pathname={pathname} />
            </SidebarGroupContent>
          </SidebarGroup>
        ) : null}

        {preparationNavigation.some((item) => item.visible !== false) ? (
          <SidebarGroup>
            <SidebarGroupLabel>Institución</SidebarGroupLabel>
            <SidebarGroupContent>
              <NavigationList
                items={preparationNavigation}
                pathname={pathname}
              />
            </SidebarGroupContent>
          </SidebarGroup>
        ) : null}

        {orderedAcademicNavigation.some((item) => item.visible !== false) ? (
          <SidebarGroup>
            <SidebarGroupLabel>
              {institutionOperations ? 'Diseño académico' : academicGroupLabel}
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <NavigationList
                items={orderedAcademicNavigation}
                pathname={pathname}
              />
            </SidebarGroupContent>
          </SidebarGroup>
        ) : null}

        {assessmentNavigation.some((item) => item.visible !== false) ? (
          <SidebarGroup>
            <SidebarGroupLabel>Evaluaciones</SidebarGroupLabel>
            <SidebarGroupContent>
              <NavigationList
                items={assessmentNavigation}
                pathname={pathname}
              />
            </SidebarGroupContent>
          </SidebarGroup>
        ) : null}

        {executionNavigation.some((item) => item.visible !== false) ? (
          <SidebarGroup>
            <SidebarGroupLabel>Operación académica</SidebarGroupLabel>
            <SidebarGroupContent>
              <NavigationList items={executionNavigation} pathname={pathname} />
            </SidebarGroupContent>
          </SidebarGroup>
        ) : null}

        {academicToolsNavigation.some((item) => item.visible !== false) ? (
          <SidebarGroup>
            <SidebarGroupLabel>Herramientas académicas</SidebarGroupLabel>
            <SidebarGroupContent>
              <NavigationList
                items={academicToolsNavigation}
                pathname={pathname}
              />
            </SidebarGroupContent>
          </SidebarGroup>
        ) : null}
      </SidebarContent>

      <SidebarRail />
    </Sidebar>
  );
}

function AccountMenu({
  displayName,
  isPlatformOperator,
  organization,
}: Readonly<{
  displayName: string;
  isPlatformOperator: boolean;
  organization?: ShellOrganization | undefined;
}>) {
  const profileHref = organization
    ? `/organizaciones/${organization.slug}/miembros/${organization.membership_id}`
    : '/estudiar';
  const settingsHref = organization
    ? `/organizaciones/${organization.slug}/notificaciones/preferencias`
    : '/administracion/configuracion';
  const helpHref = organization
    ? `/organizaciones/${organization.slug}/ayuda`
    : '/administracion/ayuda';
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          aria-label={`Abrir menú de cuenta de ${displayName}`}
          className="flex h-9 max-w-56 items-center gap-2 rounded-full border bg-background py-1 pr-3 pl-1 shadow-xs transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          type="button"
        >
          <Avatar className="size-7">
            <AvatarFallback className="bg-primary text-[0.65rem] font-semibold text-primary-foreground">
              {initials(displayName)}
            </AvatarFallback>
          </Avatar>
          <span className="hidden truncate text-sm font-medium sm:block">
            {displayName}
          </span>
          <ChevronDown className="size-3.5 text-muted-foreground" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64 p-1.5">
        <DropdownMenuLabel className="px-2 py-2">
          <span className="block truncate text-sm font-semibold">
            {displayName}
          </span>
          <span className="mt-0.5 block text-xs font-normal text-muted-foreground">
            {organization
              ? sortRoles(organization.roles).map(roleLabel).join(' · ')
              : isPlatformOperator
                ? 'Administración de plataforma'
                : 'Cuenta personal'}
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {organization ? (
          <DropdownMenuItem asChild>
            <Link href={profileHref}>
              <UserRound />
              Mi perfil
            </Link>
          </DropdownMenuItem>
        ) : null}
        <DropdownMenuItem asChild>
          <Link href={settingsHref}>
            <Settings2 />
            {organization ? 'Preferencias' : 'Configuración'}
          </Link>
        </DropdownMenuItem>
        {organization?.capabilities.some((capability) =>
          ['membership.settings.view', 'integration.view'].includes(capability),
        ) ? (
          <DropdownMenuItem asChild>
            <Link href={`/organizaciones/${organization.slug}/configuracion`}>
              <Building2 />
              Configuración
            </Link>
          </DropdownMenuItem>
        ) : null}
        <DropdownMenuItem asChild>
          <Link href={helpHref}>
            <CircleHelp />
            Ayuda y guía de uso
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <div className="p-0.5">
          <LogoutButton
            className="w-full justify-start text-destructive hover:text-destructive"
            compact
          />
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function OrganizationIdentity({
  organization,
}: Readonly<{ organization: ShellOrganization }>) {
  return (
    <span className="grid min-w-0 flex-1 text-left group-data-[collapsible=icon]:hidden">
      <span className="truncate font-medium">{organization.name}</span>
      <span className="truncate text-xs text-sidebar-foreground/70">
        {sortRoles(organization.roles).map(roleLabel).join(', ')}
      </span>
    </span>
  );
}

function NavigationList({
  items,
  pathname,
}: Readonly<{ items: NavigationItem[]; pathname: string }>) {
  return (
    <SidebarMenu>
      {items
        .filter((item) => item.visible !== false)
        .map((item) => {
          const visibleChildren = item.children?.filter(
            (child) => child.visible !== false,
          );
          const childIsActive =
            visibleChildren?.some((child) =>
              isNavigationItemActive(child, pathname),
            ) ?? false;
          return (
            <SidebarMenuItem key={item.href}>
              <PlatformNavigationLink
                href={item.href}
                icon={item.icon}
                isActive={isNavigationItemActive(item, pathname)}
                isCurrent={pathname === item.href && !childIsActive}
                label={item.label}
              />
              {visibleChildren?.length ? (
                <SidebarMenuSub>
                  {visibleChildren.map((child) => (
                    <SidebarMenuSubItem key={child.href}>
                      <PlatformNavigationSubLink
                        href={child.href}
                        isActive={isNavigationItemActive(child, pathname)}
                        isCurrent={pathname === child.href}
                        label={child.label}
                        {...(child.icon ? { icon: child.icon } : {})}
                      />
                    </SidebarMenuSubItem>
                  ))}
                </SidebarMenuSub>
              ) : null}
            </SidebarMenuItem>
          );
        })}
    </SidebarMenu>
  );
}

function orderNavigation(
  items: readonly NavigationItem[],
  labels: readonly string[],
) {
  const priority = new Map(labels.map((label, index) => [label, index]));
  return [...items].sort(
    (left, right) =>
      (priority.get(left.label) ?? labels.length) -
      (priority.get(right.label) ?? labels.length),
  );
}

function PlatformNavigationLink({
  href,
  icon: Icon,
  isActive,
  isCurrent,
  label,
}: Readonly<{
  href: string;
  icon: typeof LayoutDashboard;
  isActive: boolean;
  isCurrent: boolean;
  label: string;
}>) {
  const { isMobile, setOpenMobile } = useSidebar();
  return (
    <SidebarMenuButton
      asChild
      className="relative data-[active=true]:bg-sidebar-accent data-[active=true]:font-semibold data-[active=true]:text-sidebar-accent-foreground data-[active=true]:before:absolute data-[active=true]:before:inset-y-1.5 data-[active=true]:before:left-0 data-[active=true]:before:w-0.5 data-[active=true]:before:rounded-full data-[active=true]:before:bg-primary"
      isActive={isActive}
      tooltip={label}
    >
      <Link
        aria-current={isCurrent ? 'page' : undefined}
        href={href}
        onClick={() => {
          if (isMobile) setOpenMobile(false);
        }}
      >
        <Icon />
        <span>{label}</span>
      </Link>
    </SidebarMenuButton>
  );
}

function PlatformNavigationSubLink({
  href,
  icon: Icon,
  isActive,
  isCurrent,
  label,
}: Readonly<{
  href: string;
  icon?: typeof LayoutDashboard;
  isActive: boolean;
  isCurrent: boolean;
  label: string;
}>) {
  const { isMobile, setOpenMobile } = useSidebar();
  return (
    <SidebarMenuSubButton asChild isActive={isActive}>
      <Link
        aria-current={isCurrent ? 'page' : undefined}
        href={href}
        onClick={() => {
          if (isMobile) setOpenMobile(false);
        }}
      >
        {Icon ? <Icon /> : null}
        <span>{label}</span>
      </Link>
    </SidebarMenuSubButton>
  );
}

export function isNavigationItemActive(
  item: Pick<NavigationItem, 'activePrefixes' | 'exact' | 'href'>,
  pathname: string,
) {
  return (
    pathname === item.href ||
    item.activePrefixes?.some((prefix) => pathname.startsWith(prefix)) ===
      true ||
    (!item.exact && pathname.startsWith(`${item.href}/`))
  );
}

function initials(email: string) {
  return email
    .split('@')[0]
    ?.split(/[._-]/)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
