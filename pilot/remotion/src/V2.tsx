// CoinSense Ep.4 v2 "The Seven-Minute Heist": the Remotion layer for the preview (cold open + Act 1, 16:9) and the
// 9:16 cold-open sample. Plan and timing come from tools/v2_preview.py (scene list + the fable voice's timings.json).
// Every number, price, label and button is code-drawn here (no text in any picture). Motion is per-frame float math.
import React, {useEffect, useState} from 'react';
import {AbsoluteFill, Easing, Img, OffthreadVideo, Sequence, continueRender, delayRender, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {evolvePath} from '@remotion/paths';
import {noise2D} from '@remotion/noise';
import {fitText, measureText} from '@remotion/layout-utils';

const C = {night: '#0E1A2B', night2: '#16263D', glow: '#9FD8FF', paper: '#F3E9D2', paper2: '#E6D8B9', ink: '#1E1B18', red: '#D2452F', accent: '#E8B53A', green: '#2E6B4F', mute: '#6E6A62'};
const HEAD = 'Anton-Regular';
const BODY = 'ArchivoBlack-Regular';
const TYPE = 'SpecialElite-Regular';
const SERIF = 'PT-Serif-Web-Regular';
const fam = (f: string) => `'${f}'`;
const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));
const sm = (p: number) => {
	const q = clamp(p, 0, 1);
	return q * q * (3 - 2 * q);
};
const io = Easing.inOut(Easing.cubic);
const WIPE = 18;

const useFontsReady = (fonts: Record<string, string>) => {
	const [handle] = useState(() => delayRender('v2 fonts'));
	const [ready, setReady] = useState(false);
	useEffect(() => {
		Promise.all(
			Object.entries(fonts).map(([file, family]) =>
				new FontFace(family, `url(${staticFile('fonts/' + file)})`).load().then((f) => (document.fonts as any).add(f)).catch(() => null)
			)
		).then(() => {
			setReady(true);
			continueRender(handle);
		});
	}, []);
	return ready;
};

type P = {s: any; t: number; dur: number; SW: number; SH: number; u: number; fps: number};

// ------------------------------------------------------------------ stamps (drop in from above: 110 % -> 100 % in 0.2 s)
const Stamp: React.FC<{text: string; at: number; t: number; x: number; y: number; size: number; color?: string; rot?: number}> = ({text, at, t, x, y, size, color = C.red, rot = -8}) => {
	if (t < at) return null;
	const k = clamp((t - at) / 0.2, 0, 1);
	const sc = 1.1 - 0.1 * Easing.out(Easing.quad)(k);
	return (
		<div style={{position: 'absolute', left: x, top: y, transform: `translate(-50%,-50%) rotate(${rot}deg) scale(${sc})`, opacity: clamp(k * 3, 0, 1),
			border: `${Math.max(3, size * 0.09)}px solid ${color}`, color, fontFamily: fam(HEAD), fontSize: size, lineHeight: 1, padding: `${size * 0.14}px ${size * 0.3}px`,
			letterSpacing: size * 0.04, borderRadius: size * 0.08, whiteSpace: 'nowrap', mixBlendMode: 'normal', textShadow: 'none'}}>
			{text}
		</div>
	);
};

// a stroke that draws itself along its path (true stroke, @remotion/paths)
const Stroke: React.FC<{d: string; t0: number; dur: number; t: number; w: number; color?: string; W: number; H: number}> = ({d, t0, dur, t, w, color = C.red, W, H}) => {
	const p = clamp((t - t0) / dur, 0, 1);
	if (p <= 0) return null;
	const ev = evolvePath(io(p), d);
	return (
		<svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
			<path d={d} fill="none" stroke={color} strokeWidth={w} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={ev.strokeDasharray} strokeDashoffset={ev.strokeDashoffset} />
		</svg>
	);
};

