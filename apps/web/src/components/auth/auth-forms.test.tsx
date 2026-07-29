import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

import { LoginForm } from './auth-forms';

describe('LoginForm', () => {
  it('exposes labelled fields and password-manager autocomplete', () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <LoginForm />
      </QueryClientProvider>,
    );
    expect(screen.getByLabelText('Correo electrónico')).toHaveAttribute(
      'autocomplete',
      'email',
    );
    expect(screen.getByLabelText('Contraseña')).toHaveAttribute(
      'autocomplete',
      'current-password',
    );
    expect(
      screen.getByRole('button', { name: 'Iniciar sesión' }),
    ).toBeEnabled();
  });
});
