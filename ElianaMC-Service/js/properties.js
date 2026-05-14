// ===== js/properties.js =====

let originalProps = {};
let currentProps  = {};
let serverType    = 'java';

// ── Java fields ───────────────────────────────────
const JAVA_FIELDS = {
  basic: [
    { key: 'motd',          label: 'Server MOTD',     type: 'text',   desc: 'Message shown in server list' },
    { key: 'max-players',   label: 'Max Players',     type: 'number', desc: 'Maximum players allowed' },
    { key: 'gamemode',      label: 'Gamemode',        type: 'select', options: ['survival','creative','adventure','spectator'], desc: 'Default gamemode' },
    { key: 'difficulty',    label: 'Difficulty',      type: 'select', options: ['peaceful','easy','normal','hard'], desc: 'World difficulty' },
    { key: 'pvp',           label: 'PvP',             type: 'toggle', desc: 'Player vs Player combat' },
    { key: 'online-mode',   label: 'Online Mode',     type: 'toggle', desc: 'Authenticate with Mojang' },
    { key: 'white-list',    label: 'Whitelist',       type: 'toggle', desc: 'Only allow whitelisted players' },
    { key: 'hardcore',      label: 'Hardcore',        type: 'toggle', desc: 'Hardcore mode' },
    { key: 'allow-flight',  label: 'Allow Flight',    type: 'toggle', desc: 'Allow flying in survival' },
  ],
  world: [
    { key: 'level-name',          label: 'World Name',       type: 'text',   desc: 'Name of the world folder' },
    { key: 'level-seed',          label: 'World Seed',       type: 'text',   desc: 'Seed for world generation' },
    { key: 'level-type',          label: 'World Type',       type: 'select', options: ['minecraft:normal','minecraft:flat','minecraft:large_biomes','minecraft:amplified'], desc: 'Type of world generation' },
    { key: 'generate-structures', label: 'Generate Structures', type: 'toggle', desc: 'Generate villages, dungeons etc' },
    { key: 'allow-nether',        label: 'Allow Nether',     type: 'toggle', desc: 'Enable nether dimension' },
    { key: 'spawn-monsters',      label: 'Spawn Monsters',   type: 'toggle', desc: 'Monsters spawn at night' },
    { key: 'spawn-protection',    label: 'Spawn Protection', type: 'number', desc: 'Radius of spawn protection' },
    { key: 'view-distance',       label: 'View Distance',    type: 'number', desc: 'Chunks sent to players' },
    { key: 'simulation-distance', label: 'Sim Distance',     type: 'number', desc: 'Chunks simulated around players' },
  ],
  network: [
    { key: 'server-port',                  label: 'Server Port',       type: 'number', desc: 'Port server listens on' },
    { key: 'server-ip',                    label: 'Server IP',         type: 'text',   desc: 'IP to bind (blank = all)' },
    { key: 'network-compression-threshold',label: 'Compression',       type: 'number', desc: 'Packet compression threshold' },
    { key: 'prevent-proxy-connections',    label: 'Block Proxies',     type: 'toggle', desc: 'Block VPN/proxy connections' },
    { key: 'enable-rcon',                  label: 'Enable RCON',       type: 'toggle', desc: 'Remote console access' },
    { key: 'rcon.port',                    label: 'RCON Port',         type: 'number', desc: 'RCON port' },
    { key: 'rcon.password',                label: 'RCON Password',     type: 'text',   desc: 'RCON password' },
    { key: 'enable-query',                 label: 'Enable Query',      type: 'toggle', desc: 'GameSpy4 query protocol' },
  ],
  advanced: [
    { key: 'max-tick-time',               label: 'Max Tick Time',      type: 'number', desc: 'Max ms per tick (-1 = off)' },
    { key: 'max-world-size',              label: 'Max World Size',     type: 'number', desc: 'Max world radius in blocks' },
    { key: 'enable-command-block',        label: 'Command Blocks',     type: 'toggle', desc: 'Enable command blocks' },
    { key: 'force-gamemode',              label: 'Force Gamemode',     type: 'toggle', desc: 'Force gamemode on join' },
    { key: 'op-permission-level',         label: 'OP Level',           type: 'select', options: ['1','2','3','4'], desc: 'Operator permission level' },
    { key: 'player-idle-timeout',         label: 'Idle Timeout',       type: 'number', desc: 'Kick idle players after X mins' },
    { key: 'broadcast-console-to-ops',    label: 'Broadcast Console',  type: 'toggle', desc: 'Send console to ops' },
    { key: 'sync-chunk-writes',           label: 'Sync Chunk Writes',  type: 'toggle', desc: 'Sync chunk writing to disk' },
  ]
};

