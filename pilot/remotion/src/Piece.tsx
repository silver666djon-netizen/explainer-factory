// CoinSense Remotion pilot: the overlay layer of Ep.4 r90 drawn as vector (SVG / HTML text) over the same pictures.
// All timing and layout comes from the r90 plan (tools/remotion/export_pilot.py); motion is computed per frame here
// in floating point (no pixel rounding): camera, pen, stroke reveal, pops, the Tab.
import React, {useEffect, useState} from 'react';
import {AbsoluteFill, Audio, Img, Sequence, continueRender, delayRender, staticFile, useCurrentFrame} from 'remotion';

type Pt = [number, number];
const ease = (p: number) => {
	const q = Math.min(1, Math.max(0, p));
	return q * q * (3 - 2 * q);
};
const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));
const fontFam = (f: string) => `'${f}'`;

// ------------------------------------------------------------------ fonts (the same TTF files as the Python engine)
const useFonts = (fonts: Record<string, string>) => {
	const [handle] = useState(() => delayRender('fonts'));
	useEffect(() => {
		Promise.all(
			Object.entries(fonts).map(([file, family]) => {
				const ff = new FontFace(family, `url(${staticFile('fonts/' + file)})`);
				return ff.load().then((f) => (document.fonts as any).add(f));
			})
		)
			.then(() => continueRender(handle))
			.catch((e) => {
				console.error(e);
				continueRender(handle);
			});
	}, []);
};

// ------------------------------------------------------------------ a text plate (text_block): SVG text on the same baselines
export const TextEl: React.FC<{d: any; debugText?: boolean}> = ({d}) => {
	if (d.type === 'raw') return <Img src={staticFile(d.src)} style={{width: d.w, height: d.h, display: 'block'}} />;
	if (d.type === 'card') {
		const iw = d.inner.w + 2 * d.frame;
		const ih = d.inner.h + 2 * d.frame;
		return (
			<div style={{width: d.w, height: d.h, position: 'relative'}}>
				<div
					style={{
						position: 'absolute', left: (d.w - iw) / 2, top: (d.h - ih) / 2, width: iw, height: ih, background: d.red,
						transform: `rotate(${-d.angle}deg)`,
					}}
				>
					<div style={{position: 'absolute', left: d.frame, top: d.frame, width: d.inner.w, height: d.inner.h, background: d.paper}}>
						<TextEl d={d.inner} />
					</div>
				</div>
			</div>
		);
	}
	const sw = d.stroke ? 2 * d.stroke : 0;
	return (
		<svg width={d.w} height={d.h} style={{display: 'block', overflow: 'visible'}}>
			{d.box ? <rect x={0} y={0} width={d.w} height={d.h} rx={d.radius} ry={d.radius} fill={d.box} /> : null}
			{d.lines.map((l: any, i: number) => (
				<text
					key={i}
					y={l.base}
					fontFamily={fontFam(d.font)}
					fontSize={d.size}
					fill={d.fill}
					stroke={sw ? d.strokeFill : undefined}
					strokeWidth={sw || undefined}
					strokeLinejoin="round"
					paintOrder="stroke"
					style={{whiteSpace: 'pre', fontKerning: 'normal'}}
				>
					{l.words ? (
						l.words.map((w: any, j: number) => (
							<tspan key={j} x={w.x} fill={w.c}>
								{w.t}
							</tspan>
						))
					) : (
						<tspan x={l.x}>{l.t}</tspan>
					)}
				</text>
			))}
		</svg>
	);
};

