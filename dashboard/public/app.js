// Crewism dashboard frontend. Every control hits a real bot-API endpoint.
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const state = { guildId: localStorage.getItem('crewism_guild') || '', guilds: [] };

async function api(path, opts = {}) {
  const r = await fetch(path, {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
  });
  if (!r.ok) throw new Error(`api ${r.status}`);
  return r.json();
}
const fmt = (n) => Number(n || 0).toLocaleString();
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const time = (iso) => { try { return new Date(iso + (iso.endsWith('Z') ? '' : 'Z')).toLocaleString(); } catch { return iso; } };
const q = (gid) => (gid ? `?guild_id=${gid}` : '');
const qp = (gid, extra) => (gid ? `?guild_id=${gid}&${extra}` : `?${extra}`);

// ---- tabs ----
$$('.sidebar button').forEach((b) => b.addEventListener('click', () => {
  $$('.sidebar button').forEach((x) => x.classList.remove('active'));
  b.classList.add('active');
  $$('.tab').forEach((t) => t.classList.remove('active'));
  $('#tab-' + b.dataset.tab).classList.add('active');
  loadTab(b.dataset.tab);
}));

// ---- guilds ----
async function loadHealth() {
  try {
    const h = await api('/api/health');
    state.guilds = h.guilds || [];
    $('#status-dot').className = 'dot on';
    $('#status-text').textContent = `online · ${state.guilds.length} server(s)`;
    const sel = $('#guild-select');
    sel.innerHTML = state.guilds.map((g) => `<option value="${g.id}">${esc(g.name)}</option>`).join('')
      || '<option value="">no servers</option>';
    if (!state.guildId && state.guilds[0]) state.guildId = String(state.guilds[0].id);
    if (state.guildId && !state.guilds.some((g) => String(g.id) === state.guildId)) {
      state.guildId = state.guilds[0] ? String(state.guilds[0].id) : '';
    }
    sel.value = state.guildId;
    localStorage.setItem('crewism_guild', state.guildId);
  } catch {
    $('#status-dot').className = 'dot off';
    $('#status-text').textContent = 'offline — is the bot running?';
  }
}
$('#guild-select').addEventListener('change', (e) => {
  state.guildId = e.target.value;
  localStorage.setItem('crewism_guild', state.guildId);
  refreshAll();
});
$('#refresh-btn').addEventListener('click', refreshAll);

function card(v, k, cls = '') {
  return `<div class="stat-card ${cls}"><div class="v">${v}</div><div class="k">${k}</div></div>`;
}

// ---- overview ----
async function loadOverview() {
  const o = await api('/api/overview' + q(state.guildId));
  $('#stat-cards').innerHTML =
    card(fmt(o.players), 'fighters', 'green') +
    card(fmt(o.money_supply), 'won in circulation', 'gold') +
    card(fmt(o.characters), 'recruited', 'blue') +
    card(fmt(o.crews), 'crews', 'purple') +
    card(fmt(o.battles_7d), 'battles / 7d', 'red') +
    card(fmt(o.territories_held || 0), 'turf held', '');
  $('#guild-cards').innerHTML = state.guilds.map((g) =>
    `<div class="stat-card"><div class="v" style="font-size:17px">${esc(g.name)}</div><div class="k">${g.id} · ${g.members ?? '?'} members</div></div>`).join('');
  const rows = await api('/api/ledger' + qp(state.guildId, 'limit=8'));
  $('#activity-table tbody').innerHTML = rows.map((r) =>
    `<tr><td>${time(r.created_at)}</td><td>${r.user_id}</td>
     <td class="${r.amount >= 0 ? 'pos' : 'neg'}">${r.amount >= 0 ? '+' : ''}${fmt(r.amount)}</td>
     <td>${esc(r.reason)}</td></tr>`).join('') || '<tr><td colspan="4">no activity yet</td></tr>';
}

// ---- server setup ----
async function loadServer() {
  if (!state.guildId) return;
  const s = await api(`/api/server/${state.guildId}`);
  const g = state.guilds.find((x) => String(x.id) === state.guildId);
  $('#server-name').textContent = g ? `— ${g.name}` : '';
  $$('#tab-server .switch').forEach((sw) => sw.classList.toggle('on', !!s[sw.dataset.key]));
  $('#daily-base').value = s.config?.daily_base ?? 500;
  $('#spawn-channel').value = s.spawn_channel ?? '';
}
$$('#tab-server .switch').forEach((sw) => sw.addEventListener('click', () => sw.classList.toggle('on')));
$('#save-server').addEventListener('click', async () => {
  const body = {};
  $$('#tab-server .switch').forEach((sw) => (body[sw.dataset.key] = sw.classList.contains('on') ? 1 : 0));
  const sc = $('#spawn-channel').value.trim();
  body.spawn_channel = sc ? sc : null;
  body.config = { daily_base: Math.max(0, Math.min(10000, Number($('#daily-base').value || 500))) };
  try {
    await api(`/api/server/${state.guildId}`, { method: 'POST', body: JSON.stringify(body) });
    $('#save-msg').textContent = 'saved — live immediately, no restart';
    setTimeout(() => ($('#save-msg').textContent = ''), 2500);
  } catch { $('#save-msg').textContent = 'save failed'; }
});

