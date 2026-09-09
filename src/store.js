/*
 * Pilot-scale storage: one JSON file on disk. Fine for ~150 profiles and a
 * 90-day event log. Swap for Postgres if the pilot is formalized.
 */
const fs = require('node:fs');
const path = require('node:path');

class Store {
  constructor(file) {
    this.file = file || path.join(process.cwd(), 'data', 'store.json');
    this.data = { profiles: {}, events: [], cycles: [], startDate: null };
    this.load();
  }

  load() {
    try {
      this.data = { ...this.data, ...JSON.parse(fs.readFileSync(this.file, 'utf8')) };
    } catch (err) {
      if (err.code !== 'ENOENT') throw err;
    }
    if (!this.data.startDate) { this.data.startDate = new Date().toISOString().slice(0, 10); this.save(); }
  }

  save() {
    fs.mkdirSync(path.dirname(this.file), { recursive: true });
    fs.writeFileSync(this.file, JSON.stringify(this.data, null, 2));
  }

  /** Day of the pilot, 1-based, from the recorded start date. */
  today() {
    const start = new Date(this.data.startDate + 'T00:00:00Z');
    return Math.max(1, Math.floor((Date.now() - start.getTime()) / 86400000) + 1);
  }

  profile(userId) { return this.data.profiles[userId] || null; }
  profiles() { return Object.values(this.data.profiles); }

  upsertProfile(profile) {
    const existing = this.data.profiles[profile.id];
    this.data.profiles[profile.id] = { ...existing, ...profile, optedIn: true };
    if (!existing || existing.optedIn === false) this.event({ type: 'opt_in', userId: profile.id });
    this.save();
    return this.data.profiles[profile.id];
  }

  optOut(userId) {
    if (!this.data.profiles[userId]) return;
    this.data.profiles[userId].optedIn = false;
    this.event({ type: 'opt_out', userId });
    this.save();
  }

  event(e) {
    this.data.events.push({ day: this.today(), at: new Date().toISOString(), ...e });
    this.save();
  }

  events() { return this.data.events; }
  cycles() { return this.data.cycles; }

  recordCycle(cycle) {
    this.data.cycles.push(cycle);
    for (const pair of cycle.pairs) {
      this.event({ type: 'match_sent', cycle: cycle.n, pairId: pair.id, members: pair.members });
    }
    this.save();
  }

  acknowledge(pairId, userId) {
    const cycle = this.data.cycles.find((c) => c.pairs.some((p) => p.id === pairId));
    if (!cycle) return false;
    this.event({ type: 'match_ack', cycle: cycle.n, pairId, userId });
    return true;
  }
}

module.exports = { Store };
