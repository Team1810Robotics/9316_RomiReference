'use strict';
const $ = id => document.getElementById(id);
let workspace;
let connected = false;
let transientUntil = 0;
const speeds = [['Slow (35%)','0.35'], ['Medium (45%)','0.45'], ['Fast (60%)','0.60']];
const specs = [
  ['forward', 'Drive forward for %1 seconds at %2', 145],
  ['backward', 'Drive backward for %1 seconds at %2', 145],
  ['left', 'Turn left for %1 seconds at %2', 220],
  ['right', 'Turn right for %1 seconds at %2', 220],
];

function initialize() {
  if (typeof Blockly === 'undefined') {
    $('status').textContent = 'Blockly is missing. On internet Wi-Fi, run: py -3.14 romi_blocks\\download_blockly.py';
    $('preview').textContent = 'Keep the existing vendor/blockly.min.js, or download it once.';
    return;
  }
  Blockly.defineBlocksWithJsonArray(specs.map(([direction, label, colour]) => ({
    type: 'romi_' + direction,
    message0: label,
    args0: [
      {type:'field_number', name:'SECONDS', value:0.6, min:0.1, max:2.5, precision:0.1},
      {type:'field_dropdown', name:'SPEED', options:speeds},
    ],
    previousStatement:null, nextStatement:null, colour,
    tooltip: 'Change how long and how strongly the Romi moves.', helpUrl:''
  })));

  workspace = Blockly.inject('blocklyDiv', {
    toolbox:{kind:'flyoutToolbox', contents:specs.map(([d])=>({kind:'block',type:'romi_'+d}))},
    trashcan:true, renderer:'zelos',
    grid:{spacing:20,length:2,colour:'#d6dfe9',snap:true},
    zoom:{controls:true,wheel:true,startScale:0.95,maxScale:1.6,minScale:0.55}
  });
  workspace.addChangeListener(updatePreview);
  $('run').addEventListener('click', runBlocks);
  $('stop').addEventListener('click', () => send('/api/stop', {}));
  $('example').addEventListener('click', loadExample);
  loadExample();
  setInterval(poll, 500);
  poll();
}

function loadExample() {
  workspace.clear();
  let previous = null;
  // Two forward blocks demonstrate the speed setting without changing their durations.
  for (const [direction, duration, speed] of [
    ['forward',0.6,'0.35'], ['right',0.4,'0.45'], ['forward',0.6,'0.60']
  ]) {
    const block = workspace.newBlock('romi_' + direction);
    block.setFieldValue(String(duration), 'SECONDS');
    block.setFieldValue(speed, 'SPEED');
    block.initSvg(); block.render();
    if (previous) previous.nextConnection.connect(block.previousConnection);
    else block.moveBy(32, 55);
    previous = block;
  }
  Blockly.svgResize(workspace);
  updatePreview();
}

function program() {
  const tops = workspace.getTopBlocks(true).filter(b => !b.isShadow());
  if (tops.length !== 1) throw new Error('Connect all blocks into one vertical stack.');
  const totalBlocks = workspace.getAllBlocks(false).filter(b => !b.isShadow()).length;
  if (totalBlocks < 1 || totalBlocks > 8) throw new Error('Use 1–8 movement blocks.');
  const steps = []; let total = 0;
  for (let b = tops[0]; b; b = b.getNextBlock()) {
    const direction = b.type.replace(/^romi_/, '');
    if (!['forward','backward','left','right'].includes(direction)) throw new Error('Unsupported block.');
    const seconds = Number(b.getFieldValue('SECONDS'));
    const speed = Number(b.getFieldValue('SPEED'));
    if (!Number.isFinite(seconds) || seconds < 0.1 || seconds > 2.5) throw new Error('Use 0.1–2.5 seconds per block.');
    if (!Number.isFinite(speed) || speed < 0.30 || speed > 0.60) throw new Error('Choose a valid speed.');
    total += seconds;
    steps.push({direction, seconds, speed});
  }
  if (steps.length !== totalBlocks) throw new Error('Some blocks are not connected.');
  if (total > 8.00001) throw new Error('Program must be 8 seconds or less.');
  return {
    steps, total,
    sequence:steps.map(x => `${x.direction}:${x.seconds.toFixed(2)}:${x.speed.toFixed(2)}`).join(',')
  };
}

function updatePreview() {
  if (!workspace) return;
  try {
    const p = program();
    $('preview').textContent = p.steps.map((s,i) =>
      `${i+1}. ${s.direction[0].toUpperCase()+s.direction.slice(1)} · ${s.seconds.toFixed(1)} sec · ${Math.round(s.speed*100)}%`
    ).join('\n') + `\nTotal: ${p.total.toFixed(1)} sec`;
    $('run').disabled = !connected;
  } catch (e) {
    $('preview').textContent = e.message;
    $('run').disabled = true;
  }
}

async function send(path, payload) {
  try {
    const response = await fetch(path, {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Request failed');
    transientUntil = Date.now() + 1400;
    $('status').textContent = result.message;
    $('status').classList.remove('error');
  } catch(e) {
    transientUntil = Date.now() + 4500;
    $('status').textContent = 'Error: ' + e.message;
    $('status').classList.add('error');
  }
}

function runBlocks() {
  try { send('/api/run', {sequence:program().sequence}); }
  catch (e) { $('status').textContent = e.message; }
}

function renderSensors(s) {
  const available = connected && s && s.available && s.ageMs < 2500;
  $('sensorState').textContent = available ? 'Live' : 'Waiting for Romi sensor data';
  const value = (x, n=1) => available && Number.isFinite(x) ? x.toFixed(n) : '—';
  $('gyro').textContent = value(s?.gyroZDeg) + (available ? '°' : '');
  $('leftWheel').textContent = value(s?.leftIn) + (available ? ' in' : '');
  $('rightWheel').textContent = value(s?.rightIn) + (available ? ' in' : '');
  for (const letter of ['A','B','C']) {
    const el = $('button'+letter);
    el.textContent = letter + ': ' + (available ? (s['button'+letter] ? 'Pressed' : 'Released') : '—');
    el.classList.toggle('pressed', available && !!s['button'+letter]);
  }
}

async function poll() {
  try {
    const response = await fetch('/api/status', {cache:'no-store'});
    if (!response.ok) throw new Error('Bridge unavailable');
    const data = await response.json();
    connected = !!data.connected;
    $('connection').classList.toggle('connected', connected);
    $('connectionText').textContent = connected ? 'NetworkTables connected (localhost)' : 'Waiting for WPILib simulation';
    $('stop').disabled = !connected;
    if (Date.now() > transientUntil) {
      $('status').classList.remove('error');
      $('status').textContent = connected ? data.status : 'NetworkTables not connected. Start WPILib simulation.';
    }
    renderSensors(data.sensors);
    updatePreview();
  } catch(e) {
    connected = false;
    $('connection').classList.remove('connected');
    $('connectionText').textContent = 'Local bridge unavailable';
    $('run').disabled = true; $('stop').disabled = true;
    $('status').textContent = e.message;
    renderSensors(null);
  }
}
window.addEventListener('DOMContentLoaded', initialize);
