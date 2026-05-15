import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import SceneGallery from './SceneGallery';

describe('SceneGallery', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('renders 6 scene buttons', () => {
    render(<SceneGallery onSelectScene={() => {}} />);
    expect(screen.getAllByRole('button').length).toBe(6);
  });

  it('displays scene names', () => {
    render(<SceneGallery onSelectScene={() => {}} />);
    expect(screen.getByText('Kitchen')).toBeInTheDocument();
    expect(screen.getByText('Study Desk')).toBeInTheDocument();
    expect(screen.getByText('Living Room')).toBeInTheDocument();
    expect(screen.getByText('Cafe')).toBeInTheDocument();
    expect(screen.getByText('Park')).toBeInTheDocument();
    expect(screen.getByText('Bedroom')).toBeInTheDocument();
  });

  it('disables button when scene is clicked', async () => {
    const mockFetch = vi.fn().mockImplementation(() => new Promise(() => {}));
    globalThis.fetch = mockFetch as any;
    render(<SceneGallery onSelectScene={() => {}} />);
    const kitchenBtn = screen.getByText('Kitchen').closest('button')!;
    fireEvent.click(kitchenBtn);
    expect(kitchenBtn).toBeDisabled();
    globalThis.fetch = undefined as any;
  });

  it('calls onSelectScene with a File on fetch success', async () => {
    const blob = new Blob(['fake-image-data'], { type: 'image/webp' });
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, blob: () => Promise.resolve(blob) }) as any;
    const onSelect = vi.fn();
    render(<SceneGallery onSelectScene={onSelect} />);
    fireEvent.click(screen.getByText('Cafe').closest('button')!);
    await waitFor(() => { expect(onSelect).toHaveBeenCalledTimes(1); });
    const file = onSelect.mock.calls[0][0] as File;
    expect(file).toBeInstanceOf(File);
    expect(file.name).toBe('cafe.webp');
    expect(file.type).toBe('image/webp');
    globalThis.fetch = undefined as any;
  });

  it('shows error when fetch fails', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 404 }) as any;
    render(<SceneGallery onSelectScene={() => {}} />);
    fireEvent.click(screen.getByText('Park').closest('button')!);
    await waitFor(() => { expect(screen.getByRole('alert')).toBeInTheDocument(); });
    globalThis.fetch = undefined as any;
  });

  it('shows error when fetch throws', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('Network error')) as any;
    render(<SceneGallery onSelectScene={() => {}} />);
    fireEvent.click(screen.getByText('Park').closest('button')!);
    await waitFor(() => { expect(screen.getByRole('alert')).toBeInTheDocument(); });
    globalThis.fetch = undefined as any;
  });
});
