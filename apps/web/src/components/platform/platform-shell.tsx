'use client';

import {
  Award,
  BarChart3,
  BookOpenCheck,
  Building2,
  CalendarDays,
  ChevronDown,
  ClipboardCheck,
  FileCheck2,
  GitBranch,
  GraduationCap,
  Images,
  LayoutDashboard,
  LibraryBig,
  ListTree,
  Search,
  Settings2,
  NotebookTabs,
  Plus,
  RefreshCcw,
  Send,
  SquarePen,
  Tags,
  Target,
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
  SidebarFooter,
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

type ShellOrganization = {
  id: string;
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
  email,
  organizations,
}: Readonly<{
  children: React.ReactNode;
  email: string;
  organizations: readonly ShellOrganization[];
}>) {
  const pathname = usePathname();
  const activeOrganization =
    organizations.find((organization) =>
      pathname.startsWith(`/organizaciones/${organization.slug}`),
    ) ?? organizations[0];
  const organizationBase = activeOrganization
    ? `/organizaciones/${activeOrganization.slug}`
    : undefined;
  const learningPlayerActive =
    organizationBase !== undefined &&
    new RegExp(
      `^${escapeRegExp(organizationBase)}/aprender/[^/]+/unidades/[^/]+/?$`,
    ).test(pathname);

  if (learningPlayerActive) {
    return <div className="learning-player-frame">{children}</div>;
  }

  return (
    <SidebarProvider>
      <PlatformSidebar
        activeOrganization={activeOrganization}
        email={email}
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
          <div className="platform-topbar__context">
            <span>Espacio institucional</span>
            <p>{activeOrganization?.name ?? 'Plataforma académica'}</p>
          </div>
          <span className="platform-topbar__status">Entorno seguro</span>
          {activeOrganization ? (
            <NotificationBadge
              href={`/organizaciones/${activeOrganization.slug}/notificaciones`}
            />
          ) : null}
        </header>
        <div className="platform-content min-w-0 flex-1">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  );
}

