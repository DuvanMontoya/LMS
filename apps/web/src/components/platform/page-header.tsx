import Link from 'next/link';
import { Fragment } from 'react';

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';

export type PageCrumb = {
  href?: string;
  label: string;
};

export function PageHeader({
  actions,
  breadcrumbs,
  description,
  eyebrow,
  title,
}: Readonly<{
  actions?: React.ReactNode;
  breadcrumbs?: PageCrumb[];
  description?: React.ReactNode;
  eyebrow?: string;
  title: React.ReactNode;
}>) {
  return (
    <header className="academic-page-header">
      {breadcrumbs?.length ? (
        <Breadcrumb className="sr-only">
          <BreadcrumbList>
            {breadcrumbs.map((crumb, index) => (
              <Fragment key={`${crumb.label}-${index}`}>
                {index ? <BreadcrumbSeparator /> : null}
                <BreadcrumbItem>
                  {crumb.href ? (
                    <BreadcrumbLink asChild>
                      <Link href={crumb.href}>{crumb.label}</Link>
                    </BreadcrumbLink>
                  ) : (
                    <BreadcrumbPage>{crumb.label}</BreadcrumbPage>
                  )}
                </BreadcrumbItem>
              </Fragment>
            ))}
          </BreadcrumbList>
        </Breadcrumb>
      ) : null}
      <div className="academic-page-header__body">
        <div className="min-w-0">
          {eyebrow ? <p className="academic-kicker">{eyebrow}</p> : null}
          <h1 className="academic-title mt-1">{title}</h1>
          {description ? (
            <div className="academic-description mt-1.5">{description}</div>
          ) : null}
        </div>
        {actions ? (
          <div className="academic-page-header__actions">{actions}</div>
        ) : null}
      </div>
    </header>
  );
}