// ------------------------------------------------------------------ camera (factory.shots.ImageShot._matrix, float)
const camera = (sh: any, local: number): {s: number; tx: number; ty: number} => {
	const p = local / Math.max(sh.duration, 1e-6);
	let z = 1,
		dx = 0,
		dy = 0;
	if (sh.zoomLin) {
		z = sh.zoomLin[0] + sh.zoomLin[1] * p * sh.duration;
	} else {
		const e = ease(p);
		const zmax = sh.zmax;
		const m = sh.motion;
		if (m === 'zoom_in') z = 1 + (zmax * 0.98 - 1) * e;
		else if (m === 'zoom_out') z = zmax * 0.98 - (zmax * 0.98 - 1) * e;
		else if (['pan_left', 'pan_right', 'pan_up', 'pan_down'].includes(m)) {
			z = 1.12;
			const travel = 2 * e - 1;
			const sign = m === 'pan_left' || m === 'pan_up' ? 1 : -1;
			if (m === 'pan_left' || m === 'pan_right') dx = -sign * travel;
			else dy = -sign * travel;
		} else if (m === 'drift') {
			z = 1.05 + 0.12 * e;
			dx = 0.6 * (e - 0.5);
			dy = 0.4 * (0.5 - e);
		} else z = 1.02 + 0.06 * p; // static: a slow push so the frame never freezes
	}
	dy += sh.camDy || 0;
	const winW = sh.BW / z,
		winH = sh.BH / z;
	const freeX = (sh.BW - winW) / 2,
		freeY = (sh.BH - winH) / 2;
	const cx = sh.BW / 2 + dx * freeX * 0.95;
	const cy = sh.BH / 2 + dy * freeY * 0.95;
	const s = sh.W / winW;
	return {s, tx: sh.W / 2 - s * cx, ty: sh.H / 2 - s * cy};
};

// ------------------------------------------------------------------ handwriting: strokes, pen path, reveal
const segLen = (a: Pt, b: Pt) => Math.hypot(b[0] - a[0], b[1] - a[1]);
const polyLen = (pts: Pt[]) => pts.slice(1).reduce((acc, p, i) => acc + segLen(pts[i], p), 0);
const pointAt = (pts: Pt[], d: number): Pt => {
	let acc = 0;
	for (let i = 1; i < pts.length; i++) {
		const l = segLen(pts[i - 1], pts[i]);
		if (acc + l >= d) {
			const u = l > 0 ? (d - acc) / l : 0;
			return [pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * u, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * u];
		}
		acc += l;
	}
	return pts[pts.length - 1];
};
const LIFT = 0.6; // a lifted pen travels 1/0.6 x faster than it writes

type Prepared = {strokes: Pt[][]; lens: number[]; starts: number[]; total: number};
const prepare = (m: any): Prepared => {
	if (m._prep) return m._prep;
	const strokes: Pt[][] = m.strokes.filter((s: Pt[]) => s.length > 1);
	const lens = strokes.map(polyLen);
	const starts: number[] = [];
	let acc = 0;
	strokes.forEach((s, i) => {
		if (i > 0) acc += LIFT * segLen(strokes[i - 1][strokes[i - 1].length - 1], s[0]);
		starts.push(acc);
		acc += lens[i];
	});
	m._prep = {strokes, lens, starts, total: Math.max(acc, 1e-6)};
	return m._prep;
};
// progress -> (drawn length per stroke, tip in the mark's own coordinates)
const penState = (m: any, p: number) => {
	const P = prepare(m);
	const d = clamp(p, 0, 1) * P.total;
	const drawn = P.lens.map((l, i) => clamp(d - P.starts[i], 0, l));
	let tip: Pt = P.strokes.length ? P.strokes[0][0] : [0, 0];
	for (let i = 0; i < P.strokes.length; i++) {
		if (d < P.starts[i]) {
			const a = P.strokes[i - 1][P.strokes[i - 1].length - 1];
			const b = P.strokes[i][0];
			const gap = P.starts[i] - (P.starts[i - 1] + P.lens[i - 1]);
			const u = gap > 0 ? (d - (P.starts[i - 1] + P.lens[i - 1])) / gap : 1;
			tip = [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u - Math.sin(u * Math.PI) * 3];
			break;
		}
		tip = pointAt(P.strokes[i], drawn[i]);
		if (d <= P.starts[i] + P.lens[i]) break;
	}
	return {drawn, tip, P};
};
// a write mark's box -> picture (base) px
const boxToBase = (m: any, x: number, y: number): Pt => {
	const a = (m.angle * Math.PI) / 180;
	const u = x - m.bw / 2,
		v = y - m.bh / 2;
	return [m.x + u * Math.cos(a) + v * Math.sin(a), m.y - u * Math.sin(a) + v * Math.cos(a)];
};
const markProgress = (m: any, t: number) => {
	if (m.dur <= 0.05 && t >= m.at - 1e-6) return 1;
	return (t - m.at) / Math.max(m.dur, 1e-3);
};

