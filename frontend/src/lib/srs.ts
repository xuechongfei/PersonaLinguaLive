import type { VocabRecord } from './storage';

/**
 * Quality levels for a self-graded review.
 *   1 — Again (forgot)
 *   2 — Hard
 *   3 — Good
 *   4 — Easy
 */
export type ReviewQuality = 1 | 2 | 3 | 4;

const DAY_MS = 24 * 60 * 60 * 1000;

const MIN_EASE = 1.3;
const MAX_EASE = 3.0;

export interface NextSchedule {
  ease: number;
  intervalDays: number;
  dueAt: number;
  reps: number;
}

/**
 * SM2-lite scheduler.
 * Quality 1 resets the card to a fresh 0-day interval.
 * Quality 2/3/4 multiply the previous interval by an ease factor that
 * itself drifts up on Easy and down on Hard.
 */
export function nextSchedule(
  entry: Pick<VocabRecord, 'ease' | 'intervalDays' | 'reps'>,
  quality: ReviewQuality,
  now: number = Date.now(),
): NextSchedule {
  let ease = entry.ease || 2.5;
  let intervalDays = entry.intervalDays || 0;
  let reps = entry.reps || 0;

  if (quality === 1) {
    reps = 0;
    intervalDays = 0;
    ease = Math.max(MIN_EASE, ease - 0.2);
  } else {
    reps += 1;
    if (reps === 1) {
      intervalDays = 1;
    } else if (reps === 2) {
      intervalDays = 3;
    } else {
      intervalDays = Math.max(1, Math.round(intervalDays * ease));
    }
    if (quality === 2) ease = Math.max(MIN_EASE, ease - 0.15);
    else if (quality === 4) ease = Math.min(MAX_EASE, ease + 0.15);
    // quality === 3 keeps ease unchanged
  }

  return {
    ease,
    intervalDays,
    dueAt: now + intervalDays * DAY_MS,
    reps,
  };
}
