import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';

vi.mock('@/lib/auth/registration', () => ({
  isSignupAvailable: vi.fn().mockResolvedValue(true),
}));

import Home from './page';

describe('Home', () => {
  it('renders the institutional gateway heading', async () => {
    render(await Home());

    expect(
      screen.getByRole('heading', { name: 'Conocimiento con estructura.' }),
    ).toBeInTheDocument();
  });
});
