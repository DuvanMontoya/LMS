import { render, screen } from '@testing-library/react';

import Home from './page';

describe('Home', () => {
  it('renders the institutional gateway heading', () => {
    render(<Home />);

    expect(
      screen.getByRole('heading', { name: 'Conocimiento con estructura.' }),
    ).toBeInTheDocument();
  });
});
