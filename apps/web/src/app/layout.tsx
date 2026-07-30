import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';

import { TooltipProvider } from '@/components/ui/tooltip';
import { QueryProvider } from '@/lib/query/provider';
import { cn } from '@/lib/utils';
import './globals.css';

const geist = Geist({ subsets: ['latin'], variable: '--font-geist-sans' });
const geistMono = Geist_Mono({
  subsets: ['latin'],
  variable: '--font-geist-mono',
});

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
    <html
      lang="es"
      className={cn('font-sans', geist.variable, geistMono.variable)}
      suppressHydrationWarning
    >
      <body className="min-h-svh bg-background text-foreground antialiased">
        <TooltipProvider delayDuration={300}>
          <QueryProvider>{children}</QueryProvider>
        </TooltipProvider>
      </body>
    </html>
  );
}