// ------------------------------------------------------------------ backgrounds: act palette with a slow push (no frame is static)
const NightBg: React.FC<{t: number; dur: number; SW: number; SH: number; glow?: boolean}> = ({t, dur, SW, SH, glow = true}) => {
	const sc = 1.02 + 0.05 * (t / Math.max(dur, 0.1));
	return (
		<AbsoluteFill style={{background: C.night, overflow: 'hidden'}}>
			<AbsoluteFill style={{transform: `scale(${sc})`, background: `radial-gradient(ellipse at 50% 42%, ${glow ? '#21406A' : C.night2} 0%, ${C.night2} 38%, ${C.night} 78%)`}} />
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ the browser window (code-drawn checkout)
const Win: React.FC<{u: number; SW: number; SH: number; tabs?: {label: string; dot: string; on: number; closing?: number}[]; active?: number; t: number; children: React.ReactNode; scale?: number}> = ({u, SW, SH, tabs = [{label: 'Concert tickets', dot: C.green, on: -1}], active = 0, t, children, scale = 1}) => {
	const w = 1240 * u,
		h = 700 * u;
	const x = (SW - w) / 2,
		y = (SH - h) / 2 - 50 * u;
	const bar = 58 * u;
	return (
		<div style={{position: 'absolute', left: x, top: y, width: w, height: h, transform: `scale(${scale})`, transformOrigin: '50% 50%', borderRadius: 22 * u, background: C.paper,
			boxShadow: `0 0 ${120 * u}px ${30 * u}px rgba(159,216,255,0.28), 0 ${18 * u}px ${50 * u}px rgba(0,0,0,0.55)`, overflow: 'hidden', border: `${3 * u}px solid ${C.ink}`}}>
			<div style={{position: 'absolute', left: 0, top: 0, width: w, height: bar, background: C.paper2, borderBottom: `${3 * u}px solid ${C.ink}`}}>
				{[0, 1, 2].map((i) => (
					<div key={i} style={{position: 'absolute', left: (22 + i * 26) * u, top: bar / 2 - 8 * u, width: 16 * u, height: 16 * u, borderRadius: 8 * u, background: [C.red, C.accent, C.green][i], border: `${2 * u}px solid ${C.ink}`}} />
				))}
				{tabs.map((tb, i) => {
					const inK = tb.on < 0 ? 1 : sm((t - tb.on) / 0.3);
					const outK = tb.closing === undefined ? 0 : sm((t - tb.closing) / 0.35);
					const tw = 300 * u * (1 - outK);
					const left = (112 + tabs.slice(0, i).reduce((a, b) => a + 312 * (b.closing === undefined ? 1 : 1 - sm((t - (b.closing as number)) / 0.35)), 0)) * u;
					if (inK <= 0 || tw < 4) return null;
					return (
						<div key={i} style={{position: 'absolute', left, top: 10 * u + (1 - inK) * 30 * u, width: tw, height: bar - 10 * u, opacity: inK, background: i === active ? C.paper : '#D8C8A6',
							borderRadius: `${12 * u}px ${12 * u}px 0 0`, border: `${3 * u}px solid ${C.ink}`, borderBottom: 'none', overflow: 'hidden', display: 'flex', alignItems: 'center'}}>
							<div style={{marginLeft: 14 * u, width: 14 * u, height: 14 * u, borderRadius: 3 * u, background: tb.dot, flex: 'none'}} />
							<div style={{marginLeft: 10 * u, fontFamily: fam(BODY), fontSize: 19 * u, color: C.ink, whiteSpace: 'nowrap'}}>{tb.label}</div>
						</div>
					);
				})}
			</div>
			<div style={{position: 'absolute', left: 0, top: bar, width: w, height: h - bar, overflow: 'hidden'}}>{children}</div>
		</div>
	);
};
const winBox = (u: number, SW: number, SH: number) => {
	const w = 1240 * u,
		h = 700 * u;
	return {w, h: h - 58 * u, x: (SW - w) / 2, y: (SH - h) / 2 - 50 * u + 58 * u};
};

const Field: React.FC<{u: number; x: number; y: number; w: number; label: string; value: string; p: number}> = ({u, x, y, w, label, value, p}) => {
	const shown = value.slice(0, Math.round(value.length * clamp(p, 0, 1)));
	return (
		<div style={{position: 'absolute', left: x, top: y, width: w}}>
			<div style={{fontFamily: fam(BODY), fontSize: 18 * u, color: C.mute, letterSpacing: 1.5 * u}}>{label}</div>
			<div style={{marginTop: 6 * u, height: 54 * u, border: `${3 * u}px solid ${C.ink}`, borderRadius: 8 * u, background: '#FBF6EA', display: 'flex', alignItems: 'center', paddingLeft: 16 * u,
				fontFamily: fam(TYPE), fontSize: 30 * u, color: C.ink, whiteSpace: 'pre'}}>
				{shown}
				{p > 0 && p < 1 ? <span style={{display: 'inline-block', width: 3 * u, height: 32 * u, background: C.ink, marginLeft: 2 * u}} /> : null}
			</div>
		</div>
	);
};

const Button: React.FC<{u: number; x: number; y: number; w: number; label: string; lit?: number; press?: number; t: number; color?: string}> = ({u, x, y, w, label, lit, press, t, color = C.green}) => {
	const l = lit === undefined ? 1 : sm((t - lit) / 0.25);
	const pr = press === undefined || t < press ? 0 : Math.sin(clamp((t - press) / 0.22, 0, 1) * Math.PI);
	return (
		<div style={{position: 'absolute', left: x, top: y, width: w, height: 70 * u, borderRadius: 12 * u, border: `${3 * u}px solid ${C.ink}`, background: l > 0.5 ? color : '#BDB3A0',
			color: C.paper, fontFamily: fam(HEAD), fontSize: 36 * u, letterSpacing: 2 * u, display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${1 - 0.06 * pr})`,
			boxShadow: l > 0.5 ? `0 0 ${30 * u * l}px rgba(232,181,58,${0.6 * l})` : 'none'}}>
			{label}
		</div>
	);
};

// one page of the checkout, drawn inside the window
const Page: React.FC<{kind: string; u: number; w: number; h: number; t: number; s: any; seatK?: number}> = ({kind, u, w, h, t, s, seatK = 0}) => {
	if (kind === 'list')
		return (
			<AbsoluteFill style={{padding: 40 * u}}>
				<div style={{fontFamily: fam(BODY), fontSize: 26 * u, color: C.mute}}>SATURDAY · 8 PM · THE CONCERT HALL</div>
				{['$30', '$34', '$39'].map((p, i) => (
					<div key={i} style={{marginTop: 22 * u, height: 92 * u, border: `${3 * u}px solid ${C.ink}`, borderRadius: 10 * u, background: i === 0 ? '#FFF3CF' : '#FBF6EA', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: `0 ${30 * u}px`}}>
						<div style={{fontFamily: fam(BODY), fontSize: 28 * u, color: C.ink}}>{['STALLS', 'CIRCLE', 'FRONT ROWS'][i]}</div>
						<div style={{fontFamily: fam(HEAD), fontSize: 56 * u, color: i === 0 ? C.red : C.ink}}>{p}</div>
					</div>
				))}
			</AbsoluteFill>
		);
	if (kind === 'seat' || kind === 'tabs_seat') return <SeatMap u={u} w={w} h={h} t={t} s={s} k={seatK} />;
	if (kind === 'form' || kind === 'tabs_form') {
		const p = s.fillP ?? 1;
		return (
			<AbsoluteFill>
				<Field u={u} x={60 * u} y={40 * u} w={w - 120 * u} label="NAME" value="LARRY" p={s.f0 ?? clamp(p * 3, 0, 1)} />
				<Field u={u} x={60 * u} y={160 * u} w={w - 120 * u} label="EMAIL" value="••••••••@•••••.•••" p={s.f1 ?? clamp(p * 3 - 1, 0, 1)} />
				<Field u={u} x={60 * u} y={280 * u} w={w - 120 * u} label="CARD NUMBER" value="•••• •••• •••• ••••" p={s.f2 ?? clamp(p * 3 - 2, 0, 1)} />
				<div style={{position: 'absolute', left: 60 * u, top: 420 * u, width: 40 * u, height: 40 * u, border: `${3 * u}px solid ${C.ink}`, borderRadius: 6 * u, background: '#FBF6EA'}} />
				{s.tick !== undefined ? <Stroke d={`M ${70 * u} ${440 * u} L ${82 * u} ${453 * u} L ${104 * u} ${420 * u}`} t0={s.tick} dur={0.25} t={t} w={6 * u} color={C.green} W={w} H={h} /> : null}
				<div style={{position: 'absolute', left: 116 * u, top: 424 * u, fontFamily: fam(BODY), fontSize: 24 * u, color: C.ink}}>I agree to the terms</div>
				{s.thanks !== undefined ? <Button u={u} x={w - 420 * u} y={h - 120 * u} w={360 * u} label="THANK YOU!" lit={s.thanks - 0.4} press={s.thanks} t={t} /> : null}
			</AbsoluteFill>
		);
	}
	return null;
};

const SeatMap: React.FC<{u: number; w: number; h: number; t: number; s: any; k: number}> = ({u, w, h, t, s, k}) => {
	const rows = 'ABCDEFGHIJKL'.split('');
	const cols = 16;
	const cw = 52 * u,
		ch = 34 * u;
	const gx = (w - cols * cw) / 2 + 20 * u,
		gy = 70 * u;
	const tr = 6,
		tc = 11; // G12
	const tx = gx + tc * cw + cw / 2,
		ty = gy + tr * ch + ch / 2;
	const z = 1 + 1.5 * k;
	const lit = s.light_ !== undefined && t >= s.light_ ? sm((t - s.light_) / 0.2) : 0;
	return (
		<AbsoluteFill style={{overflow: 'hidden'}}>
			<div style={{position: 'absolute', left: 0, top: 0, width: w, height: h, transform: `translate(${(w / 2 - tx) * k}px, ${(h / 2 - ty) * k}px) scale(${z})`, transformOrigin: `${tx}px ${ty}px`}}>
				<div style={{position: 'absolute', left: gx, top: 18 * u, width: cols * cw, height: 34 * u, background: C.ink, borderRadius: 6 * u, color: C.paper, fontFamily: fam(BODY), fontSize: 20 * u, textAlign: 'center', lineHeight: `${34 * u}px`}}>STAGE</div>
				{rows.map((r, ri) => (
					<React.Fragment key={r}>
						<div style={{position: 'absolute', left: gx - 40 * u, top: gy + ri * ch, width: 30 * u, height: ch, fontFamily: fam(BODY), fontSize: 18 * u, color: C.mute, lineHeight: `${ch}px`, textAlign: 'right'}}>{r}</div>
						{Array.from({length: cols}).map((_, ci) => {
							const me = ri === tr && ci === tc;
							const taken = (ri * 7 + ci * 3) % 5 === 0 && !me;
							return (
								<div key={ci} style={{position: 'absolute', left: gx + ci * cw + 5 * u, top: gy + ri * ch + 4 * u, width: cw - 10 * u, height: ch - 8 * u, borderRadius: `${8 * u}px ${8 * u}px ${3 * u}px ${3 * u}px`,
									background: me ? (lit > 0 ? C.accent : '#E9D9B6') : taken ? '#9C9384' : '#E9D9B6', border: `${2 * u}px solid ${C.ink}`, boxShadow: me && lit > 0 ? `0 0 ${18 * u * lit}px ${C.accent}` : 'none'}} />
							);
						})}
					</React.Fragment>
				))}
			</div>
			{lit > 0 ? (
				<div style={{position: 'absolute', left: w / 2 + 60 * u, top: h / 2 - 90 * u, opacity: lit, background: C.ink, color: C.paper, fontFamily: fam(BODY), fontSize: 26 * u, padding: `${8 * u}px ${16 * u}px`, borderRadius: 8 * u}}>ROW G · SEAT 12</div>
			) : null}
		</AbsoluteFill>
	);
};

const mmss = (sec: number) => `${Math.floor(sec / 60)}:${String(Math.floor(sec % 60)).padStart(2, '0')}`;

const ScreenView: React.FC<P> = ({s, t, dur, SW, SH, u}) => {
	const B = winBox(u, SW, SH);
	const push = 1 + 0.025 * (t / Math.max(dur, 0.1));
	let tabs: any[] | undefined;
	let active = 0;
	let body: React.ReactNode = null;
	if (s.mode === 'form') {
		let st: any = {};
		if (Array.isArray(s.fill)) st = {fillP: interpolate(t / dur, [0, 1], s.fill, {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})};
		if (s.fillat_) {
			// fields fill as each is read
			const [a, b, c] = s.fillat_;
			st = {f0: sm((t - a) / 0.5), f1: sm((t - b) / 0.6), f2: s.digits_ !== undefined ? sm((t - s.digits_) / 1.8) : sm((t - c) / 1.2)};
		}
		body = <Page kind="form" u={u} w={B.w} h={B.h} t={t} s={{...st, tick: s.tick_, thanks: s.thanks_}} />;
	} else if (s.mode === 'whip') {
		const pi = Math.max(0, s.page_.filter((x: number) => t >= x - 0.12).length - 1);
		const k = pi >= 0 ? sm((t - (s.page_[pi] - 0.12)) / 0.28) : 0;
		const pages = s.pages;
		const cur = Math.max(0, pi);
		const prev = Math.max(0, pi - 1);
		const off = (1 - k) * B.w;
		body = (
			<AbsoluteFill>
				{pi > 0 && k < 1 ? (
					<AbsoluteFill style={{transform: `translateX(${-k * B.w}px)`, filter: `blur(${10 * u * Math.sin(k * Math.PI)}px)`}}>
						<Page kind={pages[prev]} u={u} w={B.w} h={B.h} t={t} s={{fillP: 1}} seatK={0} />
					</AbsoluteFill>
				) : null}
				<AbsoluteFill style={{transform: `translateX(${pi > 0 ? off : 0}px)`, filter: pi > 0 ? `blur(${10 * u * Math.sin(k * Math.PI)}px)` : 'none', opacity: pi < 0 ? 0 : 1}}>
					<Page kind={pages[cur]} u={u} w={B.w} h={B.h} t={t} s={{fillP: pages[cur] === 'form' ? clamp((t - s.page_[cur]) / 1.4, 0, 1) : 1}} seatK={0} />
				</AbsoluteFill>
			</AbsoluteFill>
		);
	} else if (s.mode === 'total' || s.mode === 'pay') {
		const rows: [string, string][] = [['TICKET · ROW G, SEAT 12', '$30']];
		if (s.fees_shown) rows.push(['SERVICE FEE', '$8'], ['FACILITY FEE', '$6'], ['PROCESSING', '$4']);
		const tot = s.mode === 'pay' ? -1 : s.total_;
		body = (
			<AbsoluteFill style={{padding: `${34 * u}px ${60 * u}px`}}>
				<div style={{fontFamily: fam(BODY), fontSize: 24 * u, color: C.mute, letterSpacing: 1.5 * u}}>ORDER SUMMARY</div>
				{rows.map(([a, b], i) => (
					<div key={i} style={{display: 'flex', justifyContent: 'space-between', marginTop: 14 * u, fontFamily: fam(BODY), fontSize: 30 * u, color: C.ink, borderBottom: `${2 * u}px dashed ${C.mute}`, paddingBottom: 8 * u}}>
						<span>{a}</span>
						<span>{b}</span>
					</div>
				))}
				{(() => {
					const at = s.mode === 'pay' ? -1 : s.total_;
					if (at === undefined || t < at) return null;
					const k = clamp((t - at) / 0.2, 0, 1);
					return (
						<div style={{position: 'absolute', left: 60 * u, top: (s.fees_shown ? 300 : 150) * u, display: 'flex', alignItems: 'baseline', gap: 26 * u, transform: `scale(${1.1 - 0.1 * k})`, transformOrigin: '0% 50%'}}>
							<span style={{fontFamily: fam(BODY), fontSize: 38 * u, color: C.ink}}>TOTAL</span>
							<span style={{fontFamily: fam(HEAD), fontSize: 120 * u, color: C.red, lineHeight: 1}}>{s.mode === 'pay' ? '$48' : s.total}</span>
						</div>
					);
				})()}
				<Button u={u} x={B.w - 420 * u} y={B.h - 120 * u} w={360 * u} label="PAY" lit={s.mode === 'pay' ? -1 : s.pay_} press={s.press_} t={t} color={C.red} />
			</AbsoluteFill>
		);
	} else if (s.mode === 'tabs') {
		tabs = s.tabs.map((tb: any, i: number) => ({label: 'Concert tickets', dot: i === 0 ? C.green : C.red, on: tb.at === undefined ? -1 : 0.15, closing: i === 0 && s.close_ !== undefined ? s.close_ : undefined}));
		active = s.active ?? 0;
		const tb = s.tabs[active];
		const at = tb.at ?? -1;
		const pk = at < 0 ? 1 : clamp((t - at) / 0.2, 0, 1);
		body = (
			<AbsoluteFill>
				<div style={{position: 'absolute', left: 60 * u, top: 40 * u, fontFamily: fam(BODY), fontSize: 26 * u, color: C.mute}}>SATURDAY · 8 PM · THE CONCERT HALL</div>
				{s.crown_ === undefined ? <div style={{position: 'absolute', left: 60 * u, top: 110 * u, fontFamily: fam(BODY), fontSize: 30 * u, color: C.ink}}>1 TICKET</div> : null}
				{at < 0 || t >= at ? (
					<div style={{position: 'absolute', left: 56 * u, top: 150 * u, fontFamily: fam(HEAD), fontSize: 200 * u, lineHeight: 1.05, color: active === 0 ? C.green : C.red, transform: `scale(${1.1 - 0.1 * pk})`, transformOrigin: '0% 50%'}}>{tb.price}</div>
				) : (
					<div style={{position: 'absolute', left: 60 * u, top: 210 * u, width: 300 * u, height: 120 * u, borderRadius: 12 * u, background: 'rgba(30,27,24,0.08)'}} />
				)}
				{tb.tag ? (
					<div style={{position: 'absolute', left: 64 * u, top: 400 * u}}>
						{s.hl_ !== undefined ? <div style={{position: 'absolute', left: -10 * u, top: 4 * u, height: 58 * u, width: 300 * u * sm((t - s.hl_) / 0.45), background: C.accent, borderRadius: 6 * u, transform: 'rotate(-1.2deg)'}} /> : null}
						<div style={{position: 'relative', fontFamily: fam(BODY), fontSize: 44 * u, color: C.ink, letterSpacing: 2 * u}}>{tb.tag} · EVERYTHING INCLUDED</div>
					</div>
				) : null}
				{s.crown_ !== undefined ? (
					<Stroke d={`M ${80 * u} ${150 * u} L ${100 * u} ${95 * u} L ${135 * u} ${130 * u} L ${165 * u} ${80 * u} L ${195 * u} ${130 * u} L ${230 * u} ${95 * u} L ${250 * u} ${150 * u} Z`} t0={s.crown_} dur={0.7} t={t} w={7 * u} color={C.accent} W={B.w} H={B.h} />
				) : null}
				{s.saved_ !== undefined && t >= s.saved_ ? (
					<div style={{position: 'absolute', right: 70 * u, top: 150 * u - 40 * u * sm((t - s.saved_) / 0.6), opacity: sm((t - s.saved_) / 0.25), fontFamily: fam(HEAD), fontSize: 90 * u, color: C.green}}>+$10 SAVED</div>
				) : null}
				<Button u={u} x={B.w - 420 * u} y={B.h - 120 * u} w={360 * u} label="CONTINUE" t={t} />
			</AbsoluteFill>
		);
	} else if (s.mode === 'seat') {
		const k = s.fly_ === undefined ? 0 : io(clamp((t - s.fly_) / 0.8, 0, 1));
		body = <SeatMap u={u} w={B.w} h={B.h} t={t} s={s} k={k} />;
	} else if (s.mode === 'timer') {
		const k = s.timer_ === undefined ? 0 : sm((t - s.timer_) / 0.35);
		const left = s.from - Math.max(0, Math.floor(t - (s.timer_ ?? 0)));
		body = (
			<AbsoluteFill>
				<Page kind="seat" u={u} w={B.w} h={B.h} t={t} s={{light_: -1}} seatK={0} />
				<AbsoluteFill style={{background: `rgba(243,233,210,${0.55 * k})`}} />
				{k > 0 ? (
					<div style={{position: 'absolute', right: 40 * u, top: 30 * u + (1 - k) * -80 * u, opacity: k, background: C.ink, color: C.paper, borderRadius: 14 * u, padding: `${16 * u}px ${26 * u}px`, boxShadow: '0 8px 20px rgba(0,0,0,0.4)'}}>
						<div style={{fontFamily: fam(BODY), fontSize: 22 * u, letterSpacing: 1 * u}}>YOUR TICKET IS HELD FOR</div>
						<div style={{fontFamily: fam(HEAD), fontSize: 86 * u, lineHeight: 1.05, color: C.accent}}>{mmss(left)}</div>
					</div>
				) : null}
			</AbsoluteFill>
		);
	} else if (s.mode === 'fees') {
		body = (
			<AbsoluteFill style={{padding: `${34 * u}px ${60 * u}px`}}>
				<div style={{fontFamily: fam(BODY), fontSize: 24 * u, color: C.mute, letterSpacing: 1.5 * u}}>ORDER SUMMARY</div>
				<div style={{display: 'flex', justifyContent: 'space-between', marginTop: 14 * u, fontFamily: fam(BODY), fontSize: 30 * u, color: C.ink, borderBottom: `${2 * u}px dashed ${C.mute}`, paddingBottom: 8 * u}}>
					<span>TICKET · ROW G, SEAT 12</span>
					<span>$30</span>
				</div>
				{s.fees.map((fe: any, i: number) => {
					const at = fe.at_ ?? -1;
					if (t < at) return null;
					const k = clamp((t - at) / 0.2, 0, 1);
					const lab = fe.label ? (fe.label_ === undefined ? fe.label : fe.label.slice(0, clamp(Math.floor((t - fe.label_) / 0.04), 0, fe.label.length))) : '';
					return (
						<div key={i} style={{marginTop: 14 * u, transform: `scale(${1.1 - 0.1 * k})`, transformOrigin: '0% 50%'}}>
							<div style={{display: 'flex', justifyContent: 'space-between', fontFamily: fam(BODY), fontSize: 34 * u, color: C.red, borderBottom: `${2 * u}px dashed ${C.mute}`, paddingBottom: 8 * u}}>
								<span>{fe.name}</span>
								<span>{fe.amt}</span>
							</div>
							{fe.label ? <div style={{fontFamily: fam(TYPE), fontSize: 30 * u, color: C.ink, marginTop: 6 * u, minHeight: 36 * u, whiteSpace: 'pre'}}>{lab ? '↳ ' + lab : ''}</div> : null}
						</div>
					);
				})}
			</AbsoluteFill>
		);
	}
	const flash = s.mode === 'pay' && s.press_ !== undefined && t >= s.press_ ? Math.max(0, 1 - (t - s.press_) / 0.25) : 0;
	return (
		<AbsoluteFill>
			<NightBg t={t} dur={dur} SW={SW} SH={SH} />
			<AbsoluteFill style={{transform: `scale(${push * (s.zoom ?? 1)})`, transformOrigin: `50% ${(s.focus ?? 0.5) * 100}%`}}>
				<Win u={u} SW={SW} SH={SH} tabs={tabs} active={active} t={t}>
					{body}
				</Win>
			</AbsoluteFill>
			{flash > 0 ? <AbsoluteFill style={{background: `rgba(255,255,255,${0.85 * flash})`}} /> : null}
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ pictures
// a camera end is moved inside the picture once (never clamped per frame: a clamp mid-move is a kink, R28)
const fitEnd = (c: number[], iw: number, ih: number, SW: number, SH: number) => {
	const sc = Math.max(SW / iw, SH / ih) * c[2];
	const hx = SW / (iw * sc) / 2,
		hy = SH / (ih * sc) / 2;
	return [clamp(c[0], hx, 1 - hx), clamp(c[1], hy, 1 - hy), c[2]];
};
const camAt = (s: any, t: number, dur: number, iw = 1, ih = 1, SW = 1, SH = 1) => {
	const p = io(clamp(t / Math.max(dur, 0.1), 0, 1));
	const a = fitEnd(s.cam[0], iw, ih, SW, SH),
		b = fitEnd(s.cam[1], iw, ih, SW, SH);
	return [a[0] + (b[0] - a[0]) * p, a[1] + (b[1] - a[1]) * p, a[2] + (b[2] - a[2]) * p];
};
const Pic: React.FC<{src?: string; video?: string; iw: number; ih: number; cam: number[]; SW: number; SH: number; filter?: string}> = ({src, video, iw, ih, cam, SW, SH, filter}) => {
	const base = Math.max(SW / iw, SH / ih);
	const sc = base * cam[2];
	const tx = SW / 2 - cam[0] * iw * sc,
		ty = SH / 2 - cam[1] * ih * sc;
	const st: React.CSSProperties = {position: 'absolute', left: 0, top: 0, width: iw, height: ih, transformOrigin: '0 0', transform: `translate(${tx}px, ${ty}px) scale(${sc})`, filter};
	return video ? <OffthreadVideo src={staticFile(video)} muted style={st} /> : <Img src={staticFile(src as string)} style={st} />;
};

const StillView: React.FC<P> = ({s, t, dur, SW, SH, u}) => {
	const cam = camAt(s, t, dur, s.iw, s.ih, SW, SH);
	const nc = s.namecard;
	return (
		<AbsoluteFill style={{overflow: 'hidden', background: C.ink}}>
			<Pic src={s.img} iw={s.iw} ih={s.ih} cam={cam} SW={SW} SH={SH} filter={s.dream ? 'saturate(0.85) brightness(1.05)' : undefined} />
			{s.glow ? <AbsoluteFill style={{background: `radial-gradient(circle at 62% 52%, rgba(159,216,255,${0.18 + 0.22 * sm(t / dur)}) 0%, rgba(159,216,255,0) 45%)`}} /> : null}
			{s.dream ? <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 55%, rgba(255,236,190,0.0) 30%, rgba(255,236,190,0.35) 100%)', mixBlendMode: 'screen'}} /> : null}
			{s.green_creep ? <AbsoluteFill style={{background: C.green, opacity: 0.45 * sm((t - dur * 0.45) / (dur * 0.55)), mixBlendMode: 'multiply'}} /> : null}
			{nc ? <NameCard nc={nc} t={t} SW={SW} SH={SH} u={u} /> : null}
		</AbsoluteFill>
	);
};

const NameCard: React.FC<{nc: any; t: number; SW: number; SH: number; u: number}> = ({nc, t, SW, SH, u}) => {
	const [x0, y0, x1, y1] = SH >= SW && nc.box_short ? nc.box_short : nc.box;
	const w = (x1 - x0) * SW,
		h = (y1 - y0) * SH;
	const k = sm(t / 0.35);
	const fs = Math.min(fitText({text: nc.name, withinWidth: w * 0.7, fontFamily: TYPE}).fontSize, h * 0.32);
	return (
		<div style={{position: 'absolute', left: x0 * SW, top: y0 * SH, width: w, height: h, background: '#FBF4E2', border: `${3 * u}px solid ${C.ink}`, borderRadius: 6 * u, opacity: k,
			transform: `translateY(${(1 - k) * 14 * u}px) rotate(-1.5deg)`, boxShadow: '0 10px 24px rgba(0,0,0,0.45)', overflow: 'hidden'}}>
			<div style={{position: 'absolute', left: w * 0.12, top: 0, bottom: 0, width: 3 * u, background: C.red, opacity: 0.8}} />
			<div style={{position: 'absolute', left: w * 0.12 + 22, top: h * 0.12, fontFamily: fam(BODY), fontSize: h * 0.1, color: C.mute, letterSpacing: 1.5 * u}}>NAME</div>
			<div style={{position: 'absolute', left: w * 0.12 + 22, top: h * 0.26, fontFamily: fam(TYPE), fontSize: fs, color: C.ink}}>{nc.name}</div>
			<Stamp text={nc.stamp} at={nc.stamp_} t={t} x={w * 0.56} y={h * 0.74} size={h * 0.17} rot={-10} />
		</div>
	);
};

const ArchiveView: React.FC<P & {short: boolean; band: any}> = ({s, t, dur, SW, SH, u}) => {
	const cam = camAt(s, t, dur, s.iw, s.ih, SW, SH);
	return (
		<AbsoluteFill style={{overflow: 'hidden', background: C.ink}}>
			<Pic src={s.img} iw={s.iw} ih={s.ih} cam={cam} SW={SW} SH={SH} />
		</AbsoluteFill>
	);
};

const ClipView: React.FC<P> = ({s, t, dur, SW, SH}) => {
	const cam = camAt(s, t, dur, 1920, 1094, SW, SH);
	return (
		<AbsoluteFill style={{overflow: 'hidden', background: C.ink}}>
			<Pic video={s.video} iw={1920} ih={1094} cam={cam} SW={SW} SH={SH} />
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ a neutral card for a still Klot is still making
const MissingView: React.FC<P> = ({s, t, dur, SW, SH, u}) => {
	const sc = 1 + 0.035 * (t / Math.max(dur, 0.1));
	const w = Math.min(SW * 0.8, 1180 * u * 1.25),
		h = 360 * u * 1.15;
	const titleOn = s.title && t < 2.0;
	const title = s.title ? sm(t / 0.25) * (1 - sm((t - 1.7) / 0.3)) : 0;
	const name = `${s.file}.png`;
	const fs = Math.min(fitText({text: name, withinWidth: w * 0.86, fontFamily: BODY}).fontSize, 64 * u);
	return (
		<AbsoluteFill>
			<NightBg t={t} dur={dur} SW={SW} SH={SH} glow={false} />
			<AbsoluteFill style={{transform: `scale(${sc})`}}>
				<div style={{position: 'absolute', left: (SW - w) / 2, top: (SH - h) / 2 - 40 * u, width: w, height: h, border: `${3 * u}px dashed ${C.glow}`, borderRadius: 18 * u, background: 'rgba(14,26,43,0.6)'}}>
					<div style={{position: 'absolute', left: 0, right: 0, top: h * 0.14, textAlign: 'center', fontFamily: fam(BODY), fontSize: 26 * u, letterSpacing: 4 * u, color: C.accent}}>STILL TO COME · PREVIEW PLACEHOLDER</div>
					<div style={{position: 'absolute', left: 0, right: 0, top: h * 0.36, textAlign: 'center', fontFamily: fam(BODY), fontSize: fs, color: C.paper}}>{name}</div>
					<div style={{position: 'absolute', left: w * 0.08, right: w * 0.08, top: h * 0.64, textAlign: 'center', fontFamily: fam(SERIF), fontSize: 28 * u, color: C.glow, lineHeight: 1.3}}>{s.what}</div>
				</div>
				{s.pop_ !== undefined && t >= s.pop_ && t < s.pop_ + 0.5 ? (
					<svg width={SW} height={SH} style={{position: 'absolute', left: 0, top: 0}}>
						{Array.from({length: 12}).map((_, i) => {
							const a = (i / 12) * Math.PI * 2;
							const r0 = 60 * u + 200 * u * sm((t - s.pop_) / 0.25),
								r1 = r0 + 70 * u * (1 - sm((t - s.pop_) / 0.5));
							const cx = SW * 0.72,
								cy = SH * 0.28;
							return <line key={i} x1={cx + Math.cos(a) * r0} y1={cy + Math.sin(a) * r0} x2={cx + Math.cos(a) * r1} y2={cy + Math.sin(a) * r1} stroke={C.accent} strokeWidth={10 * u} strokeLinecap="round" />;
						})}
					</svg>
				) : null}
				{s.pop_ !== undefined && t >= s.pop_ ? <Stamp text="POP!" at={s.pop_} t={t} x={SW * 0.72} y={SH * 0.28} size={90 * u} color={C.accent} rot={8} /> : null}
				{s.sub_ !== undefined || (s.sub && s.sub_ === undefined) ? <Stamp text={s.sub} at={s.sub_ ?? 0.3} t={t} x={SW / 2} y={(SH + h) / 2 + 20 * u} size={52 * u} color={C.accent} rot={-4} /> : null}
			</AbsoluteFill>
			{titleOn ? <ActTitle lines={s.title} k={title} SW={SW} SH={SH} u={u} t={t} /> : null}
		</AbsoluteFill>
	);
};

const ActTitle: React.FC<{lines: string[]; k: number; SW: number; SH: number; u: number; t: number}> = ({lines, k, SW, SH, u, t}) => {
	const size = Math.min(fitText({text: lines[1], withinWidth: SW * 0.8, fontFamily: HEAD}).fontSize, 230 * u);
	const top = SH * 0.42 - size * 0.6;
	return (
		<AbsoluteFill style={{background: C.night, opacity: k}}>
			<AbsoluteFill style={{transform: `scale(${1.01 + 0.02 * t})`}}>
				<div style={{position: 'absolute', top: top - 70 * u, width: SW, textAlign: 'center', fontFamily: fam(BODY), fontSize: 46 * u, color: C.accent, letterSpacing: 10 * u, opacity: sm(t / 0.3)}}>{lines[0]}</div>
				<div style={{position: 'absolute', top, width: SW, textAlign: 'center', fontFamily: fam(HEAD), fontSize: size, lineHeight: 1.1, color: C.paper, opacity: sm((t - 0.2) / 0.3)}}>{lines[1]}</div>
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ cards
const IconsView: React.FC<P> = ({s, t, dur, SW, SH, u}) => {
	const n = s.items.length;
	const gap = 420 * u,
		sz = 220 * u;
	const cy = SH * 0.44;
	const icon = (kind: string) => {
		const st = {fill: C.paper, stroke: C.ink, strokeWidth: 6};
		if (kind === 'mask') return <path d="M10 60 C 40 20, 90 30, 100 50 C 110 30, 160 20, 190 60 C 180 110, 130 110, 110 85 L 90 85 C 70 110, 20 110, 10 60 Z M 45 62 a 16 11 0 1 0 32 0 a 16 11 0 1 0 -32 0 Z M 123 62 a 16 11 0 1 0 32 0 a 16 11 0 1 0 -32 0 Z" {...st} fillRule="evenodd" />;
		if (kind === 'car') return <path d="M15 120 L 15 92 C 15 82, 25 76, 40 74 L 62 46 C 70 38, 80 34, 95 34 L 140 34 C 152 34, 160 40, 166 48 L 182 74 C 192 76, 196 84, 196 94 L 196 120 Z M 52 120 a 20 20 0 1 0 40 0 a 20 20 0 1 0 -40 0 Z M 130 120 a 20 20 0 1 0 40 0 a 20 20 0 1 0 -40 0 Z" {...st} />;
		return <path d="M20 70 L 70 60 L 160 20 L 160 150 L 70 110 L 20 100 Z M 70 110 L 82 160 L 104 160 L 96 120" {...st} />;
	};
	return (
		<AbsoluteFill>
			<NightBg t={t} dur={dur} SW={SW} SH={SH} glow={false} />
			{s.items.map((it: string, i: number) => {
				const cx = SW / 2 + (i - (n - 1) / 2) * gap;
				const at = s.cross_[i];
				const k = spring({frame: (t - (at - 0.35)) * 30, fps: 30, config: {damping: 15, stiffness: 170}});
				if (t < at - 0.35) return null;
				return (
					<React.Fragment key={i}>
						<svg viewBox="0 0 210 170" width={sz} height={sz * 0.81} style={{position: 'absolute', left: cx - sz / 2, top: cy - sz * 0.4, transform: `scale(${0.85 + 0.15 * k})`, opacity: clamp(k * 1.4, 0, 1)}}>
							{icon(it)}
						</svg>
						<Stroke d={`M ${cx - sz * 0.5} ${cy - sz * 0.45} L ${cx + sz * 0.5} ${cy + sz * 0.45} M ${cx + sz * 0.5} ${cy - sz * 0.45} L ${cx - sz * 0.5} ${cy + sz * 0.45}`} t0={at} dur={0.32} t={t} w={16 * u} W={SW} H={SH} />
					</React.Fragment>
				);
			})}
		</AbsoluteFill>
	);
};

const FeeCardView: React.FC<P> = ({s, t, dur, SW, SH, u}) => {
	const w = 900 * u,
		h = 470 * u;
	const x = (SW - w) / 2,
		y = (SH - h) / 2 - 50 * u;
	return (
		<AbsoluteFill>
			<NightBg t={t} dur={dur} SW={SW} SH={SH} />
			<div style={{position: 'absolute', left: x, top: y, width: w, height: h, background: '#FBF4E2', border: `${3 * u}px solid ${C.ink}`, borderRadius: 10 * u, transform: `scale(${1 + 0.03 * t / dur}) rotate(1deg)`, boxShadow: '0 16px 40px rgba(0,0,0,0.5)'}}>
				<div style={{position: 'absolute', left: 50 * u, top: 34 * u, fontFamily: fam(BODY), fontSize: 26 * u, letterSpacing: 2 * u, color: C.mute}}>CHARGED AT CHECKOUT</div>
				{s.lines.map((l: string, i: number) => {
					const k = sm((t - 0.15 - i * 0.22) / 0.25);
					return (
						<div key={i} style={{position: 'absolute', left: 50 * u, top: (100 + i * 92) * u, width: w - 100 * u, opacity: k, borderBottom: `${2 * u}px dashed ${C.mute}`, paddingBottom: 10 * u, fontFamily: fam(TYPE), fontSize: 50 * u, color: C.ink}}>
							{l}
						</div>
					);
				})}
				<Stamp text={s.stamp} at={s.stamp_} t={t} x={w * 0.72} y={h * 0.55} size={120 * u} rot={-10} />
			</div>
		</AbsoluteFill>
	);
};

const BigNumView: React.FC<P> = ({s, t, dur, SW, SH, u}) => {
	const br = 1 + 0.012 * Math.sin(t * 2.2);
	const size = 360 * u;
	const cy = SH * (s.slots ? 0.34 : 0.42);
	const slotW = 230 * u,
		gap = 40 * u;
	const n = s.slots || 0;
	const x0 = SW / 2 - (n * slotW + (n - 1) * gap) / 2;
	return (
		<AbsoluteFill>
			<NightBg t={t} dur={dur} SW={SW} SH={SH} />
			<div style={{position: 'absolute', top: cy - size * 0.55, width: SW, textAlign: 'center', fontFamily: fam(HEAD), fontSize: size, lineHeight: 1.1, color: C.paper, transform: `scale(${br})`,
				textShadow: `0 0 ${30 * u}px rgba(159,216,255,${0.35 + 0.1 * Math.sin(t * 2.2)})`, filter: `blur(${0.6 + 0.4 * Math.sin(t * 1.3)}px)`}}>
				{s.text}
			</div>
			{Array.from({length: n}).map((_, i) => {
				const at = s.slots_ !== undefined ? s.slots_ + i * 0.18 : s.fill_at ? 0 : 0;
				const k = s.slots_ !== undefined ? spring({frame: (t - at) * 30, fps: 30, config: {damping: 14, stiffness: 180}}) : 1;
				if (s.slots_ !== undefined && t < at) return null;
				const fv = s.filled ? s.filled[i] : null;
				const fat = s.fill3_ !== undefined ? [0.05, 0.25, s.fill3_][i] : s.fill_at ? s.fill_at[i] * dur : 0;
				const fk = fv ? clamp((t - fat) / 0.2, 0, 1) : 0;
				return (
					<div key={i} style={{position: 'absolute', left: x0 + i * (slotW + gap), top: SH * 0.6, width: slotW, height: 140 * u, border: `${4 * u}px dashed ${C.glow}`, borderRadius: 14 * u, transform: `scale(${0.8 + 0.2 * k})`, opacity: clamp(k, 0, 1),
						display: 'flex', alignItems: 'center', justifyContent: 'center', background: fk > 0 ? 'rgba(210,69,47,0.18)' : 'transparent'}}>
						<div style={{fontFamily: fam(HEAD), fontSize: 90 * u, color: fk > 0 ? C.red : C.glow, opacity: fk > 0 ? 1 : 0.6, transform: `scale(${fk > 0 ? 1.1 - 0.1 * fk : 1})`}}>{fk > 0 ? fv : ['①', '②', '③'][i]}</div>
					</div>
				);
			})}
		</AbsoluteFill>
	);
};

const CalendarView: React.FC<P> = ({s, t, dur, SW, SH, u}) => {
	const n = s.days.length;
	const bw = 300 * u,
		gap = 30 * u;
	const x0 = SW / 2 - (n * bw + (n - 1) * gap) / 2;
	const y = SH * 0.36;
	const p = io(clamp((t - 0.3) / Math.min(2.5, dur * 0.6), 0, 1));
	return (
		<AbsoluteFill>
			<NightBg t={t} dur={dur} SW={SW} SH={SH} />
			{s.days.map((d: string, i: number) => (
				<div key={i} style={{position: 'absolute', left: x0 + i * (bw + gap), top: y, width: bw, height: 180 * u, background: i === 0 ? C.paper : C.paper2, border: `${3 * u}px solid ${C.ink}`, borderRadius: 10 * u, display: 'flex', alignItems: 'center', justifyContent: 'center',
					fontFamily: fam(HEAD), fontSize: 92 * u, color: i === n - 1 ? C.red : C.ink}}>{d}</div>
			))}
			<div style={{position: 'absolute', left: x0, top: y + 220 * u, height: 26 * u, width: (n * bw + (n - 1) * gap) * p, background: C.green, borderRadius: 13 * u}} />
			<div style={{position: 'absolute', left: x0, top: y - 140 * u, fontFamily: fam(HEAD), fontSize: 110 * u, color: C.accent, lineHeight: 1.1}}>{s.from}</div>
			<div style={{position: 'absolute', left: x0 + 300 * u, top: y - 100 * u, fontFamily: fam(BODY), fontSize: 40 * u, color: C.paper, opacity: sm((t - 0.6) / 0.3)}}>HAS TO LAST UNTIL FRIDAY</div>
		</AbsoluteFill>
	);
};

const RouteView: React.FC<P> = ({s, t, dur, SW, SH, u}) => {
	const ax = SW * 0.22,
		ay = SH * 0.58,
		bx = SW * 0.78,
		by = SH * 0.3;
	const d = `M ${ax} ${ay} C ${SW * 0.38} ${SH * 0.2}, ${SW * 0.58} ${SH * 0.72}, ${bx} ${by}`;
	const at = 0.3;
	const p = clamp((t - at) / 1.8, 0, 1);
	const lab = s.draw_ === undefined ? sm((p - 0.6) / 0.2) : sm((t - s.draw_) / 0.25);
	const ev = evolvePath(io(p), d);
	return (
		<AbsoluteFill>
			<NightBg t={t} dur={dur} SW={SW} SH={SH} glow={false} />
			<svg width={SW} height={SH} style={{position: 'absolute', left: 0, top: 0}}>
				{Array.from({length: 14}).map((_, i) => (
					<line key={'h' + i} x1={0} x2={SW} y1={(i + 0.5) * SH / 14 + noise2D('r', i, 0) * 20} y2={(i + 0.5) * SH / 14 + noise2D('r', i, 1) * 40} stroke="#203553" strokeWidth={4 * u} />
				))}
				{Array.from({length: 20}).map((_, i) => (
					<line key={'v' + i} y1={0} y2={SH} x1={(i + 0.5) * SW / 20 + noise2D('c', i, 0) * 30} x2={(i + 0.5) * SW / 20 + noise2D('c', i, 1) * 30} stroke="#203553" strokeWidth={4 * u} />
				))}
				<path d={d} fill="none" stroke={C.accent} strokeWidth={12 * u} strokeLinecap="round" strokeDasharray={ev.strokeDasharray} strokeDashoffset={ev.strokeDashoffset} />
				<circle cx={ax} cy={ay} r={22 * u} fill={C.paper} stroke={C.ink} strokeWidth={5 * u} />
				<circle cx={bx} cy={by} r={22 * u * sm((p - 0.9) / 0.1)} fill={C.red} stroke={C.ink} strokeWidth={5 * u} />
			</svg>
			<div style={{position: 'absolute', left: ax - 200 * u, top: ay + 40 * u, width: 400 * u, textAlign: 'center', fontFamily: fam(BODY), fontSize: 34 * u, color: C.paper}}>{s.from}</div>
			<div style={{position: 'absolute', left: bx - 260 * u, top: by - 100 * u, width: 520 * u, textAlign: 'center', fontFamily: fam(BODY), fontSize: 34 * u, color: C.paper, opacity: sm((p - 0.85) / 0.15)}}>{s.to}</div>
			<div style={{position: 'absolute', left: SW * 0.44, top: SH * 0.5, fontFamily: fam(HEAD), fontSize: 80 * u, color: C.accent, opacity: lab}}>{s.label}</div>
			<div style={{position: 'absolute', left: 80 * u, top: 70 * u, fontFamily: fam(BODY), fontSize: 36 * u, color: C.glow, letterSpacing: 6 * u}}>{s.day}</div>
		</AbsoluteFill>
	);
};

const TimerView: React.FC<P> = ({s, t, dur, SW, SH, u}) => {
	const left = s.from - Math.floor(t);
	const frac = 1 - (t % 1);
	const size = (s.big ? 300 : 240) * u;
	const r = size * 0.95;
	const cx = SW / 2,
		cy = SH * 0.43;
	const p = left / 600;
	const ring = `M ${cx} ${cy - r} A ${r} ${r} 0 1 1 ${cx - 0.01} ${cy - r}`;
	const ev = evolvePath(p, ring);
	return (
		<AbsoluteFill>
			<NightBg t={t} dur={dur} SW={SW} SH={SH} />
			<AbsoluteFill style={{transform: `scale(${1.02 + 0.04 * t / dur})`}}>
				<svg width={SW} height={SH} style={{position: 'absolute', left: 0, top: 0}}>
					<circle cx={cx} cy={cy} r={r} fill="none" stroke="#24395A" strokeWidth={22 * u} />
					<path d={ring} fill="none" stroke={C.accent} strokeWidth={22 * u} strokeLinecap="round" strokeDasharray={ev.strokeDasharray} strokeDashoffset={ev.strokeDashoffset} />
				</svg>
				<div style={{position: 'absolute', left: 0, top: cy - size * 0.62, width: SW, textAlign: 'center', fontFamily: fam(HEAD), fontSize: size, lineHeight: 1.2, color: C.paper, opacity: 0.94 + 0.06 * frac}}>{mmss(left)}</div>
				<div style={{position: 'absolute', left: 0, top: cy + r * 0.48, width: SW, textAlign: 'center', fontFamily: fam(BODY), fontSize: 30 * u, letterSpacing: 4 * u, color: C.glow}}>TICKET HELD</div>
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

const BarsView: React.FC<P> = ({s, t, dur, SW, SH, u}) => {
	const p = io(clamp((t - 0.3) / 0.9, 0, 1)); // R35: all bars grow together, monotonically, from zero
	const max = Math.max(...s.bars.map((b: any) => b[1]));
	const base = SH * 0.72,
		hMax = SH * 0.42,
		bw = 300 * u,
		gap = 200 * u;
	const x0 = SW / 2 - (s.bars.length * bw + (s.bars.length - 1) * gap) / 2;
	return (
		<AbsoluteFill>
			<NightBg t={t} dur={dur} SW={SW} SH={SH} />
			<div style={{position: 'absolute', left: x0 - 40 * u, top: base, width: s.bars.length * bw + gap + 80 * u, height: 4 * u, background: C.paper}} />
			{s.bars.map((b: any, i: number) => {
				const h = (b[1] / max) * hMax * p;
				return (
					<React.Fragment key={i}>
						<div style={{position: 'absolute', left: x0 + i * (bw + gap), top: base - h, width: bw, height: h, background: i ? C.red : C.green, border: `${3 * u}px solid ${C.ink}`, borderBottom: 'none'}} />
						<div style={{position: 'absolute', left: x0 + i * (bw + gap) - 60 * u, width: bw + 120 * u, top: base - hMax * (b[1] / max) - 120 * u, textAlign: 'center', fontFamily: fam(HEAD), fontSize: 96 * u, color: C.paper, opacity: p >= 1 ? 1 : 0}}>{b[2]}</div>
						<div style={{position: 'absolute', left: x0 + i * (bw + gap) - 60 * u, width: bw + 120 * u, top: base + 16 * u, textAlign: 'center', fontFamily: fam(BODY), fontSize: 28 * u, color: C.glow}}>{b[0]}</div>
					</React.Fragment>
				);
			})}
			{s.stamp_ !== undefined ? <Stamp text={s.stamp} at={s.stamp_} t={t} x={x0 + 2 * bw + gap + 250 * u} y={base - hMax * 0.55} size={110 * u} rot={-8} /> : null}
		</AbsoluteFill>
	);
};

const VersusView: React.FC<P> = ({s, t, dur, SW, SH, u}) => {
	const cy = SH * 0.42;
	const col = (x: number, price: string, tag: string, color: string) => (
		<>
			<div style={{position: 'absolute', left: x - 340 * u, width: 680 * u, top: cy - 200 * u, textAlign: 'center', fontFamily: fam(HEAD), fontSize: 260 * u, lineHeight: 1.1, color}}>{price}</div>
			<div style={{position: 'absolute', left: x - 340 * u, width: 680 * u, top: cy + 120 * u, textAlign: 'center', fontFamily: fam(BODY), fontSize: 34 * u, color: C.glow, letterSpacing: 2 * u}}>{tag}</div>
		</>
	);
	const lx = SW * 0.3,
		rx = SW * 0.7;
	return (
		<AbsoluteFill>
			<NightBg t={t} dur={dur} SW={SW} SH={SH} />
			<AbsoluteFill style={{transform: `scale(${1.01 + 0.03 * t / dur})`}}>
				{col(lx, s.left, s.left_tag, C.green)}
				{col(rx, s.right, s.right_tag, C.red)}
				<div style={{position: 'absolute', left: SW / 2 - 2 * u, top: cy - 200 * u, width: 4 * u, height: 380 * u, background: '#2B4466'}} />
				{s.left_cross ? <Stroke d={`M ${lx - 230 * u} ${cy + 60 * u} L ${lx + 230 * u} ${cy - 120 * u}`} t0={0.25} dur={0.35} t={t} w={18 * u} W={SW} H={SH} /> : null}
				{s.badge_ !== undefined ? <Stamp text={s.badge} at={s.badge_} t={t} x={s.badge === '?' ? SW / 2 : rx + 250 * u} y={s.badge === '?' ? cy - 330 * u : cy - 210 * u} size={(s.badge === '?' ? 150 : 90) * u} rot={s.badge === '?' ? 6 : -10} color={s.badge === '?' ? C.accent : C.red} /> : null}
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

const TimelineView: React.FC<P> = ({s, t, dur, SW, SH, u}) => {
	const n = s.steps.length;
	const x0 = SW * 0.1,
		x1 = SW * 0.9,
		y = SH * 0.42;
	const p = s.drawn ? 1 : io(clamp((t - 0.2) / (dur * 0.8), 0, 1));
	const d = `M ${x0} ${y} L ${x1} ${y}`;
	const ev = evolvePath(p, d);
	return (
		<AbsoluteFill>
			<NightBg t={t} dur={dur} SW={SW} SH={SH} />
			<svg width={SW} height={SH} style={{position: 'absolute', left: 0, top: 0}}>
				<path d={d} stroke={C.paper} strokeWidth={8 * u} strokeLinecap="round" strokeDasharray={ev.strokeDasharray} strokeDashoffset={ev.strokeDashoffset} />
			</svg>
			{s.steps.map(([tm, lab]: [string, string], i: number) => {
				const x = x0 + ((x1 - x0) * i) / (n - 1);
				const k = sm((p - i / (n - 1)) / 0.08 + 1);
				return (
					<React.Fragment key={i}>
						<div style={{position: 'absolute', left: x - 14 * u, top: y - 14 * u, width: 28 * u, height: 28 * u, borderRadius: 14 * u, background: i === n - 1 ? C.red : C.accent, opacity: k}} />
						<div style={{position: 'absolute', left: x - 120 * u, width: 240 * u, top: y - 100 * u, textAlign: 'center', fontFamily: fam(HEAD), fontSize: 54 * u, color: C.paper, opacity: k}}>{tm}</div>
						<div style={{position: 'absolute', left: x - 120 * u, width: 240 * u, top: y + 34 * u, textAlign: 'center', fontFamily: fam(BODY), fontSize: 24 * u, color: C.glow, opacity: k}}>{lab}</div>
					</React.Fragment>
				);
			})}
			{s.total ? (
				<>
					<div style={{position: 'absolute', left: 0, width: SW, top: SH * 0.56, textAlign: 'center', fontFamily: fam(HEAD), fontSize: 150 * u, color: C.red, lineHeight: 1.1}}>{s.total}</div>
					{s.circle_ !== undefined ? (
						<Stroke d={`M ${SW / 2 + 150 * u} ${SH * 0.56 + 40 * u} C ${SW / 2 + 190 * u} ${SH * 0.56 + 160 * u}, ${SW / 2 - 200 * u} ${SH * 0.56 + 190 * u}, ${SW / 2 - 190 * u} ${SH * 0.56 + 80 * u} C ${SW / 2 - 180 * u} ${SH * 0.56 - 10 * u}, ${SW / 2 + 120 * u} ${SH * 0.56 - 20 * u}, ${SW / 2 + 170 * u} ${SH * 0.56 + 60 * u}`}
							t0={s.circle_} dur={0.6} t={t} w={9 * u} W={SW} H={SH} />
					) : null}
				</>
			) : null}
		</AbsoluteFill>
	);
};

const BlueprintView: React.FC<P> = ({s, t, dur, SW, SH, u}) => {
	const bg = s.tint === 'green' ? '#0F2A24' : '#0B1626';
	const line = s.tint === 'green' ? '#7FD1B0' : C.glow;
	const segs = [
		`M ${SW * 0.2} ${SH * 0.2} L ${SW * 0.8} ${SH * 0.2} L ${SW * 0.8} ${SH * 0.7} L ${SW * 0.2} ${SH * 0.7} Z`,
		`M ${SW * 0.2} ${SH * 0.42} L ${SW * 0.46} ${SH * 0.42} L ${SW * 0.46} ${SH * 0.7}`,
		`M ${SW * 0.58} ${SH * 0.2} L ${SW * 0.58} ${SH * 0.5} L ${SW * 0.8} ${SH * 0.5}`,
		`M ${SW * 0.3} ${SH * 0.56} L ${SW * 0.38} ${SH * 0.56} M ${SW * 0.66} ${SH * 0.32} a ${40 * u} ${40 * u} 0 1 0 ${80 * u} 0 a ${40 * u} ${40 * u} 0 1 0 ${-80 * u} 0`,
		`M ${SW * 0.24} ${SH * 0.77} L ${SW * 0.76} ${SH * 0.77} M ${SW * 0.24} ${SH * 0.75} L ${SW * 0.24} ${SH * 0.79} M ${SW * 0.76} ${SH * 0.75} L ${SW * 0.76} ${SH * 0.79}`,
	];
	return (
		<AbsoluteFill style={{background: bg}}>
			<AbsoluteFill style={{transform: `scale(${1.02 + 0.04 * t / dur})`}}>
				<svg width={SW} height={SH} style={{position: 'absolute', left: 0, top: 0}}>
					{Array.from({length: 40}).map((_, i) => (
						<line key={i} x1={(i * SW) / 40} x2={(i * SW) / 40} y1={0} y2={SH} stroke={line} strokeOpacity={0.08} strokeWidth={2} />
					))}
					{Array.from({length: 24}).map((_, i) => (
						<line key={'y' + i} y1={(i * SH) / 24} y2={(i * SH) / 24} x1={0} x2={SW} stroke={line} strokeOpacity={0.08} strokeWidth={2} />
					))}
				</svg>
				{segs.map((d, i) => (
					<Stroke key={i} d={d} t0={0.1 + i * (dur * 0.16)} dur={dur * 0.22} t={t} w={5 * u} color={line} W={SW} H={SH} />
				))}
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

const CaseFolderView: React.FC<P> = ({s, t, dur, SW, SH, u}) => {
	const at = (s.slide_ ?? 0.5) - 0.45;
	const k = io(clamp((t - at) / 0.5, 0, 1));
	const w = 1100 * u,
		h = 660 * u;
	const x = (SW - w) / 2,
		y = (SH - h) / 2 - 40 * u + (1 - k) * SH * 0.8;
	const typed = (txt: string, a?: number) => (a === undefined ? '' : txt.slice(0, clamp(Math.floor((t - a) / 0.045), 0, txt.length)));
	const t1 = `CASE FILE ${s.number}`;
	return (
		<AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 45%, #3A2A1C 0%, #1C140D 70%)'}}>
			<AbsoluteFill style={{transform: `scale(${1.02 + 0.03 * t / dur})`}}>
				<div style={{position: 'absolute', left: x, top: y, width: w, height: h}}>
					<div style={{position: 'absolute', left: 60 * u, top: -50 * u, width: 360 * u, height: 70 * u, background: '#D9B97A', border: `${3 * u}px solid ${C.ink}`, borderBottom: 'none', borderRadius: `${12 * u}px ${12 * u}px 0 0`}} />
					<div style={{position: 'absolute', left: 0, top: 0, width: w, height: h, background: '#D9B97A', border: `${3 * u}px solid ${C.ink}`, borderRadius: 10 * u, boxShadow: '0 30px 60px rgba(0,0,0,0.6)'}}>
						<div style={{position: 'absolute', left: 90 * u, top: 110 * u, fontFamily: fam(TYPE), fontSize: 70 * u, color: C.ink}}>{typed(t1, s.type_?.[0])}</div>
						<div style={{position: 'absolute', left: 90 * u, top: 230 * u, width: w - 180 * u, fontFamily: fam(TYPE), fontSize: Math.min(92 * u, fitText({text: s.title, withinWidth: w - 180 * u, fontFamily: TYPE}).fontSize), color: C.red}}>{typed(s.title, s.type_?.[1])}</div>
						<div style={{position: 'absolute', left: 90 * u, top: 420 * u, width: w - 180 * u, height: 3 * u, background: 'rgba(30,27,24,0.35)'}} />
						<div style={{position: 'absolute', left: 90 * u, top: 450 * u, fontFamily: fam(BODY), fontSize: 26 * u, color: 'rgba(30,27,24,0.6)', letterSpacing: 3 * u}}>COINSENSE · PRICE INVESTIGATIONS</div>
					</div>
				</div>
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

const FanView: React.FC<P> = ({s, t, dur, SW, SH, u}) => {
	const n = s.pages.length;
	return (
		<AbsoluteFill>
			<NightBg t={t} dur={dur} SW={SW} SH={SH} />
			{s.pages.map((pg: string, i: number) => {
				const k = spring({frame: (t - 0.1 - i * 0.18) * 30, fps: 30, config: {damping: 16, stiffness: 140}});
				const rot = (i - (n - 1) / 2) * 9 * k;
				const dx = (i - (n - 1) / 2) * 400 * u * k;
				const w = 520 * u,
					h = 360 * u;
				const label = {tabs: '$40 / $30', seat: 'SEAT G12', timer: '10:00', form: 'CARD'}[pg] as string;
				return (
					<div key={i} style={{position: 'absolute', left: SW / 2 - w / 2 + dx, top: SH * 0.42 - h / 2, width: w, height: h, transform: `rotate(${rot}deg)`, transformOrigin: '50% 120%', background: C.paper, border: `${3 * u}px solid ${C.ink}`, borderRadius: 14 * u,
						boxShadow: '0 12px 30px rgba(0,0,0,0.5)', opacity: clamp(k * 1.5, 0, 1)}}>
						<div style={{height: 40 * u, background: C.paper2, borderBottom: `${3 * u}px solid ${C.ink}`, borderRadius: `${12 * u}px ${12 * u}px 0 0`}} />
						<div style={{position: 'absolute', left: 0, right: 0, top: 140 * u, textAlign: 'center', fontFamily: fam(HEAD), fontSize: 72 * u, color: C.ink}}>{label}</div>
					</div>
				);
			})}
		</AbsoluteFill>
	);
};

// two wires and a pair of scissors that cannot decide (A1.J2)
const WiresView: React.FC<P> = ({s, t, dur, SW, SH, u}) => {
	const y0 = SH * 0.42;
	const wire = (dy: number, col: string) => `M ${SW * 0.12} ${y0 + dy} C ${SW * 0.35} ${y0 + dy - 60 * u}, ${SW * 0.6} ${y0 + dy + 70 * u}, ${SW * 0.88} ${y0 + dy}`;
	const snip = s.snip_ ?? dur * 0.8;
	const hes = Math.sin(t * 5.2) * 0.5 + noise2D('sc', t * 0.7, 0) * 0.5; // hovering between the wires
	const sy = y0 + hes * 70 * u;
	const sx = SW * 0.5 + Math.sin(t * 1.7) * 30 * u;
	const open = 18 + 10 * Math.sin(t * 9);
	return (
		<AbsoluteFill>
			<NightBg t={t} dur={dur} SW={SW} SH={SH} />
			<svg width={SW} height={SH} style={{position: 'absolute', left: 0, top: 0}}>
				<path d={wire(-70 * u, '')} fill="none" stroke={C.red} strokeWidth={22 * u} strokeLinecap="round" />
				<path d={wire(70 * u, '')} fill="none" stroke="#3E7BD6" strokeWidth={22 * u} strokeLinecap="round" />
				<g transform={`translate(${sx} ${sy}) rotate(-90)`}>
					<g transform={`rotate(${-open / 2})`}><path d={`M 0 0 L ${-14 * u} ${-170 * u} L ${14 * u} ${-170 * u} Z`} fill="#C9CED6" stroke={C.ink} strokeWidth={4 * u} /><circle cx={0} cy={60 * u} r={38 * u} fill="none" stroke={C.accent} strokeWidth={14 * u} /></g>
					<g transform={`rotate(${open / 2})`}><path d={`M 0 0 L ${-14 * u} ${-170 * u} L ${14 * u} ${-170 * u} Z`} fill="#AEB4BE" stroke={C.ink} strokeWidth={4 * u} /><circle cx={0} cy={60 * u} r={38 * u} fill="none" stroke={C.accent} strokeWidth={14 * u} /></g>
					<circle cx={0} cy={0} r={8 * u} fill={C.ink} />
				</g>
			</svg>
			{t >= snip ? <div style={{position: 'absolute', left: 0, width: SW, top: SH * 0.66, textAlign: 'center', fontFamily: fam(HEAD), fontSize: 80 * u, color: C.paper, opacity: sm((t - snip) / 0.2)}}>RED? BLUE?</div> : null}
		</AbsoluteFill>
	);
};

// the card-number field, close: sixteen digits typed as dots (no real number, no hands)
const DigitsView: React.FC<P> = ({s, t, dur, SW, SH, u}) => {
	const w = 1500 * u,
		h = 190 * u;
	const x = (SW - w) / 2,
		y = SH * 0.42 - h / 2;
	const at = s.digits_ ?? 0.3;
	const n = clamp(Math.floor((t - at) / (1.8 / 16)) + 1, 0, 16);
	return (
		<AbsoluteFill>
			<NightBg t={t} dur={dur} SW={SW} SH={SH} />
			<AbsoluteFill style={{transform: `scale(${1.02 + 0.04 * t / dur})`}}>
				<div style={{position: 'absolute', left: x, top: y - 70 * u, fontFamily: fam(BODY), fontSize: 40 * u, color: C.glow, letterSpacing: 4 * u}}>CARD NUMBER</div>
				<div style={{position: 'absolute', left: x, top: y, width: w, height: h, background: '#FBF6EA', border: `${5 * u}px solid ${C.ink}`, borderRadius: 18 * u, boxShadow: `0 0 ${80 * u}px rgba(159,216,255,0.3)`}}>
					{Array.from({length: 16}).map((_, i) => {
						const k = i < n ? spring({frame: (t - at - (i * 1.8) / 16) * 30, fps: 30, config: {damping: 14, stiffness: 220}}) : 0;
						const gx = 80 * u + i * 80 * u + Math.floor(i / 4) * 50 * u;
						return <div key={i} style={{position: 'absolute', left: gx, top: h / 2 - 22 * u, width: 44 * u, height: 44 * u, borderRadius: 22 * u, background: C.ink, transform: `scale(${k})`}} />;
					})}
				</div>
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ overlays: archive caption, the in-world clock, subtitles, vignette
const CaptionPlate: React.FC<{text: string; W: number; H: number; short: boolean; t: number}> = ({text, W, H, short, t}) => {
	const fs0 = short ? 34 : 30;
	const maxW = W * (short ? 0.88 : 0.6);
	const fs = Math.max(short ? 30 : 22, Math.min(fs0, fitText({text, withinWidth: maxW - 40, fontFamily: SERIF}).fontSize));
	const lines = measureText({text, fontFamily: SERIF, fontSize: fs}).width > maxW - 40 ? 2 : 1;
	const k = sm(t / 0.3);
	const st: React.CSSProperties = short
		? {position: 'absolute', left: (W - maxW) / 2, width: maxW, top: 150}
		: {position: 'absolute', left: 48, bottom: H * 0.2, maxWidth: maxW};
	return (
		<div style={{...st, background: C.paper, color: C.ink, fontFamily: fam(SERIF), fontSize: fs, lineHeight: 1.25, padding: '10px 20px', borderRadius: 6, opacity: k, boxShadow: '0 6px 16px rgba(0,0,0,0.35)', textAlign: short ? 'center' : 'left', boxSizing: 'border-box'}}>
			{text}
		</div>
	);
};

const Clock: React.FC<{label: string; W: number; H: number; t: number}> = ({label, W, H, t}) => {
	const fs = Math.round(H * 0.03);
	const r = fs * 0.75;
	const a = (t % 60) * 6;
	return (
		<div style={{position: 'absolute', right: 40, top: 36, display: 'flex', alignItems: 'center', gap: fs * 0.5, background: 'rgba(14,26,43,0.86)', border: `2px solid ${C.glow}`, borderRadius: 10, padding: `${fs * 0.35}px ${fs * 0.6}px`}}>
			<svg width={r * 2} height={r * 2}>
				<circle cx={r} cy={r} r={r - 2} fill="none" stroke={C.paper} strokeWidth={3} />
				<line x1={r} y1={r} x2={r + Math.sin((a * Math.PI) / 180) * (r - 6)} y2={r - Math.cos((a * Math.PI) / 180) * (r - 6)} stroke={C.accent} strokeWidth={3} strokeLinecap="round" />
			</svg>
			<div style={{fontFamily: fam(BODY), fontSize: fs, color: C.paper, letterSpacing: 1}}>TUE · {label} PM</div>
		</div>
	);
};

const Subs: React.FC<{caps: any[]; W: number; H: number; t: number; short: boolean}> = ({caps, W, H, t, short}) => {
	const c = caps.find((x) => t >= x.start - 0.05 && t < x.end + 0.25);
	if (!c) return null;
	const font = short ? HEAD : BODY;
	const toks = c.words.map((w: any, i: number) => (i ? ' ' : '') + (short ? w[0].toUpperCase() : w[0]));
	let size = Math.round(H * (short ? 0.042 : 0.05));
	size = Math.min(size, Math.floor(fitText({text: toks.join(''), withinWidth: W * 0.86, fontFamily: font}).fontSize));
	const widths = toks.map((x: string) => measureText({text: x, fontFamily: font, fontSize: size}).width);
	const total = widths.reduce((a: number, b: number) => a + b, 0);
	const x0 = (W - total) / 2;
	const ai = c.words.findIndex((w: any, i: number) => t >= w[1] - 0.03 && (i === c.words.length - 1 || t < c.words[i + 1][1] - 0.03));
	const y = short ? H * 0.82 : H * 0.865 - size * 0.62;
	const stroke = Math.max(3, Math.round(size / 9));
	let acc = 0;
	return (
		<div style={{position: 'absolute', left: 0, top: y, width: W, height: size * 1.3}}>
			{toks.map((x: string, i: number) => {
				const left = x0 + acc;
				acc += widths[i];
				return (
					<span key={i} style={{position: 'absolute', left, top: 0, whiteSpace: 'pre', fontFamily: fam(font), fontSize: size, lineHeight: 1.3, color: i === ai ? C.accent : '#fff', WebkitTextStroke: `${stroke * 2}px ${C.ink}`, paintOrder: 'stroke fill'}}>
						{x}
					</span>
				);
			})}
		</div>
	);
};

// the print-style ink wipe edge (the incoming shot is revealed behind a torn ink line)
const wipeClip = (p: number, W: number, H: number) => {
	const e = Easing.inOut(Easing.cubic)(p);
	const pts: string[] = ['0px -20px'];
	for (let y = -20; y <= H + 20; y += 12) {
		const x = e * (W + 320) - 160 + noise2D('wipe', y / 260, 0) * 34 + noise2D('wipe2', y / 40, 3) * 6 + (y / H) * 120 - 60;
		pts.push(`${x}px ${y}px`);
	}
	pts.push(`0px ${H + 20}px`);
	return `polygon(${pts.join(',')})`;
};

const ShotBody: React.FC<{s: any; SW: number; SH: number; u: number; dur: number; short: boolean; band: any}> = ({s, SW, SH, u, dur, short, band}) => {
	const f = useCurrentFrame();
	const {fps} = useVideoConfig();
	const t = f / fps;
	const p: P = {s, t, dur, SW, SH, u, fps};
	switch (s.kind) {
		case 'missing': return <MissingView {...p} />;
		case 'still': return <StillView {...p} />;
		case 'archive': return <ArchiveView {...p} short={short} band={band} />;
		case 'clip': return <ClipView {...p} />;
		case 'screen': return <ScreenView {...p} />;
		case 'icons': return <IconsView {...p} />;
		case 'feecard': return <FeeCardView {...p} />;
		case 'bignum': return <BigNumView {...p} />;
		case 'calendar': return <CalendarView {...p} />;
		case 'route': return <RouteView {...p} />;
		case 'timer': return <TimerView {...p} />;
		case 'bars': return <BarsView {...p} />;
		case 'versus': return <VersusView {...p} />;
		case 'timeline': return <TimelineView {...p} />;
		case 'blueprint': return <BlueprintView {...p} />;
		case 'casefolder': return <CaseFolderView {...p} />;
		case 'fan': return <FanView {...p} />;
		case 'digits': return <DigitsView {...p} />;
		case 'wires': return <WiresView {...p} />;
		default: return null;
	}
};

const Wiped: React.FC<{W: number; H: number; on: boolean; children: React.ReactNode}> = ({W, H, on, children}) => {
	const f = useCurrentFrame();
	if (!on || f >= WIPE) return <AbsoluteFill>{children}</AbsoluteFill>;
	const p = f / WIPE;
	return <AbsoluteFill style={{clipPath: wipeClip(p, W, H)}}>{children}</AbsoluteFill>;
};

export const V2: React.FC<{name: string; data?: any; debug?: string}> = ({data}) => {
	const ready = useFontsReady(data.fonts);
	const f = useCurrentFrame();
	const {fps} = useVideoConfig();
	if (!ready) return <AbsoluteFill style={{background: C.night}} />;
	const W = data.W,
		H = data.H;
	const short = H > W;
	const band = data.band;
	const SX = short ? band[0] : 0,
		SY = short ? band[1] : 0,
		SW = short ? band[2] : W,
		SH = short ? band[3] : H;
	// the 9:16 band is square: the code-drawn objects are drawn larger there so they read on a phone
	const u = short ? Math.min(SW / 1400, SH / 800) : Math.min(SW / 1920, SH / 1080);
	const t = f / fps;
	const wipeAt = new Set((data.wipes || []).map((x: number) => Math.round(x * fps)));
	const shots = data.shots;
	const cur = shots.find((s: any) => t >= s.start && t < s.end) || shots[shots.length - 1];
	const breathe = 0.16 + 0.03 * Math.sin(t * 0.9);
	return (
		<AbsoluteFill style={{background: short ? '#0A1320' : C.night}}>
			{short ? <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 45%, #15253C 0%, #0A1320 70%)'}} /> : null}
			<div style={{position: 'absolute', left: SX, top: SY, width: SW, height: SH, overflow: 'hidden', zIndex: 0}}>
				{shots.map((s: any, i: number) => {
					const from = Math.round(s.start * fps);
					const next = shots[i + 1];
					const nextWipe = next && wipeAt.has(Math.round(next.start * fps));
					const to = Math.round(s.end * fps) + (nextWipe ? WIPE : 0);
					const dur = s.end - s.start;
					return (
						<Sequence key={s.id} from={from} durationInFrames={Math.max(1, to - from)} layout="none">
							<div style={{position: 'absolute', left: 0, top: 0, width: SW, height: SH, zIndex: i}}>
								<Wiped W={SW} H={SH} on={wipeAt.has(from)}>
									<ShotBody s={s} SW={SW} SH={SH} u={u} dur={dur} short={short} band={band} />
								</Wiped>
							</div>
						</Sequence>
					);
				})}
				<AbsoluteFill style={{pointerEvents: 'none', background: `radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0) 55%, rgba(0,0,0,${breathe * 2.2}) 100%)`, zIndex: 900}} />
			</div>
			<div style={{position: 'absolute', left: 0, top: 0, width: W, height: H, zIndex: 10}}>
			{cur && cur.kind === 'archive' ? <CaptionPlate text={cur.caption} W={W} H={H} short={short} t={t - cur.start} /> : null}
			{cur && cur.clock && !(cur.kind === 'missing' && cur.title && t - cur.start < 2.0) ? <Clock label={cur.clock} W={W} H={H} t={t} /> : null}
			<Subs caps={data.captions} W={W} H={H} t={t} short={short} />
			</div>
		</AbsoluteFill>
	);
};