const strokePaths = (P: Prepared, drawn: number[], width: number, color: string, key: string) =>
	P.strokes.map((s, i) => (
		<path
			key={key + i}
			d={'M' + s.map((q) => `${q[0]} ${q[1]}`).join(' L')}
			fill="none"
			stroke={color}
			strokeWidth={width}
			strokeLinecap="round"
			strokeLinejoin="round"
			strokeDasharray={`${P.lens[i] + 1} ${P.lens[i] + 1}`}
			strokeDashoffset={P.lens[i] + 1 - (drawn[i] >= P.lens[i] - 1e-6 ? P.lens[i] + 1 : drawn[i])}
		/>
	));

const MarksLayer: React.FC<{sh: any; t: number; id: string; white?: boolean}> = ({sh, t, id, white}) => (
	<svg width={sh.BW} height={sh.BH} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
		{sh.marks.map((m: any, k: number) => {
			let p = markProgress(m, t);
			if (p <= 0) return null;
			if (m.until !== null && m.until !== undefined && t >= m.until) return null;
			let op = 1;
			if (m.fadeAfter !== null && m.fadeAfter !== undefined) op = 1 - clamp((t - m.at - m.dur - m.fadeAfter) / 0.3, 0, 1);
			if (op <= 0) return null;
			p = Math.min(1, p);
			const {drawn, P} = penState(m, p);
			if (m.kind !== 'write') {
				return (
					<g key={k} opacity={op}>
						{strokePaths(P, drawn, m.pen, white ? '#fff' : m.color, `s${k}`)}
					</g>
				);
			}
			const mid = `${id}-m${k}`;
			const tr = `translate(${m.x} ${m.y}) rotate(${-m.angle}) translate(${-m.bw / 2} ${-m.bh / 2})`;
			return (
				<g key={k} transform={tr} opacity={op}>
					{p < 1 ? (
						<mask id={mid} maskUnits="userSpaceOnUse" x={-m.bw} y={-m.bh} width={3 * m.bw} height={3 * m.bh}>
							{strokePaths(P, drawn, m.pen, '#fff', `k${k}`)}
						</mask>
					) : null}
					<g mask={p < 1 ? `url(#${mid})` : undefined}>
						<path d={m.path} transform={`translate(${m.ox} ${m.oy})`} fill={white ? '#fff' : m.color} />
					</g>
				</g>
			);
		})}
	</svg>
);

// the writing hand (factory.draw.mark_pen + hand_path): right hand, tip exactly on the stroke being laid
const handTip = (sh: any, t: number, toScreen: (b: Pt) => Pt, FW: number, FH: number) => {
	const order = sh.marks.map((_: any, i: number) => i).sort((a: number, b: number) => sh.marks[a].at - sh.marks[b].at);
	const groups: any[][] = [];
	for (const i of order) {
		const m = sh.marks[i];
		if (!m.hand) continue;
		if (m.chain && groups.length) groups[groups.length - 1].push(m);
		else groups.push([m]);
	}
	const markTip = (m: any, q: number): Pt => {
		const {tip} = penState(m, q);
		return m.kind === 'write' ? boxToBase(m, tip[0], tip[1]) : tip;
	};
	for (const g of groups) {
		g.sort((a, b) => a.at - b.at);
		const a0 = g[0].at,
			a1 = g[g.length - 1].at + g[g.length - 1].dur;
		if (!(a0 - 0.3 <= t && t <= a1 + 0.35)) continue;
		const tipAt = (tt: number): Pt => {
			for (let k = 0; k < g.length; k++) {
				const m = g[k];
				if (tt <= m.at + m.dur || k === g.length - 1) {
					if (tt >= m.at || k === 0) return toScreen(markTip(m, clamp((tt - m.at) / Math.max(m.dur, 1e-3), 0, 1)));
					const pm = g[k - 1];
					let u = clamp((tt - pm.at - pm.dur) / Math.max(0.05, m.at - pm.at - pm.dur), 0, 1);
					u = u * u * (3 - 2 * u);
					const A = markTip(pm, 1),
						B = markTip(m, 0);
					return toScreen([A[0] + (B[0] - A[0]) * u, A[1] + (B[1] - A[1]) * u - Math.sin(u * Math.PI) * sh.BH * 0.03]);
				}
			}
			return toScreen(markTip(g[g.length - 1], 1));
		};
		// ink colour = pen colour: the hand of the mark being written (r90 kept the first mark's pen for a whole chain,
		// so a red ring after a black rule was drawn with the graphite pencil)
		const cur = [...g].reverse().find((m) => m.at - 0.05 <= t) || g[0];
		let kind = cur.penKind || 'red';
		if (cur.kind === 'circle') kind = kind + '@ring'; // R37: rings - the hand turned further, off the ring it has drawn
		const enter = 0.28,
			leave = 0.32;
		const off: Pt = [FW * 1.35, FH * 1.05];
		if (t < a0 - enter || t > a1 + leave) return null;
		let pos: Pt;
		if (t < a0) {
			const a = ease((t - (a0 - enter)) / enter);
			const p1 = tipAt(a0);
			pos = [off[0] + (p1[0] - off[0]) * a, off[1] + (p1[1] - off[1]) * a];
		} else if (t > a1) {
			const a = ease((t - a1) / leave);
			const p1 = tipAt(a1);
			pos = [p1[0] + (off[0] - p1[0]) * a, p1[1] + (off[1] - p1[1]) * a];
		} else {
			const p = tipAt(t);
			pos = [p[0] + Math.sin(t * 31) * FH * 0.002, p[1] + Math.cos(t * 23) * FH * 0.002];
		}
		return {pos, kind};
	}
	return null;
};

