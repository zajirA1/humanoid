"""Propojení přehrávače s ověřenými časy R16. Sestavení nad poslední stránkou R16."""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def replace_once(s, before, after):
    if s.count(before) != 1:
        raise ValueError(f"Nesouhlasí verze vstupní stránky: {before[:95]}")
    return s.replace(before, after, 1)


def build(source, timing):
    for key in ("vybrany", "rychly_210", "cil_10_s"):
        if key not in timing:
            continue
        times = timing[key]["casy_s"]
        if len(times) != 1141 or times[0] != 0 or any(b <= a for a, b in zip(times, times[1:])):
            raise ValueError(f"Neplatná časová osa {key}")
        if len(timing[key].get("moment", [])) != len(times) or any(
                len(m) != 22 for m in timing[key]["moment"]):
            raise ValueError(f"Neúplná řada momentů {key}")
        record = timing[key].get("zaznam", [])
        if not record or any(len(p["q"]) != 22 or len(p["rt"]) != 12 for p in record):
            raise ValueError(f"Neúplný dynamický záznam {key}")
        if any(b["t"] <= a["t"] for a,b in zip(record, record[1:])):
            raise ValueError(f"Záznam simulace nemá rostoucí čas {key}")
    data = json.dumps(timing, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("<", r"\u003c")
    s = replace_once(source, 'EMIL H22 / R16 · APLIKACE 0.8', 'EMIL H22 / R16 · APLIKACE 0.9.2')
    s = replace_once(s, '<div class="playbar"><button id="play"', '''<div id="h22TempoControls" hidden><label>Časování schodu <select id="h22Tempo"></select></label><label id="h22TrackControls" hidden>3D model <select id="h22Track"><option value="measured">Výsledek simulace</option><option value="planned">Povelové polohy</option></select></label><span id="h22TempoNotice"></span><span id="h22TrackNote"></span></div><div class="playbar"><button id="play"''')
    s = replace_once(s, '<select id="speed" aria-label="Rychlost přehrávání"><option value=".5">0,5×</option><option value="1" selected>1×</option><option value="2">2×</option></select>', '''<label class="h22-speed">Přehrávání <select id="speed" aria-label="Rychlost přehrávání"><option value=".1">0,1×</option><option value=".25">0,25×</option><option value=".5">0,5×</option><option value="1" selected>1×</option><option value="2">2×</option><option value="4">4×</option><option value="10">10×</option></select></label>''')
    s = replace_once(s, '</style></head>', '''</style><style>#h22TempoControls{display:flex;flex-wrap:wrap;gap:.5rem 1rem;align-items:baseline;margin:.65rem 0 .1rem}#h22TempoControls[hidden]{display:none}#h22TempoControls label,.h22-speed{font-weight:600}#h22TrackControls[hidden]{display:none}#h22TrackNote{display:block;flex-basis:100%;font-size:.85rem;color:#294c44}#h22TrackNote:empty{display:none}#h22TempoNotice{color:#475e54;font-size:.87rem;max-width:78ch}#h22ReportAnchor{display:inline-block;padding:.35em .5em;font-size:.9rem}#h22TempoReport{margin:1rem 0}.h22-speed{font-size:.85rem;white-space:nowrap}@media(max-width:600px){.playbar{flex-wrap:wrap}.playbar input{min-width:7em}.h22-speed{margin-left:auto}}</style></head>''')
    s = replace_once(s, 'let playRequest=0;', (HERE / 'prehravani.js').read_text() + '\nlet playRequest=0;')
    old = s.index(' function tick(t) {')
    end = s.index(";$('slider').oninput", old)
    s = s[:old] + """ function tick(t) {
   if (!playing) return;
   const motion = info(), schedule = currentSchedule();
   const end = frameTime(motion.frames - 1, motion, schedule);
   playSeconds = Math.min(end, playSeconds + Math.max(0, t - last) / 1000 * Number($('speed').value));
   last = t;
   const next = findFrame(playSeconds, motion, schedule);
   if (idx !== next) { idx = next; render(); }
   if (playSeconds >= end) stop();
   if (playing) playRequest = requestAnimationFrame(tick);
 }
 $('play').onclick = () => {
   if (playing) return stop();
   const motion = info();
   if (idx >= motion.frames - 1) idx = 0;
   playSeconds = frameTime(idx, motion, currentSchedule());
   last = performance.now(); playing = true; $('play').textContent = 'Pauza';
   render();
   if (playing) playRequest = requestAnimationFrame(tick);
 }""" + s[end:]
    s = replace_once(s, "let a=row(),o=info(),w=fk(a.q,a.rt),cmd=[]", "let a=row(),o=info(),observed=observedSample(currentSchedule(),idx),drawn=observed||a,w=fk(drawn.q,drawn.rt),cmd=[]")
    s = replace_once(s, "climbMarkers(a,project);", "climbMarkers(observed?{}:a,project);")
    s = replace_once(s, '<p class="r13-lead">R16 vychází z R15.', '<p class="r13-lead"><strong>Referenční rozbor konstrukce při původním přelezu za 190 s.</strong> Výsledek aktuálního časování a jeho dynamické meze jsou uvedené u přehrávače.</p><p class="r13-lead">R16 vychází z R15.')
    s = replace_once(s, "$('time').textContent=fmt(idx/o.hz,1)+' / '+fmt((o.frames-1)/o.hz,1)+' s';", """const plan=currentSchedule();updateTempoFields(o,plan);$('time').textContent=fmt(frameTime(idx,o,plan),1)+' / '+fmt(frameTime(o.frames-1,o,plan),1)+' s';""")
    s = replace_once(s, "if(r9IsActive()&&['climb','stairs'].includes(mode)&&load&&Object.hasOwn(load,'moving')){", """if(plan&&mode==='climb'){
   const values=plan.moment?.[idx], metric=$('metrics');
   if(values && Number.isFinite(values[side]))metric.innerHTML+=vk('Dynamický moment vybrané osy · nový přelez',fmt(Math.abs(values[side]),3)+' N·m');
   else metric.innerHTML+=vk('Dynamika zobrazeného tempa','viz výsledek zkoušky');
 } else if(r9IsActive()&&['climb','stairs'].includes(mode)&&load&&Object.hasOwn(load,'moving')){""")
    s = replace_once(s, "fetch('index.php?data=kondo',{credentials:'same-origin'})", "fetch(document.querySelector('meta[name=robot-api]')?'index.php?data=kondo':'kondo-data.json',{credentials:'same-origin'})")
    s = replace_once(s, "const rate=Number($('speed').value);", "const rate=1; // Zpomalení či zrychlení obrazu nemění identitu fyzikálního scénáře.")
    s = replace_once(s, '<script id="r8LoadsData"', '<script type="application/json" id="h22TempoData">'+data+'</script><script id="r8LoadsData"') if '<script id="r8LoadsData"' in s else replace_once(s,'</head>', '<script type="application/json" id="h22TempoData">'+data+'</script></head>')
    s = replace_once(s, "document.documentElement.dataset.ready='true';", """const originalReport=$('revR16'), workingArea=document.querySelector('main > .layout');
const tempoSettings=$('h22TempoControls'), playbar=$('play').closest('.playbar');
if(tempoSettings && playbar)playbar.after(tempoSettings);
if(originalReport && workingArea) {
  workingArea.after(originalReport);
  const jump=document.createElement('a');jump.href='#revR16';jump.id='h22ReportAnchor';jump.textContent='Zpráva o konstrukci R16';
  document.querySelector('main > header .row')?.append(jump);
}
document.documentElement.dataset.ready='true';render();""")
    return s


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('timing', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    args.destination.write_text(build(args.original.read_text(), json.loads(args.timing.read_text())))