// ── Bedrock fields ────────────────────────────────
const BEDROCK_FIELDS = {
  basic: [
    { key: 'server-name',   label: 'Server Name',  type: 'text',   desc: 'Name shown in server list' },
    { key: 'max-players',   label: 'Max Players',  type: 'number', desc: 'Maximum players allowed' },
    { key: 'gamemode',      label: 'Gamemode',     type: 'select', options: ['survival','creative','adventure'], desc: 'Default gamemode' },
    { key: 'difficulty',    label: 'Difficulty',   type: 'select', options: ['peaceful','easy','normal','hard'], desc: 'World difficulty' },
    { key: 'online-mode',   label: 'Xbox Live',    type: 'toggle', desc: 'Require Xbox Live auth' },
    { key: 'allow-list',    label: 'Allow List',   type: 'toggle', desc: 'Only allow listed players' },
    { key: 'allow-cheats',  label: 'Allow Cheats', type: 'toggle', desc: 'Enable cheat commands' },
    { key: 'force-gamemode',label: 'Force Gamemode',type: 'toggle',desc: 'Force gamemode on join' },
  ],
  world: [
    { key: 'level-name',         label: 'World Name',    type: 'text',   desc: 'Name of the world' },
    { key: 'level-seed',         label: 'World Seed',    type: 'text',   desc: 'Seed for world generation' },
    { key: 'view-distance',      label: 'View Distance', type: 'number', desc: 'Max chunks sent to player' },
    { key: 'tick-distance',      label: 'Tick Distance', type: 'number', desc: 'Chunks ticked around player' },
    { key: 'default-player-permission-level', label: 'Default Permission', type: 'select', options: ['visitor','member','operator'], desc: 'Permission for new players' },
    { key: 'texturepack-required',label: 'Force Texture Pack', type: 'toggle', desc: 'Force texture pack on clients' },
  ],
  network: [
    { key: 'server-port',          label: 'IPv4 Port',    type: 'number', desc: 'UDP port for IPv4' },
    { key: 'server-portv6',        label: 'IPv6 Port',    type: 'number', desc: 'UDP port for IPv6' },
    { key: 'enable-lan-visibility',label: 'LAN Visible',  type: 'toggle', desc: 'Show on LAN server list' },
    { key: 'player-idle-timeout',  label: 'Idle Timeout', type: 'number', desc: 'Kick idle players (mins)' },
    { key: 'max-threads',          label: 'Max Threads',  type: 'number', desc: 'Max server threads' },
    { key: 'compression-algorithm',label: 'Compression',  type: 'select', options: ['zlib','snappy'], desc: 'Network compression algorithm' },
  ],
  advanced: [
    { key: 'content-log-file-enabled',    label: 'Content Log File',    type: 'toggle', desc: 'Log content errors to file' },
    { key: 'content-log-console-output-enabled', label: 'Content Log Console', type: 'toggle', desc: 'Log content errors to console' },
    { key: 'disable-custom-skins',        label: 'Disable Custom Skins',type: 'toggle', desc: 'Block custom player skins' },
    { key: 'chat-restriction',            label: 'Chat Restriction',    type: 'select', options: ['None','Dropped','Disabled'], desc: 'Chat restriction level' },
    { key: 'disable-player-interaction',  label: 'No Player Interaction',type: 'toggle',desc: 'Players ignore each other' },
    { key: 'client-side-chunk-generation-enabled', label: 'Client Chunks', type: 'toggle', desc: 'Client generates visual chunks' },
  ]
};

// ── Init ──────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  serverType = localStorage.getItem('eliana-server') || 'java';
  console.log('Server type:', serverType);
  document.getElementById('props-sub').textContent =
    serverType === 'java' ? '☕ Java — SeraphinaMC' : '🪨 Bedrock — LuciaMC';
  loadProps();
});

// ── Load props ────────────────────────────────────
async function loadProps() {
  try {
    const res  = await fetch(`http://localhost:8007/properties?type=${serverType}`, {mode: 'cors'});
    const data = await res.json();
    originalProps = { ...data.properties };
    currentProps  = { ...data.properties };
    renderAll();
  } catch {
    document.getElementById('props-sub').textContent = '❌ Could not load — is backend running?';
  }
}

