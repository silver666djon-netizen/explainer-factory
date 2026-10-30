// CoinSense motion study: a demo reel of the techniques adopted from the Remotion / HyperFrames study, each applied to
// an existing Ep.4 beat (same r90 narration + music, same pictures, palette and fonts). Corner tag = the technique.
import React, {useEffect, useState} from 'react';
import {AbsoluteFill, Audio, Easing, Img, continueRender, delayRender, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import type {TransitionPresentation, TransitionPresentationComponentProps} from '@remotion/transitions';
import {evolvePath, getLength, getPointAtLength, getTangentAtLength} from '@remotion/paths';
import {CameraMotionBlur} from '@remotion/motion-blur';
import {noise2D} from '@remotion/noise';
import {fitText, measureText} from '@remotion/layout-utils';
import {createTikTokStyleCaptions} from '@remotion/captions';
import type {Caption} from '@remotion/captions';
import {ImageShotView, Segment, StatView, ChartView, TextEl, camera, clamp, ease, fontFam} from './Piece';

const PAL = {paper: '#F3E9D2', ink: '#1E1B18', green: '#2E6B4F', red: '#D2452F', accent: '#E8B53A'};
const HEAD = 'Anton-Regular';
const BODY = 'ArchivoBlack-Regular';
const SERIF = 'PT-Serif-Web-Regular';
const TYPE = 'SpecialElite-Regular';

// ------------------------------------------------------------------ fonts: render nothing until they are loaded
const useFontsReady = (fonts: Record<string, string>) => {
	const [handle] = useState(() => delayRender('reel fonts'));
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

// ------------------------------------------------------------------ the corner tag
const Tag: React.FC<{n: number; text: string; W: number; H: number}> = ({n, text, W, H}) => {
	const f = useCurrentFrame();
	const portrait = H > W;
	const fs = Math.round((portrait ? W : H) * (portrait ? 0.024 : 0.019));
	const a = interpolate(f, [0, 8], [0, 1], {extrapolateRight: 'clamp'});
	return (
		<div
			style={{
				position: 'absolute', left: Math.round(W * 0.016), top: Math.round(portrait ? H * 0.952 : H * 0.022), opacity: a,
				display: 'flex', alignItems: 'stretch', fontFamily: fontFam(BODY), fontSize: fs, letterSpacing: 0.5,
				boxShadow: '0 3px 10px rgba(0,0,0,0.35)',
			}}
		>
			<div style={{background: PAL.red, color: PAL.paper, padding: `${fs * 0.35}px ${fs * 0.5}px`}}>{String(n).padStart(2, '0')}</div>
			<div style={{background: 'rgba(30,27,24,0.88)', color: PAL.paper, padding: `${fs * 0.35}px ${fs * 0.6}px`}}>{text}</div>
		</div>
	);
};

// ------------------------------------------------------------------ subtitles from word timing (@remotion/captions)
const toCaptions = (words: [string, number, number][], t0: number): Caption[] =>
	words.map(([w, s, e], i) => ({text: (i ? ' ' : '') + w, startMs: Math.round((s - t0) * 1000), endMs: Math.round((e - t0) * 1000), timestampMs: null, confidence: null}));

const Subtitles: React.FC<{words: [string, number, number][]; t0: number; W: number; H: number; sweep?: boolean}> = ({words, t0, W, H, sweep}) => {
	const f = useCurrentFrame();
	const {fps} = useVideoConfig();
	const ms = (f / fps) * 1000;
	const portrait = H > W;
	const {pages} = createTikTokStyleCaptions({captions: toCaptions(words, t0), combineTokensWithinMilliseconds: portrait ? 900 : 1500});
	const pi = pages.findIndex((p, i) => ms >= p.startMs && (i === pages.length - 1 || ms < pages[i + 1].startMs));
	if (pi < 0) return null;
	const page = pages[pi];
	const lastEnd = page.tokens[page.tokens.length - 1].toMs;
	if (pi === pages.length - 1 && ms > lastEnd + 600) return null;
	const font = portrait ? HEAD : BODY;
	const toks = page.tokens.map((t) => ({...t, text: portrait ? t.text.toUpperCase() : t.text}));
	let size = Math.round(H * (portrait ? 0.05 : 0.052) * (sweep ? 1.15 : 1));
	const full = toks.map((t) => t.text).join('');
	const fit = fitText({text: full, withinWidth: W * 0.86, fontFamily: font});
	size = Math.min(size, Math.floor(fit.fontSize));
	const widths = toks.map((t) => measureText({text: t.text, fontFamily: font, fontSize: size}).width);
	const total = widths.reduce((a, b) => a + b, 0);
	const x0 = (W - total) / 2;
	const ai = Math.max(0, toks.findIndex((t, i) => ms >= t.fromMs && (i === toks.length - 1 || ms < toks[i + 1].fromMs)));
	const starts = widths.map((_, i) => widths.slice(0, i).reduce((a, b) => a + b, 0));
	const lead = (txt: string) => measureText({text: txt.match(/^\s*/)![0] || '', fontFamily: font, fontSize: size}).width;
	// the highlight box glides from word to word (spring on the change), it never jumps
	const prev = Math.max(0, ai - 1);
	const tChange = toks[ai].fromMs;
	const k = spring({frame: Math.max(0, ((ms - tChange) / 1000) * fps), fps, config: {damping: 18, stiffness: 220}});
	const bx = interpolate(k, [0, 1], [starts[prev] + lead(toks[prev].text), starts[ai] + lead(toks[ai].text)]);
	const bw = interpolate(k, [0, 1], [widths[prev] - lead(toks[prev].text), widths[ai] - lead(toks[ai].text)]);
	const y = H * (portrait ? 0.78 : 0.86) - size * 0.62;
	const stroke = Math.max(3, Math.round(size / 9));
	return (
		<div style={{position: 'absolute', left: 0, top: y, width: W, height: size * 1.3}}>
			{sweep ? (
				<div style={{position: 'absolute', left: x0 + bx - size * 0.14, top: size * 0.06, width: bw + size * 0.28, height: size * 1.18, background: PAL.accent, borderRadius: size * 0.18, transform: 'rotate(-1.2deg)'}} />
			) : null}
			{toks.map((t, i) => (
				<span
					key={i}
					style={{
						position: 'absolute', left: x0 + starts[i], top: 0, whiteSpace: 'pre', fontFamily: fontFam(font), fontSize: size, lineHeight: 1.3,
						color: sweep ? (i === ai ? PAL.ink : '#fff') : i === ai ? PAL.accent : '#fff',
						WebkitTextStroke: sweep && i === ai ? undefined : `${stroke * 2}px ${PAL.ink}`, paintOrder: 'stroke fill',
					}}
				>
					{t.text}
				</span>
			))}
		</div>
	);
};

// ------------------------------------------------------------------ 02 number card: spring stamp, press ghost, synced hit
const SpringStat: React.FC<any> = ({sh, local, W, H}) => {
	const {fps} = useVideoConfig();
	const fr = Math.max(0, local * fps);
	const s = spring({frame: fr, fps, config: {damping: 10, stiffness: 190, mass: 0.8}});
	const sc = interpolate(s, [0, 1], [1.55, 1]);
	const hit = Math.exp(-local * 16) * Math.sin(local * 95) * H * 0.006 * (local < 0.35 ? 1 : 0); // the frame jolts with the brass stab
	const ghost = clamp(1 - local / 0.45, 0, 1);
	const n = sh.numEl;
	const yNum = Math.floor(H * 0.42) - Math.floor(sh.numH / 2);
	const lab = spring({frame: fr - 5, fps, config: {damping: 200}});
	const breathe = 0.1 + 0.05 * Math.sin((local / 3) * Math.PI * 2);
	return (
		<AbsoluteFill style={{transform: `translateY(${hit}px)`}}>
			<Img src={staticFile(sh.bg)} style={{position: 'absolute', left: 0, top: 0, width: W, height: H, transform: `scale(${1 + 0.02 * local})`}} />
			{sh.label ? (
				<div style={{position: 'absolute', left: Math.floor((W - sh.label.w) / 2), top: yNum + sh.numH + Math.floor(H * 0.02) + (1 - lab) * 18, opacity: lab}}>
					<TextEl d={sh.label} />
				</div>
			) : null}
			{ghost > 0 ? (
				<div style={{position: 'absolute', left: (W - n.w) / 2, top: H * 0.42 - n.h / 2, transform: `scale(${1 + 0.06 * (1 - ghost)})`, opacity: 0.35 * ghost, filter: 'blur(6px)'}}>
					<TextEl d={n} />
				</div>
			) : null}
			<div style={{position: 'absolute', left: (W - n.w) / 2, top: H * 0.42 - n.h / 2, transform: `scale(${sc}) rotate(${(1 - s) * -3}deg)`, transformOrigin: '50% 50%'}}>
				<TextEl d={n} />
			</div>
			<AbsoluteFill style={{background: `radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(30,27,24,${breathe}) 100%)`}} />
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 03 chart: staggered eased build, drawn grid, value pops
const SpringChart: React.FC<any> = ({sh, local, W, H}) => {
	const {fps} = useVideoConfig();
	const [x0, y0, x1, y1] = sh.area;
	const vals = sh.values.map(Number);
	const vmax = Math.max(...vals) * 1.15 || 1;
	const n = vals.length;
	const slot = (x1 - x0) / n;
	const bw = slot * 0.62;
	const grid = [0.25, 0.5, 0.75, 1].map((g) => y1 - (y1 - y0) * g * (Math.max(...vals) / vmax));
	return (
		<AbsoluteFill>
			<Img src={staticFile(sh.bg)} style={{position: 'absolute', left: 0, top: 0, width: W, height: H}} />
			<div style={{position: 'absolute', left: sh.title.x, top: sh.title.y}}>
				<TextEl d={sh.title} />
			</div>
			<svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0}}>
				{grid.map((gy, i) => {
					const d = `M ${x0} ${gy} L ${x1} ${gy}`;
					const ev = evolvePath(clamp((local - i * 0.06) / 0.6, 0, 1), d);
					return <path key={i} d={d} stroke="rgba(30,27,24,0.18)" strokeWidth={2} strokeDasharray={ev.strokeDasharray} strokeDashoffset={ev.strokeDashoffset} />;
				})}
				<line x1={x0} y1={y1} x2={x1} y2={y1} stroke={sh.pal.ink} strokeWidth={sh.axisW} />
				{vals.map((v: number, i: number) => {
					const d0 = 0.15 + i * 0.14; // left to right, a beat apart
					const p = spring({frame: (local - d0) * fps, fps, config: {damping: 200}, durationInFrames: Math.round(sh.grow * fps)}); // no overshoot: a bar never shrinks (rule 35)
					const bx = x0 + slot * i + (slot - bw) / 2;
					const top = y1 - (y1 - y0) * (v / vmax) * p;
					const color = sh.highlight !== null && i === sh.highlight ? sh.pal.red : sh.pal.green;
					const landed = d0 + sh.grow * 0.85;
					const pop = spring({frame: (local - landed) * fps, fps, config: {damping: 9, stiffness: 200}});
					return (
						<g key={i}>
							{p > 0.002 ? <rect x={bx + 1.5} y={top + 1.5} width={bw - 3} height={Math.max(0, y1 - top - 3)} fill={color} stroke={sh.pal.ink} strokeWidth={3} /> : null}
							<text x={bx + bw / 2} y={y1 + 12 + sh.labAsc} textAnchor="middle" fontFamily={fontFam(sh.labFont)} fontSize={sh.labSize} fill={sh.pal.ink}>
								{sh.labels[i]}
							</text>
							{local > landed ? (
								<g transform={`translate(${bx + bw / 2} ${top - 8}) scale(${0.6 + 0.4 * pop})`} opacity={clamp(pop * 1.4, 0, 1)}>
									<text x={0} y={-sh.valDesc} textAnchor="middle" fontFamily={fontFam(sh.valFont)} fontSize={sh.valSize} fill={sh.pal.ink}>
										{sh.fmt[i]}
									</text>
								</g>
							) : null}
						</g>
					);
				})}
			</svg>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 04 kinetic chapter title: fitText, word springs, drawn rule
const TitleView: React.FC<{s: any; W: number; H: number}> = ({s, W, H}) => {
	const f = useCurrentFrame();
	const {fps} = useVideoConfig();
	const t = f / fps;
	const portrait = H > W;
	const lines: string[] = portrait ? s.title.split(', ').map((l: string, i: number, a: string[]) => (i < a.length - 1 ? l + ',' : l)) : [s.title];
	const sizes = lines.map((l) => Math.min(H * (portrait ? 0.12 : 0.2), fitText({text: l, withinWidth: W * 0.84, fontFamily: HEAD}).fontSize));
	const size = Math.min(...sizes);
	const lh = size * 1.02;
	const kick = Math.round(size * 0.24);
	const top = H * 0.46 - (lines.length * lh) / 2;
	let wi = 0;
	const ruleY = top + lines.length * lh + size * 0.12;
	const ruleW = Math.max(...lines.map((l) => measureText({text: l, fontFamily: HEAD, fontSize: size}).width));
	const rule = `M ${(W - ruleW) / 2} ${ruleY} C ${W / 2 - ruleW / 4} ${ruleY + 6}, ${W / 2 + ruleW / 4} ${ruleY - 6}, ${(W + ruleW) / 2} ${ruleY + 2}`;
	const nWords = lines.join(' ').split(' ').length;
	const ev = evolvePath(clamp((t - 0.25 - nWords * 0.07) / 0.45, 0, 1), rule);
	const track = interpolate(t, [0, 0.8], [0.6, 0.18], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
	return (
		<AbsoluteFill>
			<Img src={staticFile(s.sun)} style={{position: 'absolute', left: 0, top: 0, width: W, height: H, transform: `scale(${1.02 + 0.03 * t}) rotate(${0.4 * t}deg)`}} />
			<div style={{position: 'absolute', top: top - kick * 2, width: W, textAlign: 'center', fontFamily: fontFam(BODY), fontSize: kick, color: PAL.red, letterSpacing: `${track}em`, opacity: clamp(t / 0.3, 0, 1)}}>
				{s.kicker}
			</div>
			{lines.map((l, li) => {
				const ws = l.split(' ');
				const lw = measureText({text: l, fontFamily: HEAD, fontSize: size}).width;
				let x = (W - lw) / 2;
				const space = measureText({text: ' ', fontFamily: HEAD, fontSize: size}).width;
				return ws.map((w) => {
					const k = spring({frame: f - (0.12 + wi++ * 0.07) * fps, fps, config: {damping: 14, stiffness: 160}});
					const ww = measureText({text: w, fontFamily: HEAD, fontSize: size}).width;
					const el = (
						<div
							key={`${li}-${x}`}
							style={{
								position: 'absolute', left: x, top: top + li * lh, fontFamily: fontFam(HEAD), fontSize: size, lineHeight: `${lh}px`, color: PAL.ink,
								opacity: clamp(k * 1.5, 0, 1), transform: `translateY(${(1 - k) * size * 0.35}px)`, whiteSpace: 'pre',
							}}
						>
							{w}
						</div>
					);
					x += ww + space;
					return el;
				});
			})}
			<svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0}}>
				<path d={rule} fill="none" stroke={PAL.red} strokeWidth={Math.max(6, size * 0.06)} strokeLinecap="round" strokeDasharray={ev.strokeDasharray} strokeDashoffset={ev.strokeDashoffset} />
			</svg>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 05 route: three borders on a print map
const wordAt = (words: [string, number, number][], w: string, t0: number) => {
	const hit = words.find((x) => x[0].replace(/[^\w']/g, '').toLowerCase() === w.toLowerCase());
	return hit ? hit[1] - t0 : 0;
};
const RouteView: React.FC<{s: any; W: number; H: number}> = ({s, W, H}) => {
	const f = useCurrentFrame();
	const {fps} = useVideoConfig();
	const t = f / fps;
	const portrait = H > W;
	const posts = portrait
		? [[W * 0.3, H * 0.25], [W * 0.7, H * 0.45], [W * 0.32, H * 0.64]]
		: [[W * 0.2, H * 0.42], [W * 0.5, H * 0.3], [W * 0.8, H * 0.46]];
	const start: [number, number] = portrait ? [-W * 0.1, H * 0.12] : [-W * 0.05, H * 0.62];
	const end: [number, number] = portrait ? [W * 1.1, H * 0.72] : [W * 1.05, H * 0.66];
	const pts = [start, ...posts, end];
	let d = `M ${pts[0][0]} ${pts[0][1]}`;
	for (let i = 1; i < pts.length; i++) {
		const [ax, ay] = pts[i - 1];
		const [bx, by] = pts[i];
		d += ` C ${ax + (bx - ax) * 0.5} ${ay - H * 0.08}, ${ax + (bx - ax) * 0.5} ${by + H * 0.08}, ${bx} ${by}`;
	}
	const L = getLength(d);
	const ta = wordAt(s.words, 'trip', s.t0) - 0.4;
	const tb = wordAt(s.words, 'stamps', s.t0) + 0.3;
	const p = interpolate(t, [ta, tb], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.sin)});
	const ev = evolvePath(p, d);
	const pt = getPointAtLength(d, p * L);
	const tg = getTangentAtLength(d, Math.min(L - 1, p * L + 1));
	const ang = (Math.atan2(tg.y, tg.x) * 180) / Math.PI;
	// where each post sits along the route
	const postP = posts.map(([px, py]) => {
		let best = 0,
			bd = 1e9;
		for (let k = 0; k <= 200; k++) {
			const q = getPointAtLength(d, (k / 200) * L);
			const dd = Math.hypot(q.x - px, q.y - py);
			if (dd < bd) {
				bd = dd;
				best = k / 200;
			}
		}
		return best;
	});
	const names = ['USA', 'UK', 'EU'];
	const stamps = ['TOTAL UPFRONT', 'ALL FEES IN', 'TOTAL BEFORE YOU PAY'];
	const tw = (portrait ? W * 0.3 : W * 0.15);
	const th = tw * (440 / 960);
	const fs = Math.round(Math.min(W, H) * 0.045);
	return (
		<AbsoluteFill style={{background: PAL.paper}}>
			<svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0}}>
				{Array.from({length: 9}).map((_, i) => (
					<path key={`m${i}`} d={`M ${(i + 0.5) * W / 9 - W * 0.03} 0 Q ${(i + 0.5) * W / 9 + W * 0.02} ${H / 2} ${(i + 0.5) * W / 9 - W * 0.03} ${H}`} fill="none" stroke="rgba(46,107,79,0.13)" strokeWidth={2} />
				))}
				{Array.from({length: 6}).map((_, i) => (
					<path key={`p${i}`} d={`M 0 ${(i + 0.5) * H / 6} Q ${W / 2} ${(i + 0.5) * H / 6 - H * 0.03} ${W} ${(i + 0.5) * H / 6}`} fill="none" stroke="rgba(46,107,79,0.13)" strokeWidth={2} />
				))}
				<rect x={W * 0.02} y={H * 0.03} width={W * 0.96} height={H * 0.94} fill="none" stroke="rgba(30,27,24,0.35)" strokeWidth={3} />
				<rect x={W * 0.028} y={H * 0.045} width={W * 0.944} height={H * 0.91} fill="none" stroke="rgba(30,27,24,0.2)" strokeWidth={1.5} />
				<path d={d} fill="none" stroke="rgba(30,27,24,0.15)" strokeWidth={4} strokeDasharray="2 14" strokeLinecap="round" />
				<mask id="route-reveal">
					<path d={d} fill="none" stroke="#fff" strokeWidth={14} strokeDasharray={ev.strokeDasharray} strokeDashoffset={ev.strokeDashoffset} />
				</mask>
				<path d={d} fill="none" stroke={PAL.red} strokeWidth={6} strokeDasharray="18 12" strokeLinecap="round" mask="url(#route-reveal)" />
			</svg>
			{posts.map(([px, py], i) => {
				const arrive = interpolate(postP[i], [0, 1], [ta, tb]);
				const k = spring({frame: f - arrive * fps, fps, config: {damping: 11, stiffness: 180}});
				const pin = spring({frame: f - (0.15 + i * 0.12) * fps, fps, config: {damping: 200}});
				return (
					<React.Fragment key={i}>
						<div style={{position: 'absolute', left: px - fs * 2.2, top: py - fs * 2.6, width: fs * 4.4, textAlign: 'center', opacity: pin, transform: `translateY(${(1 - pin) * 20}px)`}}>
							<div style={{display: 'inline-block', background: PAL.ink, color: PAL.paper, fontFamily: fontFam(HEAD), fontSize: fs, padding: `${fs * 0.1}px ${fs * 0.5}px`, letterSpacing: 2}}>
								{names[i]}
							</div>
						</div>
						<svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0}}>
							<circle cx={px} cy={py} r={fs * 0.28} fill={PAL.paper} stroke={PAL.ink} strokeWidth={4} opacity={pin} />
						</svg>
						{t >= arrive ? (
							<div
								style={{
									position: 'absolute', left: px - fs * 3.2, top: py + fs * 0.7, width: fs * 6.4, textAlign: 'center',
									transform: `scale(${interpolate(k, [0, 1], [1.9, 1])}) rotate(${-6 + i * 4}deg)`, opacity: clamp(k * 2, 0, 1),
								}}
							>
								<span style={{display: 'inline-block', border: `${Math.max(3, fs * 0.09)}px solid ${PAL.red}`, color: PAL.red, fontFamily: fontFam(HEAD), fontSize: fs * 0.62, padding: `${fs * 0.08}px ${fs * 0.3}px`, letterSpacing: 1, background: 'rgba(243,233,210,0.85)'}}>
									{stamps[i]}
								</span>
							</div>
						) : null}
					</React.Fragment>
				);
			})}
			<div
				style={{
					position: 'absolute', left: pt.x - tw / 2, top: pt.y - th / 2, width: tw, height: th, overflow: 'hidden',
					transform: `rotate(${clamp(ang, -14, 14)}deg)`, boxShadow: '0 8px 18px rgba(0,0,0,0.35)', opacity: p > 0 ? 1 : interpolate(t, [0, 0.4], [0, 1], {extrapolateRight: 'clamp'}),
				}}
			>
				<Img src={staticFile(s.ticket)} style={{position: 'absolute', width: tw * (s.ticketSize[0] / 960), left: -tw * (83 / 960), top: -th * (170 / 440)}} />
			</div>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 06 parallax from one still: foreground moves more than the room
const ParallaxView: React.FC<{s: any; W: number; H: number; dur: number}> = ({s, W, H, dur}) => {
	const f = useCurrentFrame();
	const {fps} = useVideoConfig();
	const p = interpolate(f / fps, [0, dur], [0, 1], {easing: Easing.inOut(Easing.sin)});
	const [iw, ih] = s.size;
	const sc = Math.max(W / iw, H / ih) * 1.12;
	const [ax, ay] = s.feet; // Larry's feet (fractions of the picture): both layers grow about them
	const w0 = iw * sc,
		h0 = ih * sc;
	const left0 = W * (H > W ? 0.5 : 0.5) - w0 * (H > W ? ax : 0.5);
	const top0 = (H - h0) / 2;
	const origin = `${ax * 100}% ${ay * 100}%`;
	const lay = {position: 'absolute' as const, left: left0, top: top0, width: w0, height: h0, transformOrigin: origin};
	return (
		<AbsoluteFill>
			<Img src={staticFile(s.bg)} style={{...lay, transform: `scale(${1 + 0.012 * p}) translateX(${-0.004 * w0 * p}px)`}} />
			<Img src={staticFile(s.fg)} style={{...lay, transform: `scale(${1 + 0.055 * p})`}} />
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 07 evidence card: paper, ink texture, noise wobble, highlighter
const EvidenceView: React.FC<{s: any; W: number; H: number}> = ({s, W, H}) => {
	const f = useCurrentFrame();
	const {fps} = useVideoConfig();
	const t = f / fps;
	const portrait = H > W;
	const doc = s.doc;
	const cw = portrait ? W * 0.86 : W * 0.56;
	const pad = cw * 0.07;
	const rot = -1.3 + noise2D('card-rot', t * 0.22, 0) * 0.45;
	const dx = noise2D('card-x', t * 0.3, 1) * 3;
	const dy = noise2D('card-y', 2, t * 0.3) * 3;
	const ton = wordAt(s.words, 'marketexpanding', s.t0) || 3.5;
	const push = interpolate(t, [ton - 0.3, ton + 1.6], [1, 1.07], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});
	const hp = interpolate(t, [ton, ton + 1.3], [0, 100], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.quad)});
	const [pre, post] = doc.body.split(doc.highlight);
	const bodyFs = cw * 0.042;
	const enter = spring({frame: f, fps, config: {damping: 200}});
	return (
		<AbsoluteFill style={{background: `radial-gradient(ellipse at 50% 40%, #2f5a43 0%, #1c3a2b 70%, #142a1f 100%)`}}>
			<svg width={0} height={0} style={{position: 'absolute'}}>
				<filter id="ink-bleed">
					<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} seed={7} result="n" />
					<feDisplacementMap in="SourceGraphic" in2="n" scale={1.6} />
				</filter>
				<filter id="paper-fibre" x="0" y="0" width="100%" height="100%">
					<feTurbulence type="fractalNoise" baseFrequency="0.035 0.6" numOctaves={3} seed={11} />
					<feColorMatrix type="matrix" values="0 0 0 0 0.45  0 0 0 0 0.38  0 0 0 0 0.25  0 0 0 0.10 0" />
				</filter>
			</svg>
			<div
				style={{
					position: 'absolute', left: (W - cw) / 2 + dx, top: H * (portrait ? 0.24 : 0.17) + dy + (1 - enter) * 40, width: cw,
					transform: `rotate(${rot}deg) scale(${push})`, transformOrigin: '50% 40%', background: '#FAF6EC', padding: pad,
					boxShadow: '0 22px 40px rgba(0,0,0,0.45), 0 2px 0 rgba(0,0,0,0.08)', opacity: enter,
				}}
			>
				<svg width="100%" height="100%" style={{position: 'absolute', left: 0, top: 0}}>
					<rect width="100%" height="100%" filter="url(#paper-fibre)" />
				</svg>
				<div style={{fontFamily: fontFam(TYPE), fontSize: bodyFs * 0.62, color: PAL.red, letterSpacing: 1, marginBottom: bodyFs * 0.4}}>{doc.kicker}</div>
				<div style={{fontFamily: fontFam(SERIF), fontSize: bodyFs * 1.45, color: PAL.ink, marginBottom: bodyFs * 0.5, filter: 'url(#ink-bleed)'}}>{doc.headline}</div>
				<div style={{height: 2, background: 'rgba(30,27,24,0.35)', marginBottom: bodyFs * 0.7}} />
				<div style={{fontFamily: fontFam(SERIF), fontSize: bodyFs, lineHeight: 1.5, color: '#2a2622', filter: 'url(#ink-bleed)'}}>
					{pre}
					<span
						style={{
							backgroundImage: `linear-gradient(transparent 12%, rgba(232,181,58,0.62) 12%, rgba(232,181,58,0.62) 88%, transparent 88%)`,
							backgroundRepeat: 'no-repeat', backgroundSize: `${hp}% 100%`, WebkitBoxDecorationBreak: 'clone', boxDecorationBreak: 'clone' as any,
						}}
					>
						{doc.highlight}
					</span>
					{post}
				</div>
				<div style={{marginTop: bodyFs * 0.8, fontFamily: fontFam(TYPE), fontSize: bodyFs * 0.55, color: 'rgba(30,27,24,0.65)'}}>{doc.source}</div>
			</div>
			<div
				style={{
					position: 'absolute', left: (W + cw) / 2 - cw * 0.26 + dx, top: H * (portrait ? 0.215 : 0.13) + dy, transform: `rotate(${8 + rot}deg)`,
					background: PAL.red, color: PAL.paper, fontFamily: fontFam(HEAD), fontSize: cw * 0.06, padding: `${cw * 0.008}px ${cw * 0.03}px ${cw * 0.008}px ${cw * 0.055}px`,
					boxShadow: '0 6px 12px rgba(0,0,0,0.4)', opacity: enter, letterSpacing: 2,
				}}
			>
				<div style={{position: 'absolute', left: cw * 0.016, top: '50%', width: cw * 0.022, height: cw * 0.022, marginTop: -cw * 0.011, borderRadius: '50%', background: '#1c3a2b', border: `3px solid ${PAL.paper}`}} />
				EVIDENCE
			</div>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 08 karaoke: the picture with a slow push, word-box captions
const KaraokeView: React.FC<{s: any; W: number; H: number; dur: number}> = ({s, W, H, dur}) => {
	const f = useCurrentFrame();
	const {fps} = useVideoConfig();
	const z = 1.0 + 0.07 * (f / fps / dur);
	const [iw, ih] = s.picSize;
	const portrait = H > W;
	const sc = portrait ? W / ih : Math.max(W / iw, H / ih);
	return (
		<AbsoluteFill style={{background: '#14110f'}}>
			<div style={{position: 'absolute', left: 0, top: portrait ? H * 0.17 : 0, width: W, height: portrait ? W : H, overflow: 'hidden'}}>
				<Img src={staticFile(s.pic)} style={{position: 'absolute', width: iw * sc, height: ih * sc, left: (W - iw * sc) / 2, top: ((portrait ? W : H) - ih * sc) / 2, transform: `scale(${z})`, transformOrigin: '45% 45%'}} />
			</div>
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ 10 camera motion blur on a fast push (archive photo)
const whip = (sh: any, local: number) => {
	const q = clamp(local / 0.5, 0, 1);
	const zq = Easing.inOut(Easing.cubic)(q);
	const z = local < 0.5 ? 1.0 + 0.16 * zq : 1.16 + 0.07 * ((local - 0.5) / Math.max(0.5, sh.duration - 0.5));
	const winW = sh.BW / z;
	const s = sh.W / winW;
	return {s, tx: sh.W / 2 - (s * sh.BW) / 2, ty: sh.H / 2 - (s * sh.BH) / 2};
};
const BlurPicture: React.FC<{seg: any; W: number; H: number}> = ({seg, W, H}) => {
	const f = useCurrentFrame();
	const {fps} = useVideoConfig();
	const sh = {...seg.shots[0], start: seg.t0, duration: seg.frames / fps};
	return <ImageShotView sh={sh} local={f / fps} FW={W} FH={H} debug="none" id="blur" cam={whip} />;
};
const OpsLayer: React.FC<{seg: any}> = ({seg}) => {
	const f = useCurrentFrame();
	const ops = seg.ops[Math.min(f, seg.ops.length - 1)] || [];
	return (
		<>
			{ops.map((o: any[], i: number) => (
				<div key={i} style={{position: 'absolute', left: o[1], top: o[2], opacity: o[3], transform: `scale(${o[4]})`, transformOrigin: '0 0'}}>
					<TextEl d={seg.elements[o[0]]} />
				</div>
			))}
		</>
	);
};

// ------------------------------------------------------------------ 09 the print-style ink wipe (custom transition presentation)
const InkWipeComp: React.FC<TransitionPresentationComponentProps<{W: number; H: number}>> = ({children, presentationDirection, presentationProgress, passedProps}) => {
	const {W, H} = passedProps;
	if (presentationDirection === 'exiting') return <AbsoluteFill>{children}</AbsoluteFill>;
	const p = Easing.inOut(Easing.cubic)(presentationProgress);
	const pts: string[] = [];
	const edge: [number, number][] = [];
	for (let y = -20; y <= H + 20; y += 10) {
		const x = p * (W + 320) - 160 + noise2D('wipe', y / 260, 0) * 34 + noise2D('wipe2', y / 40, 3) * 6 + (y / H) * 120 - 60;
		edge.push([x, y]);
	}
	pts.push('0px -20px', ...edge.map(([x, y]) => `${x}px ${y}px`), `0px ${H + 20}px`);
	return (
		<AbsoluteFill>
			<AbsoluteFill style={{clipPath: `polygon(${pts.join(',')})`}}>{children}</AbsoluteFill>
			<svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0}}>
				<polyline points={edge.map(([x, y]) => `${x},${y}`).join(' ')} fill="none" stroke={PAL.ink} strokeWidth={14} strokeLinejoin="round" opacity={0.9} />
				<polyline points={edge.map(([x, y]) => `${x - 12},${y}`).join(' ')} fill="none" stroke={PAL.red} strokeWidth={5} strokeLinejoin="round" opacity={0.85} />
			</svg>
		</AbsoluteFill>
	);
};
const inkWipe = (W: number, H: number): TransitionPresentation<{W: number; H: number}> => ({component: InkWipeComp, props: {W, H}});
export const WIPE_FRAMES = 18;

// ------------------------------------------------------------------ the reel
const SegmentView: React.FC<{s: any; R: any; i: number}> = ({s, R, i}) => {
	const W = R.W,
		H = R.H;
	const dur = s.frames / R.fps;
	const piece = {W, H, fps: R.fps, vignette: R.vignette};
	let body: React.ReactNode = null;
	if (s.kind === 'piece') body = <Segment seg={s.seg} piece={piece} debug="none" id={`r${i}`} />;
	else if (s.kind === 'stat') body = <Segment seg={s.seg} piece={piece} debug="none" id={`r${i}`} v={{stat: SpringStat}} />;
	else if (s.kind === 'chart') body = <Segment seg={s.seg} piece={piece} debug="none" id={`r${i}`} v={{chart: SpringChart}} />;
	else if (s.kind === 'blurpush')
		body = (
			<AbsoluteFill style={{background: PAL.paper}}>
				<CameraMotionBlur shutterAngle={200} samples={10}>
					<BlurPicture seg={s.seg} W={W} H={H} />
				</CameraMotionBlur>
				<Img src={staticFile(R.vignette)} style={{position: 'absolute', left: 0, top: 0, width: W, height: H}} />
				<OpsLayer seg={s.seg} />
			</AbsoluteFill>
		);
	else {
		const inner =
			s.kind === 'title' ? <TitleView s={s} W={W} H={H} /> :
			s.kind === 'route' ? <RouteView s={s} W={W} H={H} /> :
			s.kind === 'parallax' ? <ParallaxView s={s} W={W} H={H} dur={dur} /> :
			s.kind === 'evidence' ? <EvidenceView s={s} W={W} H={H} /> :
			s.kind === 'karaoke' ? <KaraokeView s={s} W={W} H={H} dur={dur} /> : null;
		body = (
			<AbsoluteFill style={{background: PAL.paper}}>
				{inner}
				{s.kind !== 'evidence' ? <Img src={staticFile(R.vignette)} style={{position: 'absolute', left: 0, top: 0, width: W, height: H}} /> : null}
				<Subtitles words={s.words} t0={s.t0} W={W} H={H} sweep={s.kind === 'karaoke'} />
			</AbsoluteFill>
		);
	}
	return (
		<AbsoluteFill>
			<Audio src={staticFile(s.audio)} />
			{body}
			<Tag n={i + 1} text={s.tag} W={W} H={H} />
		</AbsoluteFill>
	);
};

export const Reel: React.FC<{name: string; data?: any}> = ({data}) => {
	const ready = useFontsReady(data.fonts);
	if (!ready) return <AbsoluteFill style={{background: PAL.paper}} />;
	const items: React.ReactNode[] = [];
	data.segments.forEach((s: any, i: number) => {
		items.push(
			<TransitionSeries.Sequence key={`s${i}`} durationInFrames={s.frames}>
				<SegmentView s={s} R={data} i={i} />
			</TransitionSeries.Sequence>
		);
		if (s.wipeOut && i < data.segments.length - 1)
			items.push(<TransitionSeries.Transition key={`t${i}`} presentation={inkWipe(data.W, data.H)} timing={linearTiming({durationInFrames: WIPE_FRAMES})} />);
	});
	return (
		<AbsoluteFill style={{background: PAL.ink}}>
			<TransitionSeries>{items}</TransitionSeries>
		</AbsoluteFill>
	);
};