// ------------------------------------------------------------------ shots
const ImageShotView: React.FC<{sh: any; local: number; FW: number; FH: number; debug: string; id: string}> = ({sh, local, FW, FH, debug, id}) => {
	const {s, tx, ty} = camera(sh, local);
	const toScreen = (b: Pt): Pt => [s * b[0] + tx, s * b[1] + ty + sh.y0];
	const hand = debug === 'nohand' || debug === 'ink' ? null : handTip(sh, local, toScreen, FW, FH);
	const hs = hand ? sh.hands[hand.kind] || Object.values(sh.hands)[0] : null;
	const ink = debug === 'ink';
	return (
		<AbsoluteFill style={{background: ink ? '#000' : undefined}}>
			{sh.full && sh.bg && !ink ? <Img src={staticFile(sh.bg)} style={{position: 'absolute', left: 0, top: 0, width: FW, height: FH}} /> : null}
			<div style={{position: 'absolute', left: 0, top: sh.y0, width: sh.W, height: sh.H, overflow: 'hidden'}}>
				<div
					style={{
						position: 'absolute', left: 0, top: 0, width: sh.BW, height: sh.BH, transformOrigin: '0 0',
						transform: `matrix(${s},0,0,${s},${tx},${ty})`,
					}}
				>
					{ink ? null : <Img src={staticFile(sh.img)} style={{position: 'absolute', left: 0, top: 0, width: sh.BW, height: sh.BH}} />}
					<MarksLayer sh={sh} t={local} id={id} white={ink} />
				</div>
			</div>
			{hand && hs ? (
				<Img
					src={staticFile((hs as any).src)}
					style={{position: 'absolute', left: hand.pos[0] - (hs as any).tx, top: hand.pos[1] - (hs as any).ty, width: (hs as any).w, height: (hs as any).h}}
				/>
			) : null}
		</AbsoluteFill>
	);
};

const StatView: React.FC<{sh: any; local: number; W: number; H: number}> = ({sh, local, W, H}) => {
	const q = clamp(local / sh.pop, 0, 1);
	const sc = 1.1 - 0.1 * (1 - (1 - q) * (1 - q)); // the stamp: 110 % -> 100 %
	const n = sh.numEl;
	const yNum = Math.floor(H * 0.42) - Math.floor(sh.numH / 2);
	return (
		<AbsoluteFill>
			<Img src={staticFile(sh.bg)} style={{position: 'absolute', left: 0, top: 0, width: W, height: H}} />
			{sh.label ? (
				<div style={{position: 'absolute', left: Math.floor((W - sh.label.w) / 2), top: yNum + sh.numH + Math.floor(H * 0.02)}}>
					<TextEl d={sh.label} />
				</div>
			) : null}
			<div style={{position: 'absolute', left: (W - n.w) / 2, top: H * 0.42 - n.h / 2, transform: `scale(${sc})`, transformOrigin: '50% 50%'}}>
				<TextEl d={n} />
			</div>
		</AbsoluteFill>
	);
};

