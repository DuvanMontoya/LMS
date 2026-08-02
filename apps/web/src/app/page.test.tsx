import { vi } from 'vitest';

const { redirect } = vi.hoisted(() => ({ redirect: vi.fn() }));

vi.mock('next/navigation', () => ({
  redirect,
}));

import Home from './page';

describe('Home', () => {
  it('redirects the private platform root to login', () => {
    Home();
    expect(redirect).toHaveBeenCalledWith('/auth/iniciar-sesion');
  });
});
