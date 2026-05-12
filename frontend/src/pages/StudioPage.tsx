import { useEffect } from 'react';
import UploadZone from '../components/UploadZone';
import ImageCanvas, { type ImageReadyInfo } from '../components/ImageCanvas';
import HotspotOverlay from '../components/HotspotOverlay';
import ChatPanel from '../components/ChatPanel';
import SummaryCard from '../components/SummaryCard';
import type { SummaryData } from '../components/SummaryCard';
import LevelSelector, { type UserLevel } from '../components/LevelSelector';
import SceneGallery from '../components/SceneGallery';
import SpeakingOverlay from '../components/SpeakingOverlay';
import { analyzeImage, generatePersona, fetchSummary, ApiError } from '../lib/api';
import type { DetectedObject } from '../lib/api';
import { ChatClient } from '../lib/chat';
import { compressIfNeeded } from '../lib/image/compress';
import { loadProfile, setLevel as persistLevel } from '../lib/profile';
import { collectLearnerContext } from '../lib/learnerContext';
import {
  saveConversation,
  saveImage,
  type ConversationData,
} from '../lib/storage';
import { useStudioStore } from '../lib/store';

export default function StudioPage() {
  const file = useStudioStore((s) => s.file);
  const status = useStudioStore((s) => s.status);
  const imageSize = useStudioStore((s) => s.imageSize);
  const level = useStudioStore((s) => s.level);
  const analysisResult = useStudioStore((s) => s.analysisResult);
  const selectedObject = useStudioStore((s) => s.selectedObject);
  const chatClient = useStudioStore((s) => s.chatClient);

  const store = useStudioStore;

  useEffect(() => {
    loadProfile().then((p) => store.getState().setLevel(p.level)).catch(() => {});
  }, []);

  async function handleLevelChange(next: UserLevel) {
    store.getState().setLevel(next);
    try {
      await persistLevel(next);
    } catch {
      /* non-fatal */
    }
  }

  function handleTurnComplete(turn: {
    userMessage: string;
    assistantResponse: { speak: string; learning: string; followup: string };
    timestamp: number;
  }) {
    const conv = store.getState().conversation;
    if (!conv) return;
    conv.turns.push(turn);
    conv.updatedAt = Date.now();
    saveConversation(conv.sessionId, conv).catch(() => {});
  }

  async function handleFile(raw: File) {
    store.getState().setStatus({ kind: 'analyzing' });
    try {
      const slim = await compressIfNeeded(raw);
      store.getState().setFile(slim);
      const result = await analyzeImage(slim);
      store.getState().setAnalysisResult(result);
      store.getState().setStatus({ kind: 'ready', result });
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : '出了点问题,请重试。';
      store.getState().setStatus({ kind: 'error', message: msg });
    }
  }

  async function handleSelectObject(obj: DetectedObject) {
    const currentStatus = store.getState().status;
    if (currentStatus.kind === 'persona_loading') return;

    // Disconnect existing chat if mid-chat switch
    store.getState().chatClient?.disconnect();
    store.getState().setChatClient(null);

    store.getState().setSelectedObject(obj);
    store.getState().setStatus({ kind: 'persona_loading', object: obj });

    try {
      const result = store.getState().analysisResult;
      const sceneSummary = result?.scene_summary ?? '';
      const persona = await generatePersona({
        label: obj.label,
        scene_summary: sceneSummary,
        persona_seed: obj.persona_seed ?? undefined,
        user_level: store.getState().level,
      });

      const sessionId = `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
      const now = Date.now();
      const conv: ConversationData = {
        sessionId,
        personaId: persona.persona_id,
        personaName: persona.persona_name,
        turns: [],
        createdAt: now,
        updatedAt: now,
      };

      const currentFile = store.getState().file;
      if (currentFile) {
        saveImage(sessionId, currentFile).catch(() => {});
      }

      const client = new ChatClient();

      let learnerContext = null;
      try {
        learnerContext = await collectLearnerContext(store.getState().level);
      } catch {
        /* non-fatal */
      }

      client.connect(
        sessionId,
        { role: 'system', content: persona.system_prompt },
        store.getState().level,
        learnerContext,
        persona.voice_id,
      );

      store.getState().setSessionId(sessionId);
      store.getState().setConversation(conv);
      store.getState().setChatClient(client);
      store.getState().setStatus({
        kind: 'chatting',
        personaName: persona.persona_name,
        sessionId,
      });
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : 'Failed to create persona.';
      store.getState().setStatus({ kind: 'error', message: msg });
    }
  }

  async function handleEndChat() {
    store.getState().chatClient?.disconnect();
    store.getState().setChatClient(null);

    const currentStatus = store.getState().status;
    const personaName = currentStatus.kind === 'chatting' ? currentStatus.personaName : '';

    try {
      const summary = await fetchSummary({
        session_id: store.getState().sessionId,
        user_level: store.getState().level,
      });

      const summaryData: SummaryData = {
        newWords: summary.new_words,
        grammarPoints: summary.grammar_points,
        fluencyScore: summary.fluency_score,
        strengths: summary.strengths,
        areasToImprove: summary.areas_to_improve,
      };

      const conv = store.getState().conversation;
      if (conv) {
        conv.summary = {
          newWords: summary.new_words,
          grammarPoints: summary.grammar_points,
          fluencyScore: summary.fluency_score,
          strengths: summary.strengths,
          areasToImprove: summary.areas_to_improve,
        };
        conv.updatedAt = Date.now();
        saveConversation(conv.sessionId, conv).catch(() => {});
      }

      store.getState().setStatus({
        kind: 'summary',
        data: summaryData,
        personaName,
      });
    } catch {
      store.getState().setStatus({ kind: 'error', message: 'Failed to fetch summary.' });
    }
  }

  function handleCloseSummary() {
    store.getState().setStatus({ kind: 'idle' });
    store.getState().setFile(null);
    store.getState().setImageSize(null);
  }

  function handleReset() {
    store.getState().reset();
  }

  function handleImageReady(size: ImageReadyInfo) {
    store.getState().setImageSize(size);
  }

  const showAnalysisBar =
    status.kind === 'analyzing' ||
    status.kind === 'ready' ||
    status.kind === 'error' ||
    status.kind === 'persona_loading';

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
          <div className="mx-auto max-w-3xl">
            <SceneGallery onSelectScene={handleFile} />
          </div>
        </>
      )}

      {file && (
        <section className="mx-auto w-full max-w-3xl">
          <div className="relative inline-block">
            <ImageCanvas file={file} alt="Selected image" onReady={handleImageReady} />

            {(status.kind === 'ready' || status.kind === 'chatting') && imageSize && analysisResult && (
              <HotspotOverlay
                renderedWidth={imageSize.renderedWidth}
                renderedHeight={imageSize.renderedHeight}
                objects={analysisResult.objects}
                onSelect={handleSelectObject}
              />
            )}

            {status.kind === 'chatting' && imageSize && selectedObject && (
              <SpeakingOverlay
                renderedWidth={imageSize.renderedWidth}
                renderedHeight={imageSize.renderedHeight}
              />
            )}
          </div>

          {showAnalysisBar && (
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
              {status.kind === 'ready' && analysisResult && (
                <span className="text-sm text-slate-500">
                  {analysisResult.objects.length} objects detected
                </span>
              )}
              {status.kind === 'persona_loading' && (
                <span className="text-sm text-slate-500">Creating persona...</span>
              )}
            </div>
          )}

          {status.kind === 'error' && (
            <p role="alert" className="mt-4 text-sm text-rose-600">
              {status.message}
            </p>
          )}
        </section>
      )}

      {status.kind === 'chatting' && chatClient && (
        <ChatPanel
          client={chatClient}
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
