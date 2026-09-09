/*
 * Run one matching cycle and DM every pair. Called from `/neighbors cycle`
 * or from cron every two weeks: `npm run cycle`.
 */
const M = require('../matching');
const B = require('./blocks');

async function runAndNotify({ store, client }) {
  const profiles = store.profiles().filter((p) => p.optedIn);
  const history = store.cycles();
  const n = history.length + 1;
  const result = M.runCycle(profiles, { history, now: new Date().toISOString() });
  const cycle = {
    n, day: store.today(), ranAt: result.ranAt,
    pairs: result.pairs.map((p, i) => ({ id: `c${n}-${i + 1}`, ...p })),
    unmatched: result.unmatched,
  };
  store.recordCycle(cycle);

  const byId = Object.fromEntries(profiles.map((p) => [p.id, p]));
  for (const pair of cycle.pairs) {
    if (!client) continue;
    const conv = await client.conversations.open({ users: pair.members.join(',') });
    await client.chat.postMessage({
      channel: conv.channel.id,
      text: M.introMessage(pair, byId),
      blocks: B.matchMessageBlocks(pair, byId),
    });
  }
  return { n, pairs: cycle.pairs, trios: cycle.pairs.filter((p) => p.trio).length };
}

if (require.main === module) {
  const { WebClient } = require('@slack/web-api');
  const { Store } = require('../store');
  const store = new Store(process.env.KYN_STORE);
  const client = process.env.SLACK_BOT_TOKEN ? new WebClient(process.env.SLACK_BOT_TOKEN) : null;
  runAndNotify({ store, client }).then((r) => {
    console.log(`Cycle ${r.n}: ${r.pairs.length} intros${client ? ' sent' : ' (dry run, no SLACK_BOT_TOKEN)'}`);
    for (const p of r.pairs) console.log(' -', p.members.join(' + '), `(${p.score})`, p.reasons.map((x) => x.text).join('; '));
  }).catch((e) => { console.error(e); process.exit(1); });
}

module.exports = { runAndNotify };
