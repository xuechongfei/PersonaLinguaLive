import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PersonaMouth from './PersonaMouth';

describe('PersonaMouth', () => {
  it('renders face SVG when silent', () => {
    render(<PersonaMouth isSpeaking={false} />);
    const svg = screen.getByRole('img', { name: /silent/i });
    expect(svg).toBeInTheDocument();
  });

  it('renders face SVG when speaking', () => {
    render(<PersonaMouth isSpeaking={true} />);
    const svg = screen.getByRole('img', { name: /speaking/i });
    expect(svg).toBeInTheDocument();
  });

  it('contains face circle, eyes, and mouth', () => {
    const { container } = render(<PersonaMouth isSpeaking={false} />);
    expect(container.querySelector('circle')).toBeInTheDocument(); // face
    expect(container.querySelectorAll('circle').length).toBe(3); // face + 2 eyes
    expect(container.querySelector('ellipse')).toBeInTheDocument(); // mouth
  });
});