// ── Render all tabs ───────────────────────────────
function renderAll() {
  const fields = serverType === 'java' ? JAVA_FIELDS : BEDROCK_FIELDS;
  ['basic','world','network','advanced'].forEach(tab => {
    const grid = document.getElementById(`grid-${tab}`);
    grid.innerHTML = '';
    (fields[tab] || []).forEach(f => grid.appendChild(makeCard(f)));
  });
}

// ── Make card ─────────────────────────────────────
function makeCard(field) {
  const card = document.createElement('div');
  card.className = 'prop-card';
  card.id = `card-${field.key}`;

  const val = currentProps[field.key] ?? '';

  card.innerHTML = `
    <div class="prop-label">
      ${field.label}
      <span class="modified-badge">MODIFIED</span>
    </div>
    ${field.desc ? `<div class="prop-desc">${field.desc}</div>` : ''}
    <div id="input-wrap-${field.key}"></div>
  `;

  const wrap = card.querySelector(`#input-wrap-${field.key}`);
  wrap.appendChild(makeInput(field, val));
  return card;
}

// ── Make input ────────────────────────────────────
function makeInput(field, val) {
  if (field.type === 'toggle') {
    const isOn = val === 'true';
    const div  = document.createElement('div');
    div.className = 'prop-toggle';
    div.innerHTML = `
      <div class="toggle-track ${isOn ? 'on' : ''}" id="track-${field.key}">
        <div class="toggle-thumb"></div>
      </div>
      <span class="toggle-label">${isOn ? 'ENABLED' : 'DISABLED'}</span>
    `;
    div.onclick = () => toggleProp(field.key);
    return div;
  }

  if (field.type === 'select') {
    const sel = document.createElement('select');
    sel.className = 'prop-select';
    sel.id = `input-${field.key}`;
    field.options.forEach(opt => {
      const o = document.createElement('option');
      o.value = opt; o.textContent = opt;
      if (opt === val) o.selected = true;
      sel.appendChild(o);
    });
    sel.onchange = () => updateProp(field.key, sel.value);
    return sel;
  }

  const inp = document.createElement('input');
  inp.className = 'prop-input';
  inp.id = `input-${field.key}`;
  inp.type = field.type === 'number' ? 'number' : 'text';
  inp.value = val;
  inp.oninput = () => updateProp(field.key, inp.value);
  return inp;
}

// ── Toggle ────────────────────────────────────────
function toggleProp(key) {
  const track = document.getElementById(`track-${key}`);
  const label = track.nextElementSibling;
  const isOn  = track.classList.contains('on');
  track.classList.toggle('on');
  label.textContent = isOn ? 'DISABLED' : 'ENABLED';
  updateProp(key, isOn ? 'false' : 'true');
}

// ── Update prop ───────────────────────────────────
function updateProp(key, value) {
  currentProps[key] = value;
  const card = document.getElementById(`card-${key}`);
  const inp  = document.getElementById(`input-${key}`);
  const changed = value !== originalProps[key];
  card?.classList.toggle('modified', changed);
  inp?.classList.toggle('modified', changed);
  checkChanges();
}

// ── Check changes ─────────────────────────────────
function checkChanges() {
  const hasChanges = Object.keys(currentProps).some(
    k => currentProps[k] !== originalProps[k]
  );
  document.getElementById('save-banner').classList.toggle('show', hasChanges);
}

// ── Save ──────────────────────────────────────────
async function saveProps() {
  try {
    const res = await fetch('http://localhost:8007/properties', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: serverType, properties: currentProps })
    });
    const data = await res.json();
    if (data.success) {
      originalProps = { ...currentProps };
      document.querySelectorAll('.prop-card').forEach(c => c.classList.remove('modified'));
      document.querySelectorAll('.prop-input,.prop-select').forEach(i => i.classList.remove('modified'));
      document.getElementById('save-banner').classList.remove('show');
      alert('✅ Saved! Restart server to apply changes.');
    }
  } catch {
    alert('❌ Save failed — is backend running?');
  }
}

// ── Reload ────────────────────────────────────────
async function reloadProps() {
  currentProps = { ...originalProps };
  renderAll();
  document.getElementById('save-banner').classList.remove('show');
}

// ── Switch tab ────────────────────────────────────
function switchTab(tab) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById(`tab-${tab}`).classList.add('active');
  document.getElementById(`content-${tab}`).classList.add('active');
}
