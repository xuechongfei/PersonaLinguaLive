import { create } from 'zustand';
import type { ImageReadyInfo } from '../components/ImageCanvas';
import type { UserLevel } from '../components/LevelSelector';
import type { SummaryData } from '../components/SummaryCard';
import type { VisionAnalyzeResponse, Entity } from './api';
import type { ChatClient } from './chat';
import type { ConversationData } from './storage';
import type { WorldSprite } from './world';

export type StudioStatus =
  | { kind: 'idle' }
  | { kind: 'analyzing' }
  | { kind: 'ready'; result: VisionAnalyzeResponse }
  | { kind: 'error'; message: string }
  | { kind: 'persona_loading'; object: Entity }
  | { kind: 'chatting'; personaName: string; sessionId: string }
  | { kind: 'summary'; data: SummaryData; personaName: string };

interface StudioState {
  file: File | null;
  imageSize: ImageReadyInfo | null;
  status: StudioStatus;
  analysisResult: VisionAnalyzeResponse | null;
  selectedObject: Entity | null;
  chatClient: ChatClient | null;
  sessionId: string;
  conversation: ConversationData | null;
  level: UserLevel;
  analyserNode: AnalyserNode | undefined;
  isSpeaking: boolean;
  worldBackground: string | null;
  worldSprites: WorldSprite[];
  worldReady: boolean;

  setFile: (f: File | null) => void;
  setImageSize: (s: ImageReadyInfo | null) => void;
  setStatus: (s: StudioStatus) => void;
  setAnalysisResult: (r: VisionAnalyzeResponse | null) => void;
  setSelectedObject: (o: Entity | null) => void;
  setChatClient: (c: ChatClient | null) => void;
  setSessionId: (id: string) => void;
  setConversation: (c: ConversationData | null) => void;
  setLevel: (l: UserLevel) => void;
  setAnalyserNode: (n: AnalyserNode | undefined) => void;
  setIsSpeaking: (v: boolean) => void;
  setWorldBackground: (b: string | null) => void;
  addWorldSprite: (s: WorldSprite) => void;
  setWorldReady: (v: boolean) => void;
  reset: () => void;
}

export const useStudioStore = create<StudioState>((set) => ({
  file: null,
  imageSize: null,
  status: { kind: 'idle' },
  analysisResult: null,
  selectedObject: null,
  chatClient: null,
  sessionId: '',
  conversation: null,
  level: 'beginner',
  analyserNode: undefined,
  isSpeaking: false,
  worldBackground: null,
  worldSprites: [],
  worldReady: false,

  setFile: (f) => set({ file: f }),
  setImageSize: (s) => set({ imageSize: s }),
  setStatus: (s) => set({ status: s }),
  setAnalysisResult: (r) => set({ analysisResult: r }),
  setSelectedObject: (o) => set({ selectedObject: o }),
  setChatClient: (c) => set({ chatClient: c }),
  setSessionId: (id) => set({ sessionId: id }),
  setConversation: (c) => set({ conversation: c }),
  setLevel: (l) => set({ level: l }),
  setAnalyserNode: (n) => set({ analyserNode: n }),
  setIsSpeaking: (v) => set({ isSpeaking: v }),
  setWorldBackground: (b) => set({ worldBackground: b }),
  addWorldSprite: (s) => set((st) => ({ worldSprites: [...st.worldSprites, s] })),
  setWorldReady: (v) => set({ worldReady: v }),

  reset: () => {
    const state = useStudioStore.getState();
    state.chatClient?.disconnect();
    set({
      file: null,
      imageSize: null,
      status: { kind: 'idle' },
      analysisResult: null,
      selectedObject: null,
      chatClient: null,
      sessionId: '',
      conversation: null,
      level: 'beginner',
      analyserNode: undefined,
      isSpeaking: false,
      worldBackground: null,
      worldSprites: [],
      worldReady: false,
    });
  },
}));
