/* Block Kit builders for the Know Your Neighbors Slack app. */
const M = require('../matching');
const S = require('../seed');

const opt = (text, value) => ({ text: { type: 'plain_text', text }, value: value == null ? text : value });

function profileModal(existing) {
  const e = existing || {};
  const hoodOptions = M.BOROUGHS.map((b) => ({
    label: { type: 'plain_text', text: b },
    options: M.NEIGHBORHOODS.filter((n) => n.borough === b).map((n) => opt(n.name)),
  }));
  const interestOptions = S.INTERESTS.map((i) => opt(i));
  const lower = (xs) => (xs || []).map((x) => String(x).toLowerCase());
  const listedInterests = (e.interests || []).filter((i) => lower(S.INTERESTS).includes(i.toLowerCase()));
  const customInterests = (e.interests || []).filter((i) => !lower(S.INTERESTS).includes(i.toLowerCase()));
  const listedTeams = (e.teams || []).filter((t) => lower(S.TEAMS).includes(t.toLowerCase()));
  const customTeams = (e.teams || []).filter((t) => !lower(S.TEAMS).includes(t.toLowerCase()));
  return {
    type: 'modal',
    callback_id: 'kyn_profile',
    title: { type: 'plain_text', text: 'Your neighbor profile' },
    submit: { type: 'plain_text', text: e.id ? 'Save' : 'Save & opt in' },
    close: { type: 'plain_text', text: 'Cancel' },
    blocks: [
      { type: 'context', elements: [{ type: 'mrkdwn', text: 'Opt-in pilot. Only opted-in colleagues can see this, and you can leave any time with `/neighbors leave`.' }] },
      {
        type: 'input', block_id: 'department',
        label: { type: 'plain_text', text: 'Department' },
        element: { type: 'static_select', action_id: 'v', options: S.DEPARTMENTS.map((d) => opt(d)),
          ...(e.department ? { initial_option: opt(e.department) } : {}) },
      },
      {
        type: 'input', block_id: 'neighborhood',
        label: { type: 'plain_text', text: 'Home neighborhood' },
        element: { type: 'static_select', action_id: 'v', option_groups: hoodOptions,
          ...(e.neighborhood ? { initial_option: opt(e.neighborhood) } : {}) },
      },
      {
        type: 'input', block_id: 'interests',
        label: { type: 'plain_text', text: 'Interests & hobbies' },
        hint: { type: 'plain_text', text: 'Pick up to five.' },
        element: { type: 'multi_static_select', action_id: 'v', max_selected_items: 5, options: interestOptions,
          ...(listedInterests.length ? { initial_options: listedInterests.map((i) => opt(i)) } : {}) },
      },
      {
        type: 'input', block_id: 'other_interests', optional: true,
        label: { type: 'plain_text', text: 'Anything not on the list?' },
        hint: { type: 'plain_text', text: 'Comma-separated. Write-ins match other people\'s write-ins.' },
        element: { type: 'plain_text_input', action_id: 'v', placeholder: { type: 'plain_text', text: 'Dungeons & Dragons, roller skating' },
          ...(customInterests.length ? { initial_value: customInterests.join(', ') } : {}) },
      },
      {
        type: 'input', block_id: 'teams', optional: true,
        label: { type: 'plain_text', text: 'Teams you follow' },
        hint: { type: 'plain_text', text: 'A shared team scores like a shared restaurant. Up to four.' },
        element: { type: 'multi_static_select', action_id: 'v', max_selected_items: 4, options: S.TEAMS.map((t) => opt(t)),
          ...(listedTeams.length ? { initial_options: listedTeams.map((t) => opt(t)) } : {}) },
      },
      {
        type: 'input', block_id: 'other_teams', optional: true,
        label: { type: 'plain_text', text: 'Other teams, any sport or college' },
        element: { type: 'plain_text_input', action_id: 'v', placeholder: { type: 'plain_text', text: 'Arsenal, Syracuse basketball' },
          ...(customTeams.length ? { initial_value: customTeams.join(', ') } : {}) },
      },
      {
        type: 'input', block_id: 'restaurants', optional: true,
        label: { type: 'plain_text', text: 'Favorite restaurants' },
        hint: { type: 'plain_text', text: 'Comma-separated. A shared favorite is the easiest first plan.' },
        element: { type: 'plain_text_input', action_id: 'v', placeholder: { type: 'plain_text', text: 'Taverna Kyclades, Di Fara' },
          ...(e.restaurants && e.restaurants.length ? { initial_value: e.restaurants.join(', ') } : {}) },
      },
    ],
  };
}

