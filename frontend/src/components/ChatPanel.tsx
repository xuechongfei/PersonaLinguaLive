import { useState, useRef, useEffect, useCallback } from 'react';
import { ChatClient, type ChatEvent } from '../lib/chat';
import { useStudioStore } from '../lib/store';
import PersonaMouth from './PersonaMouth';
import LearningTip from './LearningTip';
import MicButton from './MicButton';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  learning?: string;
  followup?: string;
}

interface Props {
  client: ChatClient;
  personaName: string;
  onEndChat?: () => void;
  onTurnComplete?: (turn: {
    userMessage: string;
    assistantResponse: { speak: string; learning: string; followup: string };
    timestamp: number;
  }) => void;
}

export default function ChatPanel({ client, personaName, onEndChat, onTurnComplete }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const isSpeaking = useStudioStore((s) => s.isSpeaking);
  const [showTip, setShowTip] = useState<{ learning: string; followup: string } | null>(null);
  const [streamingText, setStreamingText] = useState('');
  const analyserNode = useStudioStore((s) => s.analyserNode);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamContentRef = useRef('');
  const lastUserMessageRef = useRef('');
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const onTurnCompleteRef = useRef(onTurnComplete);
  onTurnCompleteRef.current = onTurnComplete;

  const ensureAnalyser = useCallback((): { ctx: AudioContext; analyser: AnalyserNode } | null => {
    try {
      const Ctor = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!Ctor) return null;
      if (!audioContextRef.current) audioContextRef.current = new Ctor();
      if (!analyserRef.current) {
        const analyser = audioContextRef.current.createAnalyser();
        analyser.fftSize = 256;
        analyserRef.current = analyser;
        useStudioStore.getState().setAnalyserNode(analyser);
      }
      return { ctx: audioContextRef.current, analyser: analyserRef.current };
    } catch { return null; }
  }, []);

  useEffect(() => {
    return () => { audioContextRef.current?.close().catch(() => {}); audioContextRef.current = null; analyserRef.current = null; };
  }, []);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  useEffect(() => {
    const handleChunk = (event: ChatEvent) => {
      if (event.content) { streamContentRef.current += event.content; setStreamingText(streamContentRef.current); }
    };
    const handleResult = (event: ChatEvent) => {
      const segments = event.segments || { speak: '', learning: '', followup: '' };
      setMessages((prev) => [...prev, {
        role: 'assistant', content: segments.speak || streamContentRef.current,
        learning: segments.learning, followup: segments.followup,
      }]);
      onTurnCompleteRef.current?.({
        userMessage: lastUserMessageRef.current,
        assistantResponse: { speak: segments.speak, learning: segments.learning, followup: segments.followup },
        timestamp: Date.now(),
      });
      streamContentRef.current = ''; setStreamingText(''); setIsStreaming(false);
      if (segments.learning || segments.followup) setShowTip({ learning: segments.learning, followup: segments.followup });
    };
    const handleAudio = (event: ChatEvent) => {
      const audioBase64 = event.audio_base64;
      if (!audioBase64) return;
      useStudioStore.getState().setIsSpeaking(true);
      const audio = new Audio(`data:audio/wav;base64,${audioBase64}`);
      audio.crossOrigin = 'anonymous';
      audio.onended = () => useStudioStore.getState().setIsSpeaking(false);
      const wiring = ensureAnalyser();
      if (wiring) {
        try {
          const source = wiring.ctx.createMediaElementSource(audio);
          source.connect(wiring.analyser); wiring.analyser.connect(wiring.ctx.destination);
          if (wiring.ctx.state === 'suspended') wiring.ctx.resume().catch(() => {});
        } catch { /* fallback */ }
      }
      audio.play().catch(() => useStudioStore.getState().setIsSpeaking(false));
    };
    const handleError = () => { setIsStreaming(false); setStreamingText(''); streamContentRef.current = ''; };

    client.on('text_chunk', handleChunk);
    client.on('audio', handleAudio);
    client.on('result', handleResult);
    client.on('error', handleError);
    return () => {
      client.off('text_chunk', handleChunk); client.off('audio', handleAudio);
      client.off('result', handleResult); client.off('error', handleError);
    };
  }, [client, ensureAnalyser]);

  const sendMessage = useCallback((text: string) => {
    if (!text.trim() || isStreaming) return;
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    lastUserMessageRef.current = text;
    streamContentRef.current = ''; setStreamingText(''); setIsStreaming(true); setShowTip(null);
    client.sendMessage(text); setInput('');
  }, [client, isStreaming]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input); }
  };

  const handleTranscript = useCallback((text: string) => { setInput((prev) => prev + text); }, []);

  return (
    <aside
      role="dialog"
      aria-label="Chat panel"
      className="fixed right-4 top-4 z-30 flex h-[calc(100vh-2rem)] w-96 flex-col
                 rounded-3xl border border-sand/80 bg-white shadow-card animate-pop-in"
    >
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3.5 border-b border-sand/60">
        <div className="flex items-center gap-3">
          <PersonaMouth isSpeaking={isSpeaking} analyserNode={analyserNode} />
          <div>
            <h2 className="font-semibold text-sm text-ink">{personaName}</h2>
            <p className={`text-xs font-medium transition-colors ${isSpeaking ? 'text-honey' : isStreaming ? 'text-teal' : 'text-ink-light'}`}>
              {isStreaming ? 'typing...' : isSpeaking ? 'speaking...' : 'listening'}
            </p>
          </div>
        </div>
        {onEndChat && (
          <button type="button" onClick={onEndChat} className="btn-ghost text-xs">
            End
          </button>
        )}
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="mt-8 text-center">
            <span className="text-3xl">{'\u{1F4AC}'}</span>
            <p className="mt-3 text-sm text-ink-light">
              Start a conversation with <strong className="text-honey-dark">{personaName}</strong>!
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-pop-in`}>
            <div className={`max-w-[82%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed
              ${msg.role === 'user'
                ? 'bg-honey text-white rounded-br-md'
                : 'bg-sand/50 text-ink rounded-bl-md'}`}>
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {isStreaming && streamingText && (
          <div className="flex justify-start">
            <div className="max-w-[82%] rounded-2xl rounded-bl-md bg-sand/50 px-4 py-2.5 text-sm text-ink">
              <p className="whitespace-pre-wrap">
                {streamingText}
                <span className="inline-block w-1.5 h-4 ml-0.5 bg-honey animate-pulse-soft align-middle rounded-sm" />
              </p>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Learning Tip */}
      {showTip && (
        <div className="border-t border-sand/60 px-4 py-3 animate-slide-up">
          <LearningTip learning={showTip.learning} followup={showTip.followup} />
        </div>
      )}

      {/* Input */}
      <div className="flex items-center gap-2 border-t border-sand/60 px-4 py-3">
        <MicButton onTranscript={handleTranscript} disabled={isStreaming} />
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          disabled={isStreaming}
          className="flex-1 rounded-xl border-2 border-sand bg-sand/30 px-3.5 py-2.5 text-sm
                     outline-none transition-colors placeholder:text-ink-light/50
                     focus:border-honey focus:bg-white disabled:opacity-50"
        />
        <button
          type="button"
          onClick={() => sendMessage(input)}
          disabled={!input.trim() || isStreaming}
          className="rounded-xl bg-honey px-4 py-2.5 text-sm font-semibold text-white
                     hover:bg-honey-dark transition-all duration-200
                     disabled:opacity-50 active:scale-95"
        >
          Send
        </button>
      </div>
    </aside>
  );
}