const ChartView: React.FC<{sh: any; local: number; W: number; H: number}> = ({sh, local, W, H}) => {
	const [x0, y0, x1, y1] = sh.area;
	const vals = sh.values.map(Number);
	const vmax = Math.max(...vals) * 1.15 || 1;
	const n = vals.length;
	const p = ease(local / sh.grow);
	const slot = (x1 - x0) / n;
	const bw = slot * 0.62;
	return (
		<AbsoluteFill>
			<Img src={staticFile(sh.bg)} style={{position: 'absolute', left: 0, top: 0, width: W, height: H}} />
			<div style={{position: 'absolute', left: sh.title.x, top: sh.title.y}}>
				<TextEl d={sh.title} />
			</div>
			<svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0}}>
				<line x1={x0} y1={y1} x2={x1} y2={y1} stroke={sh.pal.ink} strokeWidth={sh.axisW} />
				{vals.map((v: number, i: number) => {
					const bx = x0 + slot * i + (slot - bw) / 2;
					const top = y1 - (y1 - y0) * (v / vmax) * p;
					const color = sh.highlight !== null && i === sh.highlight ? sh.pal.red : sh.pal.green;
					const vlOp = clamp((p - 0.97) / 0.03, 0, 1);
					return (
						<g key={i}>
							{p > 0 ? <rect x={bx + 1.5} y={top + 1.5} width={bw - 3} height={Math.max(0, y1 - top - 3)} fill={color} stroke={sh.pal.ink} strokeWidth={3} /> : null}
							<text x={bx + bw / 2} y={y1 + 12 + sh.labAsc} textAnchor="middle" fontFamily={fontFam(sh.labFont)} fontSize={sh.labSize} fill={sh.pal.ink}>
								{sh.labels[i]}
							</text>
							{vlOp > 0 ? (
								<text x={bx + bw / 2} y={top - 8 - sh.valDesc} textAnchor="middle" fontFamily={fontFam(sh.valFont)} fontSize={sh.valSize} fill={sh.pal.ink} opacity={vlOp}>
									{sh.fmt[i]}
								</text>
							) : null}
						</g>
					);
				})}
			</svg>
		</AbsoluteFill>
	);
};

const KineticView: React.FC<{sh: any; local: number; W: number; H: number; debug: string}> = ({sh, local, W, H, debug}) => {
	const z = 1 + 0.045 * Math.min(1, Math.max(0, local) / Math.max(4, sh.duration));
	return (
		<AbsoluteFill style={{background: debug === 'text' ? '#000' : undefined}}>
			{debug === 'text' ? null : (
				<Img src={staticFile(sh.bg)} style={{position: 'absolute', left: 0, top: 0, width: W, height: H, transform: `scale(${z})`, transformOrigin: '50% 50%'}} />
			)}
			{sh.items.map((it: any, i: number) => {
				const age = local - it.appear;
				if (age < 0) return null;
				return (
					<div key={i} style={{position: 'absolute', left: it.x, top: it.y, opacity: Math.min(1, age / 0.1)}}>
						<TextEl d={debug === 'text' ? {...it, fill: '#fff'} : it} />
					</div>
				);
			})}
		</AbsoluteFill>
	);
};

