import { describe, it, expect } from 'vitest';
import { nextSchedule } from './srs';

const base = { ease: 2.5, intervalDays: 0, reps: 0 };

describe('srs.nextSchedule', () => {
  it('first Good review schedules in 1 day', () => {
    const r = nextSchedule(base, 3, 0);
    expect(r.reps).toBe(1);
    expect(r.intervalDays).toBe(1);
    expect(r.dueAt).toBe(1 * 24 * 60 * 60 * 1000);
  });

  it('second Good review schedules in 3 days', () => {
    const r1 = nextSchedule(base, 3, 0);
    const r2 = nextSchedule(r1, 3, 0);
    expect(r2.reps).toBe(2);
    expect(r2.intervalDays).toBe(3);
  });

  it('subsequent Good reviews multiply by ease', () => {
    let r = nextSchedule(base, 3, 0);
    r = nextSchedule(r, 3, 0);
    r = nextSchedule(r, 3, 0);
    // 3 * 2.5 = 7.5 → 8 (rounded)
    expect(r.intervalDays).toBe(8);
  });

  it('Again (1) resets reps and interval, lowers ease', () => {
    let r = nextSchedule(base, 3, 0);
    r = nextSchedule(r, 1, 0);
    expect(r.reps).toBe(0);
    expect(r.intervalDays).toBe(0);
    expect(r.ease).toBeLessThan(2.5);
  });

  it('Easy (4) raises ease', () => {
    const r = nextSchedule(base, 4, 0);
    expect(r.ease).toBeGreaterThan(2.5);
  });

  it('Hard (2) lowers ease but still advances interval', () => {
    const r = nextSchedule(base, 2, 0);
    expect(r.ease).toBeLessThan(2.5);
    expect(r.intervalDays).toBe(1);
    expect(r.reps).toBe(1);
  });

  it('ease is clamped to the [1.3, 3.0] window', () => {
    let r = { ...base, ease: 1.3, reps: 1, intervalDays: 1 };
    r = nextSchedule(r, 1, 0);
    expect(r.ease).toBe(1.3);

    let s = { ...base, ease: 3.0, reps: 1, intervalDays: 1 };
    s = nextSchedule(s, 4, 0);
    expect(s.ease).toBe(3.0);
  });
});
