"""python tools/qc/handcheck.py <timings.json> long|shorts [--no-frames]   (EP=episodes/<slug>, default 0004)
Handwriting QC at 4 fps on REAL narration timings (timings.json from the last preview).
Flags: (a) text revealing while no pen is on it, (b) two hands on screen, (c) stamps applied by a hand (code audit)."""
import sys, json, collections, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault('OPENROUTER_API_KEY', 'audit-offline')  # offline: only makes cache names match the CI renders
import numpy as np
from factory.config import load_config, ROOT
from factory.script import load_episode, image_prompts
from factory.images import ensure_images
from factory.archive import ensure_archive, ensure_clips
from factory.tts import make_voice
from factory.build import voice_beats, SAMPLE_RATE
from factory.render import build_plan, Overlay
import factory.draw as D, factory.shots as SH, factory.endscreen as ES
import factory.devices as DV, factory.evidence as EV, factory.props as PR
TJ = json.load(open(sys.argv[1]))
WHICH = sys.argv[2] if len(sys.argv) > 2 else 'long'
T = {b['id']: b for b in TJ['beats']}
ep = load_episode(os.environ.get('EP', 'episodes/0004-fake-sale'))
cfg = load_config(ep.get('config'))
cache = ROOT / '.cache' / 'images' / ep['slug']
images = ensure_images(cfg, image_prompts(ep), cache, True, lambda *a: None)
images.update(ensure_archive(ep, cfg, cache, lambda *a: None)); ensure_clips(ep, cache, lambda *a: None)
mus = ep.get('music') or {}
for b in ep['beats']:
    b['_music'] = b.get('music') or mus.get(b.get('section') or '', mus.get('_default'))
voice = make_voice(cfg, True, ep.get('voices'))
TXT = {b['text']: b for b in TJ['beats']}
def voiced(beats):
    out = []
    for b in beats:
        r = T.get(b['id']) if T.get(b['id'], {}).get('text') == b['text'] else TXT.get(b['text'])
        if r:
            out.append({'audio': np.zeros(int(r['voice'] * SAMPLE_RATE), np.float32), 'sr': SAMPLE_RATE, 'duration': r['voice'],
                        'words': [tuple(w) for w in r['words']], 'speaker': 'narrator'})
        else:
            out += voice_beats(voice, [b])
    return out
lookup = {b['id']: b for b in ep['beats']}
plans = []
if WHICH == 'long':
    vb = voiced(ep['beats'])
    import factory.build as FB
    plan = build_plan(ep['beats'], vb, images, cfg, (960, 540), 'long', lookup)
    tgt = float(cfg['video'].get('long_min_seconds', 0))
    if tgt and plan.total < tgt:
        extra = min(0.45, (tgt - plan.total) / len(ep['beats']) + 0.01)
        plan = build_plan(ep['beats'], vb, images, cfg, (960, 540), 'long', lookup, extra)
    plans.append(('long', plan))
else:
    for sh in ep['shorts']:
        if sh.get('hook'):
            sh['beats'][0]['on_screen'] = sh['hook']; sh['beats'][0]['_hook'] = True
        plans.append((sh['id'], build_plan(sh['beats'], voiced(sh['beats']), images, cfg, (540, 960), 'short', lookup)))
state = {'hands': 0, 'partial': 0}
orig_hand = D._hand
def counting_hand(kind, *a, **k):
    state['hands'] += 1
    state['kinds'] = state.get('kinds', []) + [kind]
    return orig_hand(kind, *a, **k)
D._hand = counting_hand
orig_dw = SH._draw_write
def dw(out, mark, p, W, H, red, cfg):
    if 0 < p < 1 and not mark.get('bg') and not (mark.get('font') == 'typewriter' and not mark.get('hand')):
        state['partial'] += 1
        if not mark.get('hand'):
            state['nohand'] = state.get('nohand', 0) + 1
    return orig_dw(out, mark, p, W, H, red, cfg)
SH._draw_write = dw
orig_at = ES.Writing.at
def wat(self, p):
    if 0 < p < 1:
        state['partial'] += 1
    return orig_at(self, p)
ES.Writing.at = wat
for name, plan in plans:
    ov = Overlay(cfg, plan)
    starts = sorted(plan.beat_starts.items(), key=lambda x: x[1])
    def beat_at(t):
        b = None
        for k, v in starts:
            if v <= t: b = k
        return b
    issues = collections.OrderedDict()
    t = 0.0
    while t < plan.total and '--no-frames' not in sys.argv:
        state.update(hands=0, partial=0, nohand=0, kinds=[])
        si = max(i for i, s in enumerate(plan.shots) if s.start <= t)
        sh = plan.shots[si]
        fr = np.ascontiguousarray(sh.frame(t - sh.start)).copy()
        ci = next((i for i, c in enumerate(plan.captions) if c.end > t), len(plan.captions))
        ki = next((i for i, c in enumerate(plan.cards) if c.end > t), len(plan.cards))
        bi = next((i for i, c in enumerate(plan.bubbles) if c.end > t), len(plan.bubbles))
        ov.apply(fr, t, ci, ki, bi)
        tag = None
        if state['hands'] > 1:
            tag = f"{state['hands']} hands {state['kinds']}"
        elif False:
            tag = f"{state['hands']} hands"
        elif state['partial'] > state['hands'] or state.get('nohand'):
            tag = f"text revealing with no pen ({state['partial']} partial, {state['hands']} hand)"
        if tag:
            issues.setdefault((beat_at(t), tag), []).append(round(t, 2))
        t += 0.25
    print(f'== {name}: {round(plan.total, 1)} s, {len(issues)} issue groups')
    for (b, tag), ts in issues.items():
        print(f'  {b}: {tag} at {ts[0]}–{ts[-1]} ({len(ts)} frames)')
print('== marks that do not finish inside their shot')
for name, plan in plans:
    for sh in plan.shots:
        ms = getattr(sh, 'marks', None) or getattr(sh, 'photo_marks', None) or []
        for m in ms:
            if float(m.get('at', 0)) + float(m.get('dur', 0.45)) > sh.duration - 0.1 and float(m.get('dur', .45)) > 0.05:
                print(' ', name, type(sh).__name__, round(sh.start, 1), m.get('type'), m.get('text', ''), round(m['at'], 2), round(sh.duration, 2))
        if hasattr(sh, 'tag_at') and sh.tag_at > sh.duration - 0.3:
            print(' ', name, 'mugshot stamp late', round(sh.start, 1), round(sh.tag_at, 2), round(sh.duration, 2))
        for w in getattr(sh, 'writes', []) or []:
            if w[3] + w[4] > sh.duration - 0.1:
                print(' ', name, 'casefile write late', round(sh.start, 1), round(w[3], 2), round(sh.duration, 2))
        if hasattr(sh, 'type_at'):
            for a, d in zip(sh.type_at, sh.type_dur):
                if a + d > sh.duration - 0.1:
                    print(' ', name, 'typing late', round(sh.start, 1), round(a, 2), round(d, 2), round(sh.duration, 2))