// ------------------------------------------------------------------ Larry's Tab
const LedgerView: React.FC<{lg: any; f: number; t: number; W: number; H: number; noHand?: boolean}> = ({lg, f, t, W, H, noHand}) => {
	const st = lg.states[f];
	if (!st) return null;
	const [x, y, k, a, g, cur] = st;
	const rh = lg.rowH;
	const card = (
		<div style={{position: 'absolute', left: 0, top: 0, width: lg.cw, height: lg.ch}}>
			<Img src={staticFile(lg.paper)} style={{position: 'absolute', left: 0, top: 0, width: lg.cw, height: lg.ch}} />
			<svg width={lg.cw} height={lg.ch} style={{position: 'absolute', left: 0, top: 0}}>
				<text x={lg.titleX} y={lg.titleBase} fontFamily={fontFam(lg.typew)} fontSize={lg.titleSize} fill={lg.pal.ink}>
					{lg.title}
				</text>
				<line x1={0} y1={lg.headH - 3} x2={lg.cw} y2={lg.headH - 3} stroke={lg.pal.red} strokeWidth={3} />
				{Array.from({length: lg.rows.length + 1}).map((_, j) => (
					<line key={j} x1={lg.cw * 0.04} x2={lg.cw * 0.96} y1={lg.headH + j * rh + rh - 4} y2={lg.headH + j * rh + rh - 4} stroke="rgba(150,170,190,0.63)" strokeWidth={1} />
				))}
				<line x1={lg.cw * 0.6} x2={lg.cw * 0.6} y1={lg.headH} y2={lg.ch - 6} stroke="rgba(200,120,110,0.59)" strokeWidth={1} />
				{lg.rows.map((r: any, j: number) => {
					if (t < r.at) return null;
					const p = (t - r.at - 0.15) / r.dur;
					const bold = g < 0.5 && p >= 1;
					const mid = `lg-${j}`;
					const {drawn, P} = penState(r, clamp(p, 0, 1));
					return (
						<g key={j}>
							<text x={r.labX} y={r.labY} fontFamily={fontFam(lg.typew)} fontSize={r.labSize} fill={lg.pal.ink}>
								{r.label}
							</text>
							{p > 0 && bold ? (
								<text x={r.boldX} y={r.boldBase} fontFamily={fontFam(lg.body)} fontSize={r.boldSize} fill={r.color}>
									{r.amount}
								</text>
							) : null}
							{p > 0 && !bold ? (
								<g transform={`translate(${r.ax} ${r.ay})`}>
									{p < 1 ? (
										<mask id={mid} maskUnits="userSpaceOnUse" x={-r.bw} y={-r.bh} width={3 * r.bw} height={3 * r.bh}>
											{strokePaths(P, drawn, r.pen, '#fff', `l${j}`)}
										</mask>
									) : null}
									<g mask={p < 1 ? `url(#${mid})` : undefined}>
										<path d={r.path} transform={`translate(${r.ox} ${r.oy})`} fill={r.color} />
									</g>
								</g>
							) : null}
						</g>
					);
				})}
			</svg>
		</div>
	);
	// the hand (from the right, level with the line): only while the card is full size and a row is being written
	let hand: Pt | null = null;
	if (cur !== null && g > 0.95 && !noHand) {
		let a0i = cur,
			a1i = cur;
		while (a0i > 0 && lg.rows[a0i].chain) a0i--;
		while (a1i + 1 < lg.rows.length && lg.rows[a1i + 1].chain) a1i++;
		const grp = lg.rows.slice(a0i, a1i + 1);
		const rowTip = (r: any, q: number): Pt => {
			const {tip} = penState(r, q);
			return [x + (r.ax + tip[0]) * k, y + (r.ay + tip[1]) * k];
		};
		const tipf = (q: number): Pt => {
			for (let j = 0; j < grp.length; j++) {
				const r = grp[j];
				const t0 = r.at + 0.15;
				if (q <= t0 + r.dur || j === grp.length - 1) {
					if (q >= t0 || j === 0) return rowTip(r, clamp((q - t0) / r.dur, 0, 1));
					const pr = grp[j - 1];
					const u = clamp((q - pr.at - 0.15 - pr.dur) / Math.max(0.05, t0 - pr.at - 0.15 - pr.dur), 0, 1);
					const A = rowTip(pr, 1),
						B = rowTip(r, 0);
					return [A[0] + (B[0] - A[0]) * u, A[1] + (B[1] - A[1]) * u];
				}
			}
			return rowTip(grp[grp.length - 1], 1);
		};
		const ta = grp[0].at + 0.15,
			tb = grp[grp.length - 1].at + 0.15 + grp[grp.length - 1].dur;
		const enter = 0.28,
			leave = 0.32;
		if (ta - enter <= t && t <= tb + leave) {
			const q = tipf(clamp(t, ta, tb));
			const off = W * 1.12;
			if (t < ta) hand = [off + (q[0] - off) * ease((t - (ta - enter)) / enter), q[1]];
			else if (t > tb) hand = [q[0] + (off - q[0]) * ease((t - tb) / leave), q[1]];
			else hand = q;
		}
	}
	const tw = lg.cw * 0.3;
	return (
		<>
			<div
				style={{
					position: 'absolute', left: x, top: y, width: lg.cw, height: lg.ch, transformOrigin: '0 0', transform: `scale(${k})`, opacity: a,
					boxShadow: `${5 / k}px ${7 / k}px ${12 / k}px rgba(0,0,0,0.45)`,
				}}
			>
				{card}
			</div>
			<Img
				src={staticFile(lg.tape)}
				style={{position: 'absolute', left: x + (lg.cw * k) / 2 - (tw * k) / 2, top: y - (rh * 0.55 * k) / 3, width: tw * k, opacity: a}}
			/>
			{hand ? (
				<Img src={staticFile(lg.hand.src)} style={{position: 'absolute', left: hand[0] - lg.hand.tx, top: hand[1] - lg.hand.ty, width: lg.hand.w, height: lg.hand.h}} />
			) : null}
		</>
	);
};

