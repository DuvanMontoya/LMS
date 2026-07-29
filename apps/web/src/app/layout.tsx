import type { Metadata } from 'next';

import { QueryProvider } from '@/lib/query/provider';
import './globals.css';

export const metadata: Metadata = {
  title: {
    default: 'Plataforma académica',
    template: '%s | Plataforma académica',
  },
  description: 'Espacio de acceso de la plataforma académica.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
