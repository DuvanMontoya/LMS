import { render, screen } from '@testing-library/react';

import Home from './page';

describe('Home', () => {
  it('renders the accessible scaffolding heading', () => {
    render(<Home />);

    expect(
      screen.getByRole('heading', { name: 'Plataforma académica' }),
    ).toBeInTheDocument();
  });
});
