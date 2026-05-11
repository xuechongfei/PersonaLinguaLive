import { describe, it, expect, beforeEach } from 'vitest';
import { useStudioStore } from './store';

describe('useStudioStore', () => {
  beforeEach(() => {
    useStudioStore.getState().reset();
  });

  it('has correct initial state', () => {
    const s = useStudioStore.getState();
    expect(s.file).toBeNull();
    expect(s.imageSize).toBeNull();
    expect(s.status).toEqual({ kind: 'idle' });
    expect(s.analysisResult).toBeNull();
    expect(s.selectedObject).toBeNull();
    expect(s.chatClient).toBeNull();
    expect(s.sessionId).toBe('');
    expect(s.conversation).toBeNull();
    expect(s.level).toBe('beginner');
    expect(s.analyserNode).toBeUndefined();
    expect(s.isSpeaking).toBe(false);
  });

  it('setFile stores file', () => {
    const file = new File([], 'test.jpg');
    useStudioStore.getState().setFile(file);
    expect(useStudioStore.getState().file).toBe(file);
  });

  it('setImageSize stores dimensions', () => {
    const size = { naturalWidth: 800, naturalHeight: 600, renderedWidth: 400, renderedHeight: 300 };
    useStudioStore.getState().setImageSize(size);
    expect(useStudioStore.getState().imageSize).toEqual(size);
  });

  it('setStatus transitions through analysis pipeline', () => {
    const result = {
      request_id: '1',
      is_safe: true,
      reject_reasons: [],
      scene_summary: 'a kitchen',
      objects: [{ id: '1', label: 'cup', bbox: { x: 0.1, y: 0.1, w: 0.2, h: 0.2 }, confidence: 0.9 }],
    };
    useStudioStore.getState().setStatus({ kind: 'analyzing' });
    expect(useStudioStore.getState().status.kind).toBe('analyzing');

    useStudioStore.getState().setStatus({ kind: 'ready', result });
    expect(useStudioStore.getState().status.kind).toBe('ready');
  });

  it('setAnalysisResult stores result separately from status', () => {
    const result = {
      request_id: '2',
      is_safe: true,
      reject_reasons: [],
      scene_summary: 'a desk',
      objects: [{ id: '2', label: 'laptop', bbox: { x: 0.5, y: 0.5, w: 0.3, h: 0.3 }, confidence: 0.95 }],
    };
    useStudioStore.getState().setAnalysisResult(result);
    expect(useStudioStore.getState().analysisResult?.objects[0].label).toBe('laptop');
    // Status should still be idle
    expect(useStudioStore.getState().status).toEqual({ kind: 'idle' });
  });

  it('setSelectedObject stores object reference', () => {
    const obj = { id: '3', label: 'mug', bbox: { x: 0.2, y: 0.3, w: 0.4, h: 0.4 }, confidence: 0.8 };
    useStudioStore.getState().setSelectedObject(obj);
    expect(useStudioStore.getState().selectedObject?.id).toBe('3');
  });

  it('setLevel updates and persists', () => {
    useStudioStore.getState().setLevel('advanced');
    expect(useStudioStore.getState().level).toBe('advanced');

    useStudioStore.getState().setLevel('intermediate');
    expect(useStudioStore.getState().level).toBe('intermediate');
  });

  it('setAnalyserNode stores analyser reference', () => {
    const fakeNode = {} as AnalyserNode;
    useStudioStore.getState().setAnalyserNode(fakeNode);
    expect(useStudioStore.getState().analyserNode).toBe(fakeNode);
    useStudioStore.getState().setAnalyserNode(undefined);
    expect(useStudioStore.getState().analyserNode).toBeUndefined();
  });

  it('setIsSpeaking toggles speaking state', () => {
    expect(useStudioStore.getState().isSpeaking).toBe(false);
    useStudioStore.getState().setIsSpeaking(true);
    expect(useStudioStore.getState().isSpeaking).toBe(true);
    useStudioStore.getState().setIsSpeaking(false);
    expect(useStudioStore.getState().isSpeaking).toBe(false);
  });

  it('reset clears all state to initial', () => {
    useStudioStore.getState().setFile(new File([], 'x.jpg'));
    useStudioStore.getState().setLevel('advanced');
    useStudioStore.getState().setIsSpeaking(true);
    useStudioStore.getState().setAnalysisResult({
      request_id: 'r',
      is_safe: true,
      reject_reasons: [],
      scene_summary: '',
      objects: [],
    });

    useStudioStore.getState().reset();

    const s = useStudioStore.getState();
    expect(s.file).toBeNull();
    expect(s.level).toBe('beginner');
    expect(s.isSpeaking).toBe(false);
    expect(s.analysisResult).toBeNull();
    expect(s.selectedObject).toBeNull();
    expect(s.chatClient).toBeNull();
    expect(s.conversation).toBeNull();
  });

  it('setChatClient and setSessionId work together', () => {
    const mockClient = { disconnect: () => {} } as any;
    useStudioStore.getState().setChatClient(mockClient);
    useStudioStore.getState().setSessionId('session_123');
    expect(useStudioStore.getState().chatClient).toBe(mockClient);
    expect(useStudioStore.getState().sessionId).toBe('session_123');
  });

  it('setConversation stores conversation data', () => {
    const conv = {
      sessionId: 's1',
      personaId: 'p1',
      personaName: 'Test',
      turns: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    useStudioStore.getState().setConversation(conv);
    expect(useStudioStore.getState().conversation?.personaName).toBe('Test');
  });
});
