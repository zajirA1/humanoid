// Čas povelové trajektorie je nezávislý na rychlosti prohlížení.
const tempoData = JSON.parse($('h22TempoData').textContent);
const tempoMenu = $('h22Tempo');
const tempoNotice = $('h22TempoNotice');
let playSeconds = 0;

function tempoContext() {
  if (mode !== 'climb' || !r9IsActive()) return 'other';
  if (document.documentElement.dataset.ready !== 'true') return 'init';
  if (r14Rev !== tempoData.revize || r14View || r14Has()) return 'edit';
  if (r14Dh !== 0) return 'height';
  return 'nominal';
}
function currentSchedule() {
  if (tempoContext() !== 'nominal') return null;
  return tempoData[tempoMenu.value] || null;
}
function frameTime(frame, info, schedule) {
  return schedule ? schedule.casy_s[frame] : frame / info.hz;
}
function findFrame(seconds, info, schedule) {
  if (!schedule) return Math.min(info.frames - 1, Math.floor(seconds * info.hz + 1e-8));
  const times = schedule.casy_s;
  let lo = 0, hi = times.length - 1;
  while (lo < hi) {
    const m = Math.ceil((lo + hi) / 2);
    if (times[m] <= seconds + 1e-9) lo = m;
    else hi = m - 1;
  }
  return lo;
}
function updateTempoFields(info, schedule) {
  const c = tempoContext();
  $('h22TempoControls').hidden = c === 'other';
  if (c === 'other') return;
  updateObserved(schedule);
  tempoMenu.disabled = c === 'edit' || c === 'height';
  let message = '';
  if (c === 'edit') message = 'Úprava geometrie nebo archivní revize používá původní časování. Pro rychlý kontrolovaný profil obnov výchozí R16.';
  else if (c === 'height') message = 'Změněná výška používá původní časování. Rychlý profil je zobrazen pro nominální geometrii schodu 210 mm.';
  else if (schedule) message = schedule.popis_ui || (tempoMenu.value === 'cil_10_s' ? 'Zobrazení zadaných poloh experimentu. Dosažitelnost popisuje výsledek dynamické zkoušky.' : 'Časování ověřené v dynamické simulaci. Fyzická zkouška dosud neproběhla.');
  else message = 'Původní trajektorie a dynamické výsledky referenčního běhu.';
  if (tempoNotice.textContent !== message) tempoNotice.textContent = message;
}
for (const [key, label] of [['vybrany','Simulovaný přelez'], ['rychly_210','Rychlý pokus na 210 mm'], ['cil_10_s','Cíl 10 s'], ['reference','Původní přelez']]) {
  const schedule = tempoData[key];
  if (!schedule && key !== 'reference') continue;
  const seconds = schedule ? schedule.casy_s[schedule.casy_s.length - 1] : (tempoData.zdrojovy_cas_s ?? tempoData.puvodni_s);
  tempoMenu.add(new Option(label + ' · ' + fmt(seconds,1) + ' s', key));
}
tempoMenu.onchange = () => { stop(); render(); };
document.addEventListener('visibilitychange', () => { if (document.hidden && playing) stop(); });

function observedSample(plan, frame) {
  if (!plan?.zaznam?.length || $('h22Track').value !== 'measured') return null;
  const times=plan.zaznam, t=plan.casy_s[frame];
  let low=0, high=times.length-1;
  while (low<high) {
    const mid=Math.ceil((low+high)/2);
    if (times[mid].t<=t) low=mid;
    else high=mid-1;
  }
  return times[low];
}
function updateObserved(plan) {
  const control=$('h22TrackControls'), note=$('h22TrackNote');
  control.hidden=!plan?.zaznam?.length;
  const sample=observedSample(plan,idx);
  if (!sample) {note.textContent=plan?'Model zobrazuje povelové polohy.':'';return;}
  const t=plan.casy_s[idx], end=plan.zaznam[plan.zaznam.length-1].t;
  if (plan.pad_s!=null && t>end) note.textContent='Záznam skončil po ztrátě opory. Model zůstává v poslední zaznamenané poloze.';
  else if (plan.pad_s!=null && t>=plan.pad_s) note.textContent='Ztráta opory v simulaci · sleduješ zaznamenaný pohyb.';
  else note.textContent='Model zobrazuje zaznamenaný pohyb. Fáze, kontaktní plán a statické výpočty níže patří k zadaným povelům.';
}
$('h22Track').onchange=()=>{render();};
