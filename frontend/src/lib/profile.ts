import type { UserLevel } from '../components/LevelSelector';
import { getPreference, savePreference } from './storage';

export interface LearnerProfile {
  level: UserLevel;
  createdAt: number;
  updatedAt: number;
}

const PREF_KEY = 'profile';
const DEFAULT_LEVEL: UserLevel = 'beginner';

export function defaultProfile(now: number = Date.now()): LearnerProfile {
  return { level: DEFAULT_LEVEL, createdAt: now, updatedAt: now };
}

export async function loadProfile(): Promise<LearnerProfile> {
  const stored = (await getPreference(PREF_KEY)) as Partial<LearnerProfile> | undefined;
  if (stored && (stored.level === 'beginner' || stored.level === 'intermediate' || stored.level === 'advanced')) {
    return {
      level: stored.level,
      createdAt: stored.createdAt ?? Date.now(),
      updatedAt: stored.updatedAt ?? Date.now(),
    };
  }
  return defaultProfile();
}

export async function saveProfile(profile: LearnerProfile): Promise<void> {
  await savePreference(PREF_KEY, profile);
}

export async function setLevel(level: UserLevel): Promise<LearnerProfile> {
  const current = await loadProfile();
  const updated: LearnerProfile = { ...current, level, updatedAt: Date.now() };
  await saveProfile(updated);
  return updated;
}
