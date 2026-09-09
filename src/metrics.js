/*
 * Pilot metrics — the three numbers the proposal commits to tracking:
 * opt-in rate, directory usage, and match acknowledgment.
 *
 * Computed from an append-only event log so the Slack app and the web
 * prototype produce identical numbers from identical events.
 *
 * Event shapes:
 *   { type: 'opt_in',         day, userId }
 *   { type: 'opt_out',        day, userId }
 *   { type: 'directory_view', day, userId }
 *   { type: 'match_sent',     day, cycle, pairId, members: [ids] }
 *   { type: 'match_ack',      day, cycle, pairId, userId }
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.KYN = Object.assign(root.KYN || {}, factory());
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const PILOT_DAYS = 90;
  const PHASES = [
    { key: 'launch', name: 'Launch', startDay: 1, endDay: 14, weeks: 'Weeks 1–2' },
    { key: 'run', name: 'Run', startDay: 15, endDay: 70, weeks: 'Weeks 3–10' },
    { key: 'review', name: 'Review', startDay: 71, endDay: 90, weeks: 'Weeks 11–12' },
  ];
  const CYCLE_LENGTH_DAYS = 14;

  function phaseForDay(day) {
    return PHASES.find((ph) => day >= ph.startDay && day <= ph.endDay) || PHASES[PHASES.length - 1];
  }

  function weekForDay(day) {
    return Math.max(1, Math.ceil(day / 7));
  }

  /** Cycle n runs on day 15 + 14*(n-1): days 15, 29, 43, 57 — four cycles in the Run phase. */
  function cycleDay(n) {
    return PHASES[1].startDay + CYCLE_LENGTH_DAYS * (n - 1);
  }

  function nextCycle(today, cyclesRun) {
    const n = cyclesRun + 1;
    const day = cycleDay(n);
    if (day > PHASES[1].endDay) return null;
    return { n, day, daysAway: day - today };
  }

  function compute(events, opts) {
    const o = opts || {};
    const eligible = o.eligibleHeadcount || 0;
    const today = o.today || PILOT_DAYS;
    const weekStart = today - 6;

    const optedIn = new Set();
    let directoryViews = 0;
    let directoryViewsThisWeek = 0;
    const viewers = new Set();
    const matches = new Map(); // pairId -> { members, acks:Set, cycle }
    for (const e of events || []) {
      if (e.day != null && e.day > today) continue;
      switch (e.type) {
        case 'opt_in': optedIn.add(e.userId); break;
        case 'opt_out': optedIn.delete(e.userId); break;
        case 'directory_view':
          directoryViews++;
          viewers.add(e.userId);
          if (e.day >= weekStart) directoryViewsThisWeek++;
          break;
        case 'match_sent':
          matches.set(e.pairId, { members: e.members || [], acks: new Set(), cycle: e.cycle });
          break;
        case 'match_ack': {
          const m = matches.get(e.pairId);
          if (m) m.acks.add(e.userId);
          break;
        }
        default: break;
      }
    }

    const matchList = [...matches.values()];
    const acknowledged = matchList.filter((m) => m.acks.size > 0).length;
    const perCycle = {};
    for (const m of matchList) {
      const c = perCycle[m.cycle] || (perCycle[m.cycle] = { sent: 0, acknowledged: 0 });
      c.sent++;
      if (m.acks.size > 0) c.acknowledged++;
    }

    return {
      today,
      week: weekForDay(today),
      phase: phaseForDay(today),
      optIn: { count: optedIn.size, eligible, rate: eligible ? optedIn.size / eligible : 0 },
      directory: { views: directoryViews, viewsThisWeek: directoryViewsThisWeek, uniqueViewers: viewers.size },
      matches: { sent: matchList.length, acknowledged, rate: matchList.length ? acknowledged / matchList.length : 0, perCycle },
    };
  }

  return { PILOT_DAYS, PHASES, CYCLE_LENGTH_DAYS, phaseForDay, weekForDay, cycleDay, nextCycle, compute };
});