function PlatformSidebar({
  activeOrganization,
  email,
  organizations,
  pathname,
}: Readonly<{
  activeOrganization?: ShellOrganization | undefined;
  email: string;
  organizations: readonly ShellOrganization[];
  pathname: string;
}>) {
  const capabilities = new Set(activeOrganization?.capabilities ?? []);
  const learnerOnly =
    activeOrganization?.roles.length === 1 &&
    activeOrganization.roles[0] === 'learner';
  const organizationBase = activeOrganization
    ? `/organizaciones/${activeOrganization.slug}`
    : undefined;
  const assessmentWorkspaceActive =
    organizationBase !== undefined &&
    pathname.startsWith(`${organizationBase}/evaluaciones`);
  const generalNavigation: NavigationItem[] = [
    {
      href: '/estudiar',
      icon: LayoutDashboard,
      label: 'Inicio',
      exact: true,
      visible: !learnerOnly,
    },
    ...(organizations.length > 1
      ? [
          {
            href: `${organizationBase}/buscar`,
            icon: Search,
            label: 'Buscar',
          },
          {
            href: '/organizaciones',
            icon: Building2,
            label: 'Cambiar organización',
            exact: true,
          },
        ]
      : []),
  ];
  const organizationNavigation: NavigationItem[] = organizationBase
    ? [
        {
          href: organizationBase,
          icon: GraduationCap,
          label: 'Resumen institucional',
          exact: true,
          visible: !learnerOnly,
        },
      ]
    : [];
  const academicNavigation: NavigationItem[] = organizationBase
    ? [
        {
          href: `${organizationBase}/calendario`,
          icon: CalendarDays,
          label: 'Calendario',
          visible:
            capabilities.has('scheduling.view') ||
            capabilities.has('assessment.attempt'),
        },
        {
          activePrefixes: [`${organizationBase}/clases/`],
          exact: true,
          href: `${organizationBase}/clases`,
          icon: Video,
          label: 'Clases en vivo',
          visible: capabilities.has('scheduling.view'),
        },
        {
          activePrefixes: [`${organizationBase}/aprender/`],
          exact: true,
          href: `${organizationBase}/aprendizaje`,
          icon: NotebookTabs,
          label: 'Mi aprendizaje',
          visible: capabilities.has('assessment.attempt'),
        },
        {
          children: [
            {
              activePrefixes: [`${organizationBase}/curriculo/asignaturas/`],
              href: `${organizationBase}/curriculo`,
              label: 'Estructura curricular',
              exact: true,
            },
            {
              href: `${organizationBase}/curriculo/conceptos`,
              icon: Tags,
              label: 'Conceptos',
              exact: true,
            },
            {
              href: `${organizationBase}/curriculo/objetivos`,
              icon: Target,
              label: 'Objetivos',
              exact: true,
            },
            {
              href: `${organizationBase}/curriculo/prerrequisitos`,
              icon: GitBranch,
              label: 'Prerrequisitos',
              exact: true,
            },
          ],
          href: `${organizationBase}/curriculo`,
          icon: LibraryBig,
          label: 'Currículo',
          visible: capabilities.has('catalog.view'),
        },
        {
          children: [
            {
              href: `${organizationBase}/cursos`,
              label: 'Todos los cursos',
              exact: true,
            },
            {
              href: `${organizationBase}/cursos/nuevo`,
              icon: Plus,
              label: 'Crear curso',
              exact: true,
              visible: capabilities.has('course.authoring.manage'),
            },
          ],
          href: `${organizationBase}/cursos`,
          icon: BookOpenCheck,
          label: 'Cursos',
          visible:
            capabilities.has('course.authoring.view') ||
            capabilities.has('course.approved.view'),
        },
        {
          children: [
            {
              href: `${organizationBase}/recursos`,
              label: 'Todos los recursos',
              exact: true,
            },
            {
              href: `${organizationBase}/recursos/nuevo`,
              icon: Plus,
              label: 'Cargar recurso',
              exact: true,
              visible: capabilities.has('asset.upload'),
            },
          ],
          href: `${organizationBase}/recursos`,
          icon: Images,
          label: 'Recursos',
          visible: capabilities.has('asset.library.view'),
        },
        {
          href: `${organizationBase}/biblioteca`,
          icon: LibraryBig,
          label: 'Biblioteca',
          visible: capabilities.has('course.published.view'),
        },
        {
          href: `${organizationBase}/evaluaciones/asignadas`,
          icon: ClipboardCheck,
          label: 'Mis evaluaciones',
          visible:
            !assessmentWorkspaceActive &&
            capabilities.has('assessment.attempt'),
        },
        {
          href: `${organizationBase}/evaluaciones/calificaciones`,
          icon: Award,
          label: 'Mis calificaciones',
          visible:
            !assessmentWorkspaceActive &&
            capabilities.has('assessment.attempt'),
        },
        {
          children: [
            {
              href: `${organizationBase}/evaluaciones`,
              label: 'Evaluaciones',
              exact: true,
              visible: capabilities.has('assessment.authoring.view'),
            },
            {
              href: `${organizationBase}/evaluaciones/bancos`,
              label: 'Bancos de preguntas',
              exact: true,
              visible:
                capabilities.has('assessment.bank.view') ||
                capabilities.has('assessment.question.view'),
            },
          ],
          href: `${organizationBase}/evaluaciones`,
          icon: ClipboardCheck,
          label: 'Autoría de evaluaciones',
          visible:
            !assessmentWorkspaceActive &&
            (capabilities.has('assessment.authoring.view') ||
              capabilities.has('assessment.bank.view') ||
              capabilities.has('assessment.question.view')),
        },
      ]
    : [];
  const assessmentNavigation: NavigationItem[] =
    organizationBase && assessmentWorkspaceActive
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
            visible: capabilities.has('assessment.attempt'),
          },
          {
            href: `${organizationBase}/evaluaciones/calificaciones`,
            icon: Award,
            label: 'Mis calificaciones',
            visible: capabilities.has('assessment.attempt'),
          },
        ]
      : [];
  const administrationNavigation: NavigationItem[] = organizationBase
    ? [
        {
          href: `${organizationBase}/miembros`,
          icon: Users,
          label: 'Personas y miembros',
          visible: capabilities.has('membership.view'),
        },
        {
          activePrefixes: [
            `${organizationBase}/aprendizaje/matriculas`,
            `${organizationBase}/aprendizaje/grupos`,
          ],
          children: [
            {
              href: `${organizationBase}/aprendizaje/grupos`,
              label: 'Grupos académicos',
              visible: capabilities.has('learning.cohort.view'),
            },
            {
              href: `${organizationBase}/aprendizaje/cohortes`,
              label: 'Cohortes',
              visible: capabilities.has('learning.cohort.view'),
            },
            {
              href: `${organizationBase}/aprendizaje/matriculas`,
              label: 'Matrículas',
              visible: capabilities.has('learning.enrollment.view'),
            },
          ],
          href: `${organizationBase}/aprendizaje/cohortes`,
          icon: GraduationCap,
          label: 'Grupos y matrículas',
          visible:
            capabilities.has('learning.cohort.view') ||
            capabilities.has('learning.enrollment.view'),
        },
        {
          children: [
            {
              href: `${organizationBase}/evaluaciones/entregas`,
              label: 'Entregas',
              visible: capabilities.has('assessment.delivery.view'),
            },
            {
              href: `${organizationBase}/evaluaciones/resultados`,
              label: 'Resultados',
              visible: capabilities.has('assessment.results.view'),
            },
            {
              href: `${organizationBase}/evaluaciones/calificacion-manual`,
              label: 'Calificación manual',
              visible: capabilities.has('assessment.grading.manage'),
            },
            {
              href: `${organizationBase}/evaluaciones/regrading`,
              label: 'Recalificación',
              visible: capabilities.has('assessment.regrading.view'),
            },
            {
              href: `${organizationBase}/evaluaciones/gradebooks`,
              label: 'Libros de calificaciones',
              visible: capabilities.has('assessment.gradebook.view'),
            },
            {
              href: `${organizationBase}/evaluaciones/analitica`,
              label: 'Analítica',
              visible: capabilities.has('assessment.analytics.view'),
            },
          ],
          href: `${organizationBase}/evaluaciones/entregas`,
          icon: ClipboardCheck,
          label: 'Gestión de evaluaciones',
          visible:
            !assessmentWorkspaceActive &&
            (capabilities.has('assessment.delivery.view') ||
              capabilities.has('assessment.results.view') ||
              capabilities.has('assessment.grading.manage') ||
              capabilities.has('assessment.regrading.view') ||
              capabilities.has('assessment.gradebook.view') ||
              capabilities.has('assessment.analytics.view')),
        },
        {
          href: `${organizationBase}/configuracion`,
          icon: Settings2,
          label: 'Configuración institucional',
          visible:
            capabilities.has('membership.settings.view') ||
            capabilities.has('integration.view'),
        },
      ]
    : [];
  const courseBase = organizationBase
    ? courseWorkspaceBase(pathname, organizationBase)
    : undefined;
  const courseNavigation: NavigationItem[] = courseBase
    ? [
        {
          href: courseBase,
          icon: BookOpenCheck,
          label: 'Resumen del curso',
          exact: true,
        },
        {
          activePrefixes: [`${courseBase}/unidades/`],
          href: `${courseBase}/estructura`,
          icon: ListTree,
          label: 'Estructura',
          exact: true,
        },
        {
          href: `${courseBase}/revision`,
          icon: FileCheck2,
          label: 'Revisión',
          exact: true,
        },
        {
          activePrefixes: [`${courseBase}/publicaciones/`],
          href: `${courseBase}/publicacion`,
          icon: Send,
          label: 'Publicación',
          exact: true,
          visible: capabilities.has('course.release.history.view'),
        },
      ]
    : [];

  return (
    <Sidebar collapsible="icon" variant="sidebar">
      <SidebarHeader className="border-b border-sidebar-border p-3">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              asChild
              className="h-11 data-[slot=sidebar-menu-button]:p-2"
              size="lg"
              tooltip="Plataforma académica"
            >
              <Link href="/estudiar">
                <span className="grid size-8 shrink-0 place-items-center rounded-md border border-sidebar-border bg-white text-primary shadow-xs">
                  <GraduationCap className="size-4.5" />
                </span>
                <span className="grid min-w-0 flex-1 text-left leading-tight">
                  <span className="truncate font-semibold">
                    Plataforma académica
                  </span>
                  <span className="truncate text-xs text-sidebar-foreground/70">
                    Entorno institucional
                  </span>
                </span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {generalNavigation.some((item) => item.visible !== false) ? (
          <SidebarGroup>
            <SidebarGroupLabel>Plataforma</SidebarGroupLabel>
            <SidebarGroupContent>
              <NavigationList items={generalNavigation} pathname={pathname} />
            </SidebarGroupContent>
          </SidebarGroup>
        ) : null}

        {activeOrganization ? (
          <SidebarGroup>
            <SidebarGroupLabel>Institución</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  {organizations.length > 1 ? (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <SidebarMenuButton
                          className="h-auto min-h-12"
                          tooltip={`Cambiar ${activeOrganization.name}`}
                        >
                          <Building2 />
                          <OrganizationIdentity
                            organization={activeOrganization}
                          />
                          <ChevronDown className="ml-auto group-data-[collapsible=icon]:hidden" />
                        </SidebarMenuButton>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent
                        align="start"
                        className="min-w-64"
                        side="right"
                      >
                        <DropdownMenuLabel>
                          Cambiar organización
                        </DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        {organizations
                          .filter(
                            (organization) =>
                              organization.id !== activeOrganization.id,
                          )
                          .map((organization) => (
                            <DropdownMenuItem asChild key={organization.id}>
                              <Link
                                href={`/organizaciones/${organization.slug}`}
                              >
                                <Building2 />
                                <OrganizationIdentity
                                  organization={organization}
                                />
                              </Link>
                            </DropdownMenuItem>
                          ))}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  ) : (
                    <div
                      className="flex min-h-12 items-center gap-2 overflow-hidden rounded-lg px-2 text-sidebar-foreground group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0"
                      title={activeOrganization.name}
                    >
                      <Building2 className="size-4 shrink-0" />
                      <OrganizationIdentity organization={activeOrganization} />
                    </div>
                  )}
                </SidebarMenuItem>
              </SidebarMenu>
              <NavigationList
                items={organizationNavigation}
                pathname={pathname}
              />
            </SidebarGroupContent>
          </SidebarGroup>
        ) : null}

        {assessmentNavigation.some((item) => item.visible !== false) ? (
          <SidebarGroup>
            <SidebarGroupLabel>Flujo de evaluaciones</SidebarGroupLabel>
            <SidebarGroupContent>
              <NavigationList
                items={assessmentNavigation}
                pathname={pathname}
              />
            </SidebarGroupContent>
          </SidebarGroup>
        ) : null}

        {academicNavigation.some((item) => item.visible !== false) ? (
          <SidebarGroup>
            <SidebarGroupLabel>
              {learnerOnly ? 'Mi espacio académico' : 'Gestión académica'}
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <NavigationList items={academicNavigation} pathname={pathname} />
            </SidebarGroupContent>
          </SidebarGroup>
        ) : null}

        {courseNavigation.some((item) => item.visible !== false) ? (
          <SidebarGroup>
            <SidebarGroupLabel>Curso actual</SidebarGroupLabel>
            <SidebarGroupContent>
              <NavigationList items={courseNavigation} pathname={pathname} />
            </SidebarGroupContent>
          </SidebarGroup>
        ) : null}

        {administrationNavigation.some((item) => item.visible !== false) ? (
          <SidebarGroup>
            <SidebarGroupLabel>Administración institucional</SidebarGroupLabel>
            <SidebarGroupContent>
              <NavigationList
                items={administrationNavigation}
                pathname={pathname}
              />
            </SidebarGroupContent>
          </SidebarGroup>
        ) : null}
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border p-3">
        <SidebarMenu>
          <SidebarMenuItem>
            <div className="flex items-center gap-2 overflow-hidden rounded-lg p-1.5 group-data-[collapsible=icon]:justify-center">
              <Avatar className="size-8">
                <AvatarFallback className="bg-primary/5 text-xs font-semibold text-primary">
                  {initials(email)}
                </AvatarFallback>
              </Avatar>
              <div className="min-w-0 flex-1 group-data-[collapsible=icon]:hidden">
                <p className="truncate text-sm font-medium">{email}</p>
              </div>
            </div>
          </SidebarMenuItem>
          <SidebarMenuItem className="group-data-[collapsible=icon]:hidden">
            <LogoutButton className="w-full justify-start" compact />
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
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

export function courseWorkspaceBase(
  pathname: string,
  organizationBase: string,
) {
  const prefix = `${organizationBase}/cursos/`;
  if (!pathname.startsWith(prefix)) return undefined;
  const courseSlug = pathname.slice(prefix.length).split('/')[0];
  if (!courseSlug || courseSlug === 'nuevo') return undefined;
  return `${prefix}${courseSlug}`;
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
