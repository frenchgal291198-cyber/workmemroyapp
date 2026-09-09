/*
 * Know Your Neighbors — matching engine.
 *
 * Pure functions, no I/O. Works in Node (module.exports) and in the browser
 * (attached to window.KYN) so the Slack app and the web prototype share one
 * implementation.
 *
 * Weighting follows the pilot plan: shared neighborhood first, shared
 * interests second. Restaurants count a little more than a generic interest
 * because a shared restaurant is a concrete plan, not just a topic.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.KYN = Object.assign(root.KYN || {}, factory());
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const WEIGHTS = Object.freeze({
    sameNeighborhood: 10,
    nearbyNeighborhood: 6,   // same area cluster (e.g. Park Slope <-> Prospect Heights)
    sameBorough: 3,
    sharedRestaurant: 3,     // per shared restaurant
    sharedInterest: 2,       // per shared interest
    crossDepartment: 1,      // the tool exists to cross silos
    sameDepartment: -2,      // still allowed, just not preferred
    pairedBefore: -1000,     // never repeat a match within a pilot
  });

  // NYC neighborhoods the pilot supports. `area` groups neighborhoods that
  // are a short walk or one subway stop apart, so "nearby" can score.
  const NEIGHBORHOODS = [
    // Brooklyn
    { name: 'Downtown Brooklyn', borough: 'Brooklyn', area: 'Downtown Brooklyn' },
    { name: 'Fort Greene', borough: 'Brooklyn', area: 'Downtown Brooklyn' },
    { name: 'Clinton Hill', borough: 'Brooklyn', area: 'Downtown Brooklyn' },
    { name: 'Boerum Hill', borough: 'Brooklyn', area: 'Brownstone Brooklyn' },
    { name: 'Cobble Hill', borough: 'Brooklyn', area: 'Brownstone Brooklyn' },
    { name: 'Carroll Gardens', borough: 'Brooklyn', area: 'Brownstone Brooklyn' },
    { name: 'Park Slope', borough: 'Brooklyn', area: 'Prospect Park West' },
    { name: 'Prospect Heights', borough: 'Brooklyn', area: 'Prospect Park West' },
    { name: 'Gowanus', borough: 'Brooklyn', area: 'Prospect Park West' },
    { name: 'Windsor Terrace', borough: 'Brooklyn', area: 'Prospect Park West' },
    { name: 'Crown Heights', borough: 'Brooklyn', area: 'Central Brooklyn' },
    { name: 'Bed-Stuy', borough: 'Brooklyn', area: 'Central Brooklyn' },
    { name: 'Flatbush', borough: 'Brooklyn', area: 'Flatbush' },
    { name: 'Ditmas Park', borough: 'Brooklyn', area: 'Flatbush' },
    { name: 'Williamsburg', borough: 'Brooklyn', area: 'North Brooklyn' },
    { name: 'Greenpoint', borough: 'Brooklyn', area: 'North Brooklyn' },
    { name: 'Bushwick', borough: 'Brooklyn', area: 'North Brooklyn' },
    { name: 'Bay Ridge', borough: 'Brooklyn', area: 'South Brooklyn' },
    { name: 'Sunset Park', borough: 'Brooklyn', area: 'South Brooklyn' },
    // Queens
    { name: 'Astoria', borough: 'Queens', area: 'Western Queens' },
    { name: 'Long Island City', borough: 'Queens', area: 'Western Queens' },
    { name: 'Sunnyside', borough: 'Queens', area: 'Western Queens' },
    { name: 'Jackson Heights', borough: 'Queens', area: 'Central Queens' },
    { name: 'Forest Hills', borough: 'Queens', area: 'Central Queens' },
    { name: 'Flushing', borough: 'Queens', area: 'Eastern Queens' },
    { name: 'Ridgewood', borough: 'Queens', area: 'North Brooklyn' },
    // Manhattan
    { name: 'Harlem', borough: 'Manhattan', area: 'Upper Manhattan' },
    { name: 'Washington Heights', borough: 'Manhattan', area: 'Upper Manhattan' },
    { name: 'Upper West Side', borough: 'Manhattan', area: 'Uptown' },
    { name: 'Upper East Side', borough: 'Manhattan', area: 'Uptown' },
    { name: "Hell's Kitchen", borough: 'Manhattan', area: 'Midtown West' },
    { name: 'Chelsea', borough: 'Manhattan', area: 'Midtown West' },
    { name: 'East Village', borough: 'Manhattan', area: 'Downtown Manhattan' },
    { name: 'Lower East Side', borough: 'Manhattan', area: 'Downtown Manhattan' },
    { name: 'West Village', borough: 'Manhattan', area: 'Downtown Manhattan' },
    { name: 'Financial District', borough: 'Manhattan', area: 'Downtown Manhattan' },
    // Bronx
    { name: 'Riverdale', borough: 'Bronx', area: 'Northwest Bronx' },
    { name: 'Mott Haven', borough: 'Bronx', area: 'South Bronx' },
    { name: 'Belmont', borough: 'Bronx', area: 'Central Bronx' },
    // Staten Island
    { name: 'St. George', borough: 'Staten Island', area: 'North Shore' },
    { name: 'Stapleton', borough: 'Staten Island', area: 'North Shore' },
    // New Jersey commuters
    { name: 'Hoboken', borough: 'New Jersey', area: 'Hudson Waterfront' },
    { name: 'Jersey City', borough: 'New Jersey', area: 'Hudson Waterfront' },
  ];

  const BOROUGHS = ['Brooklyn', 'Queens', 'Manhattan', 'Bronx', 'Staten Island', 'New Jersey'];

  const byName = new Map(NEIGHBORHOODS.map((n) => [n.name.toLowerCase(), n]));

  function neighborhoodInfo(name) {
    if (!name) return null;
    return byName.get(String(name).trim().toLowerCase()) || { name, borough: 'Other', area: name };
  }

  function norm(list) {
    return new Set((list || []).map((s) => String(s).trim().toLowerCase()).filter(Boolean));
  }

  function shared(a, b) {
    const sb = norm(b);
    const out = [];
    for (const x of a || []) if (sb.has(String(x).trim().toLowerCase())) out.push(x);
    return out;
  }

  function pairKey(idA, idB) {
    return [String(idA), String(idB)].sort().join('|');
  }

  /** Set of pair keys that have already been matched in earlier cycles. */
  function historyKeys(history) {
    const keys = new Set();
    for (const cycle of history || []) {
      for (const pair of cycle.pairs || []) {
        const ids = pair.members || [];
        for (let i = 0; i < ids.length; i++)
          for (let j = i + 1; j < ids.length; j++) keys.add(pairKey(ids[i], ids[j]));
      }
    }
    return keys;
  }

  /**
   * Score one pair. Returns { score, reasons } where reasons are plain-English
   * strings suitable for the intro message ("You both live in Astoria").
   */
  function scorePair(a, b, opts) {
    const history = (opts && opts.historyKeys) || new Set();
    const reasons = [];
    let score = 0;

    const na = neighborhoodInfo(a.neighborhood);
    const nb = neighborhoodInfo(b.neighborhood);
    if (na && nb) {
      if (na.name.toLowerCase() === nb.name.toLowerCase()) {
        score += WEIGHTS.sameNeighborhood;
        reasons.push({ type: 'neighborhood', text: `You both live in ${na.name}` });
      } else if (na.area === nb.area) {
        score += WEIGHTS.nearbyNeighborhood;
        reasons.push({ type: 'nearby', text: `${na.name} and ${nb.name} are neighbors` });
      } else if (na.borough === nb.borough && na.borough !== 'Other') {
        score += WEIGHTS.sameBorough;
        reasons.push({ type: 'borough', text: `You're both in ${na.borough}` });
      }
    }

    const rest = shared(a.restaurants, b.restaurants);
    if (rest.length) {
      score += WEIGHTS.sharedRestaurant * rest.length;
      reasons.push({ type: 'restaurant', text: `You both love ${listify(rest)}` });
    }

    const ints = shared(a.interests, b.interests);
    if (ints.length) {
      score += WEIGHTS.sharedInterest * ints.length;
      reasons.push({ type: 'interest', text: `Shared interests: ${listify(ints)}` });
    }

    if (a.department && b.department) {
      if (a.department === b.department) score += WEIGHTS.sameDepartment;
      else {
        score += WEIGHTS.crossDepartment;
        reasons.push({ type: 'department', text: `${a.department} meets ${b.department}` });
      }
    }

    if (history.has(pairKey(a.id, b.id))) {
      score += WEIGHTS.pairedBefore;
      reasons.push({ type: 'repeat', text: 'Already matched in an earlier cycle' });
    }

    return { score, reasons, shared: { neighborhood: na && nb && na.name === nb.name, restaurants: rest, interests: ints } };
  }

  function listify(items) {
    const xs = items.map(String);
    if (xs.length <= 1) return xs.join('');
    if (xs.length === 2) return `${xs[0]} and ${xs[1]}`;
    return `${xs.slice(0, -1).join(', ')}, and ${xs[xs.length - 1]}`;
  }

  /**
   * Run one matching cycle over opted-in profiles.
   *
   * Greedy maximum-weight pairing: score every pair, take the best pair whose
   * members are still free, repeat. With an odd count, the leftover person
   * joins the pair they fit best with, making one trio (nobody sits out).
   * Deterministic: ties break on ids, so the same input gives the same output.
   */
  function runCycle(profiles, opts) {
    const options = opts || {};
    const people = (profiles || [])
      .filter((p) => p && p.id != null && p.optedIn !== false)
      .sort((x, y) => String(x.id).localeCompare(String(y.id)));
    const hk = historyKeys(options.history);
    const scored = [];
    for (let i = 0; i < people.length; i++) {
      for (let j = i + 1; j < people.length; j++) {
        const s = scorePair(people[i], people[j], { historyKeys: hk });
        scored.push({ a: people[i], b: people[j], score: s.score, reasons: s.reasons });
      }
    }
    scored.sort((x, y) => y.score - x.score || pairKey(x.a.id, x.b.id).localeCompare(pairKey(y.a.id, y.b.id)));

    const taken = new Set();
    const pairs = [];
    for (const s of scored) {
      if (taken.has(s.a.id) || taken.has(s.b.id)) continue;
      taken.add(s.a.id);
      taken.add(s.b.id);
      pairs.push({ members: [s.a.id, s.b.id], score: s.score, reasons: s.reasons.filter((r) => r.type !== 'repeat') });
    }

    const leftover = people.filter((p) => !taken.has(p.id));
    const unmatched = [];
    for (const solo of leftover) {
      if (!pairs.length) { unmatched.push(solo.id); continue; }
      let best = null;
      for (const pair of pairs) {
        if (pair.members.length > 2) continue;
        const total = pair.members.reduce((acc, id) => {
          const other = people.find((p) => p.id === id);
          return acc + scorePair(solo, other, { historyKeys: hk }).score;
        }, 0);
        if (!best || total > best.total) best = { pair, total };
      }
      if (!best) { unmatched.push(solo.id); continue; }
      best.pair.members.push(solo.id);
      best.pair.trio = true;
      best.pair.reasons.push({ type: 'trio', text: `${solo.name} joins as a third so nobody sits out` });
    }

    return { pairs, unmatched, ranAt: options.now || null };
  }

  /** The Slack DM the bot sends to a matched pair. */
  function introMessage(pair, profileById) {
    const members = pair.members.map((id) => profileById[id]).filter(Boolean);
    const names = members.map((m) => m.name.split(' ')[0]);
    const lead = pair.reasons.find((r) => r.type === 'neighborhood' || r.type === 'nearby' || r.type === 'borough');
    const others = pair.reasons.filter((r) => r !== lead && r.type !== 'department' && r.type !== 'trio');
    const lines = [];
    lines.push(`Hi ${listify(names)} — this cycle's match.`);
    if (lead) lines.push(lead.text + '.');
    for (const r of others) lines.push(r.text + '.');
    const dept = pair.reasons.find((r) => r.type === 'department');
    if (dept) lines.push(`(${dept.text}: two teams that rarely cross paths.)`);
    const trio = pair.reasons.find((r) => r.type === 'trio');
    if (trio) lines.push(trio.text + '.');
    lines.push(suggestion(pair, members));
    return lines.join('\n');
  }

  function suggestion(pair, members) {
    const rest = pair.reasons.find((r) => r.type === 'restaurant');
    if (rest) return 'Idea: grab a table there after work this week.';
    const hood = pair.reasons.find((r) => r.type === 'neighborhood' || r.type === 'nearby');
    if (hood) return 'Idea: coffee near home on Saturday, or split the commute in.';
    const interest = pair.reasons.find((r) => r.type === 'interest');
    if (interest) return 'Idea: a 20-minute walk around the arena on a game-free day.';
    return 'Idea: say hi in the kitchen this week.';
  }

  /** Quick "what do we have in common" for directory cards. */
  function commonGround(me, other) {
    if (!me || !other) return { count: 0, items: [] };
    const s = scorePair(me, other, {});
    const items = s.reasons.filter((r) => r.type !== 'department').map((r) => r.text);
    return { count: (s.shared.neighborhood ? 1 : 0) + s.shared.restaurants.length + s.shared.interests.length, items, score: s.score };
  }

  return { WEIGHTS, NEIGHBORHOODS, BOROUGHS, neighborhoodInfo, scorePair, runCycle, introMessage, commonGround, pairKey, historyKeys, listify };
});
