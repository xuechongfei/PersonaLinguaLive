import { describe, it, expect, beforeEach, vi } from 'vitest';

const prefs = new Map<string, unknown>();

vi.mock('./storage', () => ({
  getPreference: vi.fn(async (key: string) => prefs.get(key)),
  savePreference: vi.fn(async (key: string, value: unknown) => {
    prefs.set(key, value);
  }),
}));

beforeEach(() => {
  prefs.clear();
  vi.clearAllMocks();
});

describe('profile', () => {
  it('loadProfile returns a beginner default when nothing stored', async () => {
    const { loadProfile } = await import('./profile');
    const profile = await loadProfile();
    expect(profile.level).toBe('beginner');
    expect(profile.createdAt).toBeGreaterThan(0);
  });

  it('saveProfile then loadProfile round-trips', async () => {
    const { loadProfile, saveProfile } = await import('./profile');
    await saveProfile({ level: 'advanced', createdAt: 1000, updatedAt: 2000 });
    const loaded = await loadProfile();
    expect(loaded).toEqual({ level: 'advanced', createdAt: 1000, updatedAt: 2000 });
  });

  it('setLevel updates only the level and bumps updatedAt', async () => {
    const { setLevel, loadProfile } = await import('./profile');
    await setLevel('intermediate');
    const after = await loadProfile();
    expect(after.level).toBe('intermediate');
    expect(after.updatedAt).toBeGreaterThanOrEqual(after.createdAt);
  });

  it('loadProfile falls back to default when stored level is invalid', async () => {
    const { loadProfile } = await import('./profile');
    prefs.set('profile', { level: 'guru', createdAt: 1, updatedAt: 1 });
    const profile = await loadProfile();
    expect(profile.level).toBe('beginner');
  });
});