// ---- players ----
async function loadPlayers() {
  const sort = $('#player-sort').value;
  const rows = await api(`/api/players${qp(state.guildId, `sort=${sort}&limit=50`)}`);
  $(`#players-table tbody`).innerHTML = rows.map((p, i) =>
    `<tr><td>${i + 1}</td><td>${esc(p.name)}</td><td>${p.level}</td><td>${fmt(p.money)}</td>
     <td class="pos">${p.wins}</td><td class="neg">${p.losses ?? ''}</td><td>${fmt(p.bounty)}</td></tr>`).join('')
    || '<tr><td colspan="7">no players yet — run /profile in Discord</td></tr>';
}
$('#player-sort').addEventListener('change', loadPlayers);

// ---- economy ----
async function loadEconomy() {
  const o = await api('/api/overview' + q(state.guildId));
  $('#econ-cards').innerHTML =
    card(fmt(o.money_supply), 'total won', 'gold') + card(fmt(o.players), 'wallets', '');
  const rows = await api('/api/ledger' + q(state.guildId));
  $('#ledger-table tbody').innerHTML = rows.map((r) =>
    `<tr><td>${time(r.created_at)}</td><td>${r.user_id}</td>
     <td class="${r.amount >= 0 ? 'pos' : 'neg'}">${r.amount >= 0 ? '+' : ''}${fmt(r.amount)}</td>
     <td>${fmt(r.after)}</td><td>${esc(r.reason)}${r.ref ? ` <small>${esc(r.ref)}</small>` : ''}</td></tr>`).join('')
    || '<tr><td colspan="5">empty</td></tr>';
}

// ---- bosses ----
async function loadBosses() {
  const rows = await api('/api/bosses');
  $('#boss-cards').innerHTML = rows.map((b) => {
    const f = b.fights_7d || 0, k = b.kills_7d || 0;
    const pct = f ? Math.round((k / f) * 100) : 0;
    return `<div class="boss-card"><div class="name">${esc(b.name)}</div>
      <div class="meta">LV${b.level} · ${esc(b.region)} · ${f} fights / ${k} kills (7d)</div>
      <div class="bar"><div style="width:${pct}%"></div></div></div>`;
  }).join('');
}

// ---- territories ----
async function loadTerritories() {
  const rows = await api('/api/territories' + q(state.guildId));
  const g = state.guilds.find((x) => String(x.id) === state.guildId);
  $('#terr-guild').textContent = g ? `— ${g.name}` : '(pick a server)';
  $('#terr-list').innerHTML = rows.map((t) => {
    const owner = t.owner_type === 'crew' && t.crew_name ? t.crew_name
      : t.owner_type === 'player' ? 'a solo fighter' : 'NPC';
    const cls = t.owner_type === 'npc' ? 'npc' : t.owner_type;
    return `<div class="terr-row"><span><b>${esc(t.name)}</b> <small>· LV${t.rec_level}+ · ${fmt(t.income)} Won/day</small></span>
      <span class="badge ${cls}">${esc(owner)}</span></div>`;
  }).join('');
}

// ---- events ----
async function loadEvents() {
  const rows = await api('/api/events');
  $('#event-list').innerHTML = rows.map((e) =>
    `<div class="event-row"><span><b>${esc(e.name)}</b> <small>· ${esc(e.id)}</small></span>
     <button class="switch ${e.active ? 'on' : ''}" data-id="${esc(e.id)}"></button></div>`).join('')
    || '<div class="hint">no events defined yet</div>';
  $$('#event-list .switch').forEach((sw) => sw.addEventListener('click', async () => {
    const next = !sw.classList.contains('on');
    await api(`/api/events/${sw.dataset.id}`, { method: 'POST', body: JSON.stringify({ active: next }) });
    sw.classList.toggle('on', next);
  }));
}

function loadTab(t) {
  if (t === 'players') loadPlayers().catch(console.error);
  if (t === 'economy') loadEconomy().catch(console.error);
  if (t === 'bosses') loadBosses().catch(console.error);
  if (t === 'territories') loadTerritories().catch(console.error);
  if (t === 'events') loadEvents().catch(console.error);
  if (t === 'server') loadServer().catch(console.error);
}
async function refreshAll() {
  await loadHealth();
  try { await loadOverview(); } catch (e) { console.error(e); }
  const active = document.querySelector('.sidebar button.active').dataset.tab;
  loadTab(active);
}
refreshAll();
setInterval(() => loadOverview().catch(() => {}), 20000);
