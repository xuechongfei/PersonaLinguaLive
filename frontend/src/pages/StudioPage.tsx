import { useState, useRef, useEffect } from 'react';
import UploadZone from '../components/UploadZone';
import ImageCanvas, { type ImageReadyInfo } from '../components/ImageCanvas';
import HotspotOverlay from '../components/HotspotOverlay';
import ChatPanel from '../components/ChatPanel';
import SummaryCard from '../components/SummaryCard';
import type { SummaryData } from '../components/SummaryCard';
import LevelSelector, { type UserLevel } from '../components/LevelSelector';
import { analyzeImage, generatePersona, fetchSummary, ApiError } from '../lib/api';
import type { VisionAnalyzeResponse, DetectedObject } from '../lib/api';
import { ChatClient } from '../lib/chat';
import { compressIfNeeded } from '../lib/image/compress';
import { loadProfile, setLevel as persistLevel } from '../lib/profile';
import { collectLearnerContext } from '../lib/learnerContext';
import {
  saveConversation,
  saveImage,
  type ConversationData,
} from '../lib/storage';

type Status =
  | { kind: 'idle' }
  | { kind: 'analyzing' }
  | { kind: 'ready'; result: VisionAnalyzeResponse }
  | { kind: 'error'; message: string }
  | { kind: 'persona_loading'; object: DetectedObject }
  | { kind: 'chatting'; personaName: string; sessionId: string }
  | { kind: 'summary'; data: SummaryData; personaName: string };