function parseProfileSubmission(view, user) {
  const v = view.state.values;
  const csv = (block) => String((v[block] && v[block].v && v[block].v.value) || '').split(',').map((s) => s.trim()).filter(Boolean);
  const dedupe = (xs) => xs.filter((x, i) => xs.findIndex((y) => y.toLowerCase() === x.toLowerCase()) === i);
  return {
    id: user.id,
    name: user.real_name || user.name,
    department: v.department.v.selected_option.value,
    neighborhood: v.neighborhood.v.selected_option.value,
    interests: dedupe([...(v.interests.v.selected_options || []).map((o) => o.value), ...csv('other_interests')]),
    teams: dedupe([...((v.teams && v.teams.v.selected_options) || []).map((o) => o.value), ...csv('other_teams')]).slice(0, 4),
    restaurants: csv('restaurants'),
  };
}

function directoryBlocks(profiles, me, filter) {
  const rows = profiles
    .filter((p) => p.id !== (me && me.id))
    .filter((p) => !filter || [p.neighborhood, p.department, ...(p.interests || [])].some((x) => String(x).toLowerCase().includes(filter.toLowerCase())))
    .map((p) => ({ p, common: M.commonGround(me, p) }))
    .sort((a, b) => b.common.score - a.common.score)
    .slice(0, 20);
  const blocks = [{ type: 'header', text: { type: 'plain_text', text: filter ? `Neighbors matching “${filter}”` : 'Your neighbors' } }];
  if (!rows.length) blocks.push({ type: 'section', text: { type: 'mrkdwn', text: 'Nobody matches that yet. Try a neighborhood, a department, or an interest.' } });
  for (const { p, common } of rows) {
    const info = M.neighborhoodInfo(p.neighborhood);
    const line = `*${p.name}* · ${p.department}\n:round_pushpin: ${p.neighborhood}, ${info.borough} · ${(p.interests || []).join(', ')}` +
      (p.teams && p.teams.length ? ` · :trophy: ${p.teams.join(', ')}` : '') +
      (p.restaurants && p.restaurants.length ? `\n:fork_and_knife: ${p.restaurants.join(', ')}` : '') +
      (common.count ? `\n_${common.count} in common: ${common.items.join('; ')}_` : '');
    blocks.push({
      type: 'section', text: { type: 'mrkdwn', text: line },
      accessory: { type: 'button', text: { type: 'plain_text', text: 'Say hi' }, action_id: 'kyn_say_hi', value: p.id },
    });
  }
  return blocks;
}

function matchMessageBlocks(pair, profileById) {
  return [
    { type: 'section', text: { type: 'mrkdwn', text: M.introMessage(pair, profileById) } },
    {
      type: 'actions', block_id: `ack_${pair.id}`,
      elements: [
        { type: 'button', style: 'primary', text: { type: 'plain_text', text: 'We met ☕' }, action_id: 'kyn_ack', value: pair.id },
        { type: 'button', text: { type: 'plain_text', text: 'Not this time' }, action_id: 'kyn_skip', value: pair.id },
      ],
    },
    { type: 'context', elements: [{ type: 'mrkdwn', text: 'Tapping “We met” is the only thing we track. It tells HR whether matches turn into real conversations.' }] },
  ];
}

function homeTab(metrics, me, next) {
  const pct = (x) => `${Math.round(x * 100)}%`;
  return {
    type: 'home',
    blocks: [
      { type: 'header', text: { type: 'plain_text', text: 'Know Your Neighbors' } },
      { type: 'context', elements: [{ type: 'mrkdwn', text: `Day ${metrics.today} of 90 · ${metrics.phase.name} phase · ` + (next ? `next match cycle in ${next.daysAway} day${next.daysAway === 1 ? '' : 's'}` : 'matching complete') }] },
      { type: 'section', fields: [
        { type: 'mrkdwn', text: `*Opted in*\n${metrics.optIn.count} of ${metrics.optIn.eligible} (${pct(metrics.optIn.rate)})` },
        { type: 'mrkdwn', text: `*Directory views*\n${metrics.directory.views} total · ${metrics.directory.viewsThisWeek} this week` },
        { type: 'mrkdwn', text: `*Matches acknowledged*\n${metrics.matches.acknowledged} of ${metrics.matches.sent} (${pct(metrics.matches.rate)})` },
      ] },
      { type: 'divider' },
      { type: 'section', text: { type: 'mrkdwn', text: me ? `You're in as *${me.neighborhood}* · ${(me.interests || []).join(', ')}` : "You haven't joined yet. Takes about a minute." },
        accessory: { type: 'button', text: { type: 'plain_text', text: me ? 'Edit profile' : 'Join the pilot' }, action_id: 'kyn_open_profile' } },
      { type: 'section', text: { type: 'mrkdwn', text: 'Browse who lives near you or shares a hobby.' },
        accessory: { type: 'button', text: { type: 'plain_text', text: 'Open directory' }, action_id: 'kyn_open_directory' } },
    ],
  };
}

module.exports = { profileModal, parseProfileSubmission, directoryBlocks, matchMessageBlocks, homeTab };
