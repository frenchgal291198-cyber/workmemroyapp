/*
 * Know Your Neighbors — Slack app (Bolt for JavaScript).
 *
 * Slash command:  /neighbors            → help
 *                 /neighbors profile    → open the profile modal (joins the pilot)
 *                 /neighbors directory [filter]
 *                 /neighbors leave
 *                 /neighbors cycle      → run a match cycle (pilot admins only)
 *
 * Env: SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, SLACK_APP_TOKEN (Socket Mode),
 *      KYN_ADMINS (comma-separated Slack user ids), KYN_STORE (path to JSON file).
 */
const { App } = require('@slack/bolt');
const M = require('../matching');
const X = require('../metrics');
const S = require('../seed');
const { Store } = require('../store');
const B = require('./blocks');
const { runAndNotify } = require('./run-cycle');

const store = new Store(process.env.KYN_STORE);
const ADMINS = new Set((process.env.KYN_ADMINS || '').split(',').map((s) => s.trim()).filter(Boolean));
const ELIGIBLE = Number(process.env.KYN_ELIGIBLE_HEADCOUNT || S.ELIGIBLE_HEADCOUNT);

const app = new App({
  token: process.env.SLACK_BOT_TOKEN,
  signingSecret: process.env.SLACK_SIGNING_SECRET,
  appToken: process.env.SLACK_APP_TOKEN,
  socketMode: Boolean(process.env.SLACK_APP_TOKEN),
});

const HELP = [
  '*Know Your Neighbors* — opt-in pilot, corporate staff only.',
  '`/neighbors profile` — join, or edit your neighborhood and interests',
  '`/neighbors directory [neighborhood | interest | department]` — see who\'s near you',
  '`/neighbors leave` — opt out; your profile is hidden immediately',
].join('\n');

app.command('/neighbors', async ({ command, ack, client, respond }) => {
  await ack();
  const [sub, ...rest] = command.text.trim().split(/\s+/);
  const me = store.profile(command.user_id);
  switch ((sub || '').toLowerCase()) {
    case 'profile':
      await client.views.open({ trigger_id: command.trigger_id, view: B.profileModal(me) });
      break;
    case 'directory':
      store.event({ type: 'directory_view', userId: command.user_id });
      await respond({ response_type: 'ephemeral', blocks: B.directoryBlocks(store.profiles().filter((p) => p.optedIn), me, rest.join(' ')) });
      break;
    case 'leave':
      store.optOut(command.user_id);
      await respond({ response_type: 'ephemeral', text: 'You\'re out. Your profile is hidden and you won\'t be matched. Come back any time with `/neighbors profile`.' });
      break;
    case 'cycle':
      if (!ADMINS.has(command.user_id)) { await respond({ response_type: 'ephemeral', text: 'Only pilot admins can run a cycle.' }); break; }
      { const result = await runAndNotify({ store, client });
        await respond({ response_type: 'ephemeral', text: `Cycle ${result.n} sent: ${result.pairs.length} intros, ${result.trios} trio${result.trios === 1 ? '' : 's'}.` }); }
      break;
    default:
      await respond({ response_type: 'ephemeral', text: HELP });
  }
});

app.view('kyn_profile', async ({ ack, body, view, client }) => {
  await ack();
  const info = await client.users.info({ user: body.user.id });
  const profile = B.parseProfileSubmission(view, { id: body.user.id, real_name: info.user.real_name, name: info.user.name });
  store.upsertProfile(profile);
  await client.chat.postMessage({
    channel: body.user.id,
    text: `You're in. Neighborhood: ${profile.neighborhood}. Next match cycle goes out ${nextCycleText()}. Browse neighbors any time with \`/neighbors directory\`.`,
  });
  await publishHome(client, body.user.id);
});

app.action('kyn_open_profile', async ({ ack, body, client }) => {
  await ack();
  await client.views.open({ trigger_id: body.trigger_id, view: B.profileModal(store.profile(body.user.id)) });
});

app.action('kyn_open_directory', async ({ ack, body, client }) => {
  await ack();
  store.event({ type: 'directory_view', userId: body.user.id });
  await client.chat.postEphemeral({
    channel: body.user.id, user: body.user.id,
    blocks: B.directoryBlocks(store.profiles().filter((p) => p.optedIn), store.profile(body.user.id), ''),
  });
});

app.action('kyn_say_hi', async ({ ack, body, client, action }) => {
  await ack();
  const conv = await client.conversations.open({ users: `${body.user.id},${action.value}` });
  const target = store.profile(action.value);
  await client.chat.postEphemeral({ channel: body.user.id, user: body.user.id, text: `Opened a DM with ${target ? target.name : 'them'}: <#${conv.channel.id}>` });
});

app.action('kyn_ack', async ({ ack, body, client, action, respond }) => {
  await ack();
  store.acknowledge(action.value, body.user.id);
  await respond({ replace_original: false, response_type: 'ephemeral', text: 'Logged. Thanks for closing the loop.' });
  await publishHome(client, body.user.id);
});

app.action('kyn_skip', async ({ ack, respond }) => {
  await ack();
  await respond({ replace_original: false, response_type: 'ephemeral', text: 'No problem. You\'ll get a new match next cycle.' });
});

app.event('app_home_opened', async ({ event, client }) => publishHome(client, event.user));

function nextCycleText() {
  const next = X.nextCycle(store.today(), store.cycles().length);
  return next ? `in ${next.daysAway} day${next.daysAway === 1 ? '' : 's'}` : 'when the next pilot phase starts';
}

async function publishHome(client, userId) {
  const metrics = X.compute(store.events(), { eligibleHeadcount: ELIGIBLE, today: store.today() });
  const next = X.nextCycle(store.today(), store.cycles().length);
  await client.views.publish({ user_id: userId, view: B.homeTab(metrics, store.profile(userId), next) });
}

if (require.main === module) {
  (async () => {
    await app.start(Number(process.env.PORT) || 3000);
    console.log('Know Your Neighbors is running. Day', store.today(), 'of the pilot.');
  })();
}

module.exports = { app, store };
