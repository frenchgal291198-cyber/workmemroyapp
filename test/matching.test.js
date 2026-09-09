const test = require('node:test');
const assert = require('node:assert/strict');
const M = require('../src/matching');
const S = require('../src/seed');
const X = require('../src/metrics');

const mk = (id, neighborhood, interests, restaurants, department) => ({
  id, name: `Person ${id}`, neighborhood, interests, restaurants, department, optedIn: true,
});

test('same neighborhood outranks shared interests', () => {
  const me = mk('a', 'Astoria', ['running', 'film', 'chess'], [], 'Sales');
  const neighbor = mk('b', 'Astoria', [], [], 'Finance');
  const hobbyist = mk('c', 'Harlem', ['running', 'film', 'chess'], [], 'Finance');
  const n = M.scorePair(me, neighbor).score;
  const h = M.scorePair(me, hobbyist).score;
  assert.ok(n > h, `neighborhood ${n} should beat interests ${h}`);
});

test('nearby neighborhoods score between same neighborhood and same borough', () => {
  const me = mk('a', 'Park Slope', [], [], 'Sales');
  const same = M.scorePair(me, mk('b', 'Park Slope', [], [], 'Finance')).score;
  const nearby = M.scorePair(me, mk('c', 'Prospect Heights', [], [], 'Finance')).score;
  const borough = M.scorePair(me, mk('d', 'Bay Ridge', [], [], 'Finance')).score;
  const far = M.scorePair(me, mk('e', 'Riverdale', [], [], 'Finance')).score;
  assert.ok(same > nearby && nearby > borough && borough > far);
});

test('reasons are plain English and tag matching is case-insensitive', () => {
  const a = mk('a', 'Astoria', ['Karaoke'], ['Taverna Kyclades'], 'Sales');
  const b = mk('b', 'astoria', ['karaoke'], ['taverna kyclades'], 'Legal');
  const { reasons } = M.scorePair(a, b);
  const texts = reasons.map((r) => r.text);
  assert.ok(texts.includes('You both live in Astoria'));
  assert.ok(texts.some((t) => t.startsWith('You both love')));
  assert.ok(texts.some((t) => t.startsWith('Shared interests')));
});

test('shared teams score like restaurants and read as a reason', () => {
  const a = { ...mk('a', 'Astoria', [], [], 'Sales'), teams: ['Liberty', 'Mets'] };
  const b = { ...mk('b', 'Harlem', [], [], 'Legal'), teams: ['liberty', 'Knicks'] };
  const s = M.scorePair(a, b);
  assert.equal(s.score, M.WEIGHTS.sharedTeam + M.WEIGHTS.crossDepartment);
  assert.ok(s.reasons.some((r) => r.text === 'You both follow Liberty'));
  assert.equal(M.commonGround(a, b).count, 1);
});

test('write-in interests match against the list case-insensitively', () => {
  const a = mk('a', 'Astoria', ['Dungeons & Dragons'], [], 'Sales');
  const b = mk('b', 'Harlem', ['dungeons & dragons', 'yoga'], [], 'Legal');
  assert.equal(M.scorePair(a, b).shared.interests.length, 1);
});

test('everyone opted in gets matched; even count yields pairs only', () => {
  const people = S.SEED_PROFILES;
  const { pairs, unmatched } = M.runCycle(people);
  assert.equal(unmatched.length, 0);
  const seen = new Set(pairs.flatMap((p) => p.members));
  assert.equal(seen.size, people.length);
  assert.ok(pairs.every((p) => p.members.length === 2));
});

test('odd count yields exactly one trio and nobody sits out', () => {
  const people = S.SEED_PROFILES.slice(0, 7);
  const { pairs, unmatched } = M.runCycle(people);
  assert.equal(unmatched.length, 0);
  assert.equal(pairs.filter((p) => p.members.length === 3).length, 1);
  assert.equal(pairs.flatMap((p) => p.members).length, 7);
});

test('a pair is never repeated across cycles', () => {
  const people = S.SEED_PROFILES;
  const history = [];
  for (let i = 0; i < 4; i++) history.push(M.runCycle(people, { history }));
  const keys = new Set();
  for (const c of history) for (const p of c.pairs) {
    for (let i = 0; i < p.members.length; i++) for (let j = i + 1; j < p.members.length; j++) {
      const k = M.pairKey(p.members[i], p.members[j]);
      assert.ok(!keys.has(k), `pair ${k} repeated`);
      keys.add(k);
    }
  }
});

test('opted-out profiles are excluded', () => {
  const people = S.SEED_PROFILES.map((p, i) => (i === 0 ? { ...p, optedIn: false } : p));
  const { pairs } = M.runCycle(people);
  assert.ok(!pairs.flatMap((p) => p.members).includes(people[0].id));
});

test('cycle output is deterministic', () => {
  const a = JSON.stringify(M.runCycle(S.SEED_PROFILES).pairs);
  const b = JSON.stringify(M.runCycle([...S.SEED_PROFILES].reverse()).pairs);
  assert.equal(a, b);
});

test('intro message names the strongest shared thing first', () => {
  const people = [mk('a', 'Astoria', ['karaoke'], [], 'Sales'), mk('b', 'Astoria', ['karaoke'], [], 'Legal')];
  const { pairs } = M.runCycle(people);
  const msg = M.introMessage(pairs[0], Object.fromEntries(people.map((p) => [p.id, p])));
  const lines = msg.split('\n');
  assert.equal(lines[1], 'You both live in Astoria.');
  assert.ok(msg.includes('Idea:'));
});

test('metrics compute opt-in, directory usage and acknowledgment', () => {
  const events = [
    { type: 'opt_in', day: 1, userId: 'a' },
    { type: 'opt_in', day: 2, userId: 'b' },
    { type: 'opt_in', day: 2, userId: 'c' },
    { type: 'opt_out', day: 3, userId: 'c' },
    { type: 'directory_view', day: 3, userId: 'a' },
    { type: 'directory_view', day: 20, userId: 'b' },
    { type: 'match_sent', day: 15, cycle: 1, pairId: 'x', members: ['a', 'b'] },
    { type: 'match_sent', day: 15, cycle: 1, pairId: 'y', members: ['c', 'd'] },
    { type: 'match_ack', day: 16, cycle: 1, pairId: 'x', userId: 'a' },
    { type: 'match_ack', day: 40, cycle: 2, pairId: 'z', userId: 'a' }, // future, ignored
  ];
  const m = X.compute(events, { eligibleHeadcount: 10, today: 21 });
  assert.equal(m.optIn.count, 2);
  assert.equal(m.optIn.rate, 0.2);
  assert.equal(m.directory.views, 2);
  assert.equal(m.directory.viewsThisWeek, 1);
  assert.equal(m.matches.sent, 2);
  assert.equal(m.matches.acknowledged, 1);
  assert.equal(m.matches.rate, 0.5);
  assert.equal(m.phase.key, 'run');
  assert.equal(m.week, 3);
});

test('pilot calendar: four cycles fit inside the Run phase', () => {
  assert.equal(X.cycleDay(1), 15);
  assert.equal(X.cycleDay(4), 57);
  assert.equal(X.nextCycle(38, 2).n, 3);
  assert.equal(X.nextCycle(38, 2).daysAway, 5);
  assert.equal(X.nextCycle(60, 4), null);
});