export default function StudioPage() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<Status>({ kind: 'idle' });
  const [size, setSize] = useState<ImageReadyInfo | null>(null);
  const [level, setLevelState] = useState<UserLevel>('beginner');
  const chatClientRef = useRef<ChatClient | null>(null);
  const sessionIdRef = useRef('');
  const conversationRef = useRef<ConversationData | null>(null);

  useEffect(() => {
    loadProfile().then((p) => setLevelState(p.level)).catch(() => {});
  }, []);

  async function handleLevelChange(next: UserLevel) {
    setLevelState(next);
    try {
      await persistLevel(next);
    } catch {
      /* non-fatal: keep UI state */
    }
  }

  function handleTurnComplete(turn: {
    userMessage: string;
    assistantResponse: { speak: string; learning: string; followup: string };
    timestamp: number;
  }) {
    const conv = conversationRef.current;
    if (!conv) return;
    conv.turns.push(turn);
    conv.updatedAt = Date.now();
    saveConversation(conv.sessionId, conv).catch(() => {
      /* non-fatal: in-memory state preserved */
    });
  }

  async function handleFile(raw: File) {
    setStatus({ kind: 'analyzing' });
    try {
      const slim = await compressIfNeeded(raw);
      setFile(slim);
      const result = await analyzeImage(slim);
      setStatus({ kind: 'ready', result });
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : '出了点问题,请重试。';
      setStatus({ kind: 'error', message: msg });
    }
  }

  async function handleSelectObject(obj: DetectedObject) {
    setStatus({ kind: 'persona_loading', object: obj });

    try {
      const sceneSummary = status.kind === 'ready' ? status.result.scene_summary : '';
      const persona = await generatePersona({
        label: obj.label,
        scene_summary: sceneSummary,
        persona_seed: obj.persona_seed ?? undefined,
        user_level: level,
      });

      const sessionId = `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
      sessionIdRef.current = sessionId;

      const now = Date.now();
      conversationRef.current = {
        sessionId,
        personaId: persona.persona_id,
        personaName: persona.persona_name,
        turns: [],
        createdAt: now,
        updatedAt: now,
      };

      if (file) {
        saveImage(sessionId, file).catch(() => {
          /* non-fatal: history thumbnails may miss this entry */
        });
      }

      const client = new ChatClient();
      chatClientRef.current = client;

      let learnerContext = null;
      try {
        learnerContext = await collectLearnerContext(level);
      } catch {
        /* non-fatal: chat works without context */
      }

      client.connect(
        sessionId,
        {
          role: 'system',
          content: persona.system_prompt,
        },
        level,
        learnerContext,
      );

      setStatus({
        kind: 'chatting',
        personaName: persona.persona_name,
        sessionId,
      });
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : 'Failed to create persona.';
      setStatus({ kind: 'error', message: msg });
    }
  }

  async function handleEndChat() {
    chatClientRef.current?.disconnect();
    chatClientRef.current = null;

    // Remember persona name before state changes
    const personaName = status.kind === 'chatting' ? status.personaName : '';

    try {
      const summary = await fetchSummary({
        session_id: sessionIdRef.current,
        user_level: level,
      });

      const summaryData: SummaryData = {
        newWords: summary.new_words,
        grammarPoints: summary.grammar_points,
        fluencyScore: summary.fluency_score,
        strengths: summary.strengths,
        areasToImprove: summary.areas_to_improve,
      };

      const conv = conversationRef.current;
      if (conv) {
        conv.summary = {
          newWords: summary.new_words,
          grammarPoints: summary.grammar_points,
          fluencyScore: summary.fluency_score,
          strengths: summary.strengths,
          areasToImprove: summary.areas_to_improve,
        };
        conv.updatedAt = Date.now();
        saveConversation(conv.sessionId, conv).catch(() => {
          /* non-fatal */
        });
      }

      setStatus({
        kind: 'summary',
        data: summaryData,
        personaName,
      });
    } catch {
      // Fallback: go back to ready state
      setStatus({ kind: 'error', message: 'Failed to fetch summary.' });
    }
  }

  function handleCloseSummary() {
    setStatus({ kind: 'idle' });
    setFile(null);
    setSize(null);
  }

  function handleReset() {
    setFile(null);
    setStatus({ kind: 'idle' });
    setSize(null);
    chatClientRef.current?.disconnect();
    chatClientRef.current = null;
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900">
      <h1 className="text-2xl font-semibold text-center">Studio</h1>
      <p className="mt-1 mb-6 text-center text-sm text-slate-500">
        Upload a photo and chat with the objects inside!
      </p>

      {!file && (
        <>
          <div className="mx-auto mb-4 flex max-w-3xl items-center justify-between gap-3">
            <label className="text-sm font-medium text-slate-600">English level</label>
            <LevelSelector value={level} onChange={handleLevelChange} />
          </div>
          <UploadZone onFile={handleFile} />
        </>
      )}

      {file && status.kind !== 'chatting' && status.kind !== 'summary' && (
        <section className="mx-auto mt-4 w-full max-w-3xl">
          <div className="relative inline-block">
            <ImageCanvas file={file} alt="Selected image" onReady={setSize} />
            {status.kind === 'ready' && size && (
              <HotspotOverlay
                renderedWidth={size.renderedWidth}
                renderedHeight={size.renderedHeight}
                objects={status.result.objects}
                onSelect={handleSelectObject}
              />
            )}
          </div>

          <div className="mt-4 flex items-center gap-3">
            <button
              type="button"
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-white"
              onClick={handleReset}
            >
              Reset
            </button>
            {status.kind === 'analyzing' && (
              <span className="text-sm text-slate-500">Analyzing...</span>
            )}
            {status.kind === 'ready' && (
              <span className="text-sm text-slate-500">
                {status.result.objects.length} objects detected
              </span>
            )}
            {status.kind === 'persona_loading' && (
              <span className="text-sm text-slate-500">Creating persona...</span>
            )}
          </div>

          {status.kind === 'error' && (
            <p role="alert" className="mt-4 text-sm text-rose-600">
              {status.message}
            </p>
          )}
        </section>
      )}

      {status.kind === 'chatting' && (
        <ChatPanel
          client={chatClientRef.current!}
          personaName={status.personaName}
          onEndChat={handleEndChat}
          onTurnComplete={handleTurnComplete}
        />
      )}

      {status.kind === 'summary' && (
        <SummaryCard
          summary={status.data}
          personaName={status.personaName}
          onClose={handleCloseSummary}
        />
      )}
    </main>
  );
}
