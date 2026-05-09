import { render, screen } from '@testing-library/react';
import App from '../App';

describe('App', () => {
  it('renders the product name', () => {
    render(<App />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('PersonaLinguaLive');
  });

  it('renders the tagline', () => {
    render(<App />);
    expect(
      screen.getByText(/Anything you see can teach you English/i)
    ).toBeInTheDocument();
  });
});
