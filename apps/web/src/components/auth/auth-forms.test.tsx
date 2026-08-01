import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

import {
  LoginForm,
  PasswordRequestForm,
  PasswordResetForm,
  SignUpForm,
} from './auth-forms';
import { ManagedAccountActivation } from './managed-account-activation';

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
    expect(
      screen.getByRole('button', { name: 'Iniciar sesión' }).closest('form'),
    ).toHaveAttribute('method', 'post');
  });

  it('does not advertise signup when registration is unavailable', () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <LoginForm registrationAvailable={false} />
      </QueryClientProvider>,
    );
    expect(
      screen.queryByRole('link', { name: 'Crear una cuenta' }),
    ).not.toBeInTheDocument();
  });

  it('never falls back to GET for identity forms with secrets or codes', () => {
    const forms = [
      LoginForm,
      SignUpForm,
      PasswordRequestForm,
      PasswordResetForm,
      ManagedAccountActivation,
    ];

    for (const Form of forms) {
      const { container, unmount } = render(
        <QueryClientProvider client={new QueryClient()}>
          <Form />
        </QueryClientProvider>,
      );
      expect(container.querySelector('form')).toHaveAttribute('method', 'post');
      unmount();
    }
  });
});
