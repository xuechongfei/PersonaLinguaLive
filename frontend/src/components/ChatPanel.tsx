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
      if (!audioContextRef.current) {
        audioContextRef.current = new Ctor();
      }
      if (!analyserRef.current) {
        const analyser = audioContextRef.current.createAnalyser();
        analyser.fftSize = 256;
        analyserRef.current = analyser;
        useStudioStore.getState().setAnalyserNode(analyser);
      }
      return { ctx: audioContextRef.current, analyser: analyserRef.current };
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    return () => {
      audioContextRef.current?.close().catch(() => {});
      audioContextRef.current = null;
      analyserRef.current = null;
    };
  }, []);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    const handleChunk = (event: ChatEvent) => {
      if (event.content) {
        streamContentRef.current += event.content;
        setStreamingText(streamContentRef.current);
      }
    };

    const handleResult = (event: ChatEvent) => {
      const segments = event.segments || { speak: '', learning: '', followup: '' };

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: segments.speak || streamContentRef.current,
          learning: segments.learning,
          followup: segments.followup,
        },
      ]);

      onTurnCompleteRef.current?.({
        userMessage: lastUserMessageRef.current,
        assistantResponse: {
          speak: segments.speak,
          learning: segments.learning,
          followup: segments.followup,
        },
        timestamp: Date.now(),
      });

      streamContentRef.current = '';
      setStreamingText('');
      setIsStreaming(false);

      if (segments.learning || segments.followup) {
        setShowTip({ learning: segments.learning, followup: segments.followup });
      }
    };

    const handleAudio = (event: ChatEvent) => {
      const audioBase64 = event.audio_base64;
      if (!audioBase64) return;
      useStudioStore.getState().setIsSpeaking(true);
      const audio = new Audio(`data:audio/wav;base64,${audioBase64}`);
      audio.crossOrigin = 'anonymous';
      audio.onended = () => useStudioStore.getState().setIsSpeaking(false);

      // Wire the element through Web Audio so PersonaMouth can lip-sync.
      // Falls back to plain playback if Web Audio is unavailable.
      const wiring = ensureAnalyser();
      if (wiring) {
        try {
          const source = wiring.ctx.createMediaElementSource(audio);
          source.connect(wiring.analyser);
          wiring.analyser.connect(wiring.ctx.destination);
          if (wiring.ctx.state === 'suspended') {
            wiring.ctx.resume().catch(() => {});
          }
        } catch {
          /* fall back to direct playback */
        }
      }

      audio.play().catch(() => useStudioStore.getState().setIsSpeaking(false));
    };

    const handleError = () => {
      setIsStreaming(false);
      setStreamingText('');
      streamContentRef.current = '';
    };

    client.on('text_chunk', handleChunk);
    client.on('audio', handleAudio);
    client.on('result', handleResult);
    client.on('error', handleError);

    return () => {
      client.off('text_chunk', handleChunk);
      client.off('audio', handleAudio);
      client.off('result', handleResult);
      client.off('error', handleError);
    };
  }, [client, ensureAnalyser]);

  const sendMessage = useCallback(
    (text: string) => {
      if (!text.trim() || isStreaming) return;
      setMessages((prev) => [...prev, { role: 'user', content: text }]);
      lastUserMessageRef.current = text;
      streamContentRef.current = '';
      setStreamingText('');
      setIsStreaming(true);
      setShowTip(null);
      client.sendMessage(text);
      setInput('');
    },
    [client, isStreaming],
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const handleTranscript = useCallback((text: string) => {
    setInput((prev) => prev + text);
  }, []);

  return (
    <aside
      role="dialog"
      aria-label="Chat panel"
      className="fixed right-4 top-4 z-30 flex h-[calc(100vh-2rem)] w-96 flex-col rounded-2xl border border-slate-200 bg-white shadow-xl"
    >
      {/* Header */}
      <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <div className="flex items-center gap-3">
          <PersonaMouth isSpeaking={isSpeaking} analyserNode={analyserNode} />
          <div>
            <h2 className="font-semibold text-slate-900">{personaName}</h2>
            <p className="text-xs text-slate-500">
              {isStreaming ? 'typing...' : isSpeaking ? 'speaking...' : 'listening'}
            </p>
          </div>
        </div>
        {onEndChat && (
          <button
            type="button"
            onClick={onEndChat}
            className="rounded-md px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
          >
            End Chat
          </button>
        )}
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <p className="mt-8 text-center text-sm text-slate-400">
            Start a conversation with {personaName}!
          </p>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm ${
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-100 text-slate-800'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {isStreaming && streamingText && (
          <div className="flex justify-start">
            <div className="max-w-[80%] rounded-2xl bg-slate-100 px-4 py-2 text-sm text-slate-800">
              <p className="whitespace-pre-wrap">{streamingText}</p>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Learning Tip */}
      {showTip && (
        <div className="border-t border-slate-200 px-4 py-3">
          <LearningTip learning={showTip.learning} followup={showTip.followup} />
        </div>
      )}

      {/* Input */}
      <div className="flex items-center gap-2 border-t border-slate-200 px-4 py-3">
        <MicButton onTranscript={handleTranscript} disabled={isStreaming} />
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          disabled={isStreaming}
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 disabled:opacity-50"
        />
        <button
          type="button"
          onClick={() => sendMessage(input)}
          disabled={!input.trim() || isStreaming}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </aside>
  );
}
