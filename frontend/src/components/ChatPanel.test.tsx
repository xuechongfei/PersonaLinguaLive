import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatClient } from '../lib/chat';

vi.mock('../lib/chat', () => ({
  ChatClient: vi.fn(),
}));

vi.mock('./PersonaMouth', () => ({ default: () => null }));
vi.mock('./LearningTip', () => ({ default: () => null }));
vi.mock('./MicButton', () => ({ default: () => null }));

describe('ChatPanel', () => {
  let mockClient: any;

  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn();
    mockClient = {
      on: vi.fn(), off: vi.fn(), connect: vi.fn(),
      sendMessage: vi.fn(), disconnect: vi.fn(), isConnected: false,
    };
    (ChatClient as any).mockImplementation(() => mockClient);
  });

  it('renders persona name in header', async () => {
    const { default: ChatPanel } = await import('./ChatPanel');
    render(<ChatPanel client={mockClient} personaName="Tilly" />);
    const tillyHeaders = screen.getAllByText('Tilly');
    expect(tillyHeaders.length).toBeGreaterThanOrEqual(1);
  });

  it('renders welcome message', async () => {
    const { default: ChatPanel } = await import('./ChatPanel');
    render(<ChatPanel client={mockClient} personaName="Tilly" />);
    expect(screen.getByText(/Start a conversation/)).toBeInTheDocument();
  });

  it('has input field and send button', async () => {
    const { default: ChatPanel } = await import('./ChatPanel');
    render(<ChatPanel client={mockClient} personaName="Tilly" />);
    expect(screen.getByPlaceholderText('Type a message...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
  });

  it('disables send button with empty input', async () => {
    const { default: ChatPanel } = await import('./ChatPanel');
    render(<ChatPanel client={mockClient} personaName="Tilly" />);
    const sendBtn = screen.getByRole('button', { name: /send/i });
    expect(sendBtn).toBeDisabled();
  });

  it('sends message on button click', async () => {
    const { default: ChatPanel } = await import('./ChatPanel');
    render(<ChatPanel client={mockClient} personaName="Tilly" />);
    const input = screen.getByPlaceholderText('Type a message...');
    fireEvent.change(input, { target: { value: 'Hello!' } });
    const sendBtn = screen.getByRole('button', { name: /send/i });
    expect(sendBtn).not.toBeDisabled();
    fireEvent.click(sendBtn);
    expect(mockClient.sendMessage).toHaveBeenCalledWith('Hello!');
  });

  it('sends message on Enter key', async () => {
    const { default: ChatPanel } = await import('./ChatPanel');
    render(<ChatPanel client={mockClient} personaName="Tilly" />);
    const input = screen.getByPlaceholderText('Type a message...');
    fireEvent.change(input, { target: { value: 'Hi!' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(mockClient.sendMessage).toHaveBeenCalledWith('Hi!');
  });

  it('has end chat button that calls onEndChat', async () => {
    const onEndChat = vi.fn();
    const { default: ChatPanel } = await import('./ChatPanel');
    render(<ChatPanel client={mockClient} personaName="Tilly" onEndChat={onEndChat} />);
    const endBtn = screen.getByRole('button', { name: 'End' });
    fireEvent.click(endBtn);
    expect(onEndChat).toHaveBeenCalled();
  });
});