// ------------------------------------------------------------------ one segment of the r90 timeline
const Segment: React.FC<{seg: any; piece: any; debug: string; id: string}> = ({seg, piece, debug, id}) => {
	const f = useCurrentFrame();
	const W = piece.W,
		H = piece.H;
	const t = seg.t0 + f / piece.fps;
	let shot = seg.shots[0];
	for (const s of seg.shots) if (t >= s.start - 1e-6) shot = s;
	const local = t - shot.start;
	// punch-in on emphasised words (the picture only, not the plates)
	let z = 1;
	const pun = seg.punches.filter((p: number) => p <= t).pop();
	if (pun !== undefined && t - pun < 0.6) {
		const age = t - pun;
		z = 1 + 0.07 * (age < 0.07 ? Math.min(1, age / 0.07) : Math.max(0, 1 - (age - 0.07) / 0.5));
	}
	const ops = seg.ops[Math.min(f, seg.ops.length - 1)] || [];
	const overlays = debug === 'none' || debug === 'nohand';
	return (
		<AbsoluteFill style={{background: debug === 'ink' || debug === 'text' ? '#000' : '#F3E9D2', overflow: 'hidden'}}>
			<AbsoluteFill style={{transform: `scale(${z})`, transformOrigin: '50% 50%'}}>
				{shot.type === 'image' && debug !== 'text' ? <ImageShotView sh={shot} local={local} FW={W} FH={H} debug={debug} id={id} /> : null}
				{shot.type === 'stat' && overlays ? <StatView sh={shot} local={local} W={W} H={H} /> : null}
				{shot.type === 'chart' && overlays ? <ChartView sh={shot} local={local} W={W} H={H} /> : null}
				{shot.type === 'kinetic' && (overlays || debug === 'text') ? <KineticView sh={shot} local={local} W={W} H={H} debug={debug} /> : null}
			</AbsoluteFill>
			{overlays ? <Img src={staticFile(piece.vignette)} style={{position: 'absolute', left: 0, top: 0, width: W, height: H}} /> : null}
			{overlays && seg.ledger ? <LedgerView lg={seg.ledger} f={Math.min(f, seg.ledger.states.length - 1)} t={t} W={W} H={H} noHand={debug === 'nohand'} /> : null}
			{overlays
				? ops.map((o: any[], i: number) => (
						<div key={i} style={{position: 'absolute', left: o[1], top: o[2], opacity: o[3], transform: `scale(${o[4]})`, transformOrigin: '0 0'}}>
							<TextEl d={seg.elements[o[0]]} />
						</div>
				  ))
				: null}
		</AbsoluteFill>
	);
};

export const Piece: React.FC<{name: string; debug?: string; data?: any}> = ({data, debug = 'none'}) => {
	useFonts(data.fonts);
	let from = 0;
	return (
		<AbsoluteFill style={{background: '#000'}}>
			{data.segments.map((seg: any, i: number) => {
				const el = (
					<Sequence key={i} from={from} durationInFrames={seg.frames}>
						{debug === 'none' ? <Audio src={staticFile(seg.audio)} /> : null}
						<Segment seg={seg} piece={data} debug={debug} id={`s${i}`} />
					</Sequence>
				);
				from += seg.frames;
				return el;
			})}
		</AbsoluteFill>
	);
};
