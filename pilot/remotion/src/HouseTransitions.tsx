// CoinSense house transitions (Klot's pick from the transition reel, Nov 7; docs/APPROVED_BLOCKS.md):
//   case folder  — act changes only; the folder carries the act title (an overlay above both shots, the cut under it)
//   torn paper   — scene changes inside an act (the outgoing sheet tears away, left to right)
//   halftone     — scene changes inside an act (the incoming shot grows in through red-ink halftone dots)
//   iris         — time jumps (the rewind) and the final "Case closed" (old cinema: close to black, open again)
// The same mechanics as the approved reel (tooling/TransitionReel.tsx), sized to any frame, with no dependency beyond
// React (the QC harness renders V2 with remotion mocked). Each component gets the direction ("entering" / "exiting") and
// the progress 0..1 of the transition, like a @remotion/transitions presentation.
import React, {useMemo} from 'react';

export type TDir = 'entering' | 'exiting';
export type TKind = 'halftone' | 'torn' | 'iris' | 'folder';
const INK = '#a8231c';
const clamp01 = (v: number) => (v < 0 ? 0 : v > 1 ? 1 : v);
const smooth = (v: number) => v * v * (3 - 2 * v);
const lcg = (seed: number) => {
	let state = seed >>> 0;
	return () => {
		state = (Math.imul(1664525, state) + 1013904223) >>> 0;
		return state / 4294967296;
	};
};

// ---------------------------------------------------------------- halftone dissolve (HyperFrames halftone-dissolve, port)
const halftoneDots = (W: number, H: number) => {
	const next = lcg(0x4a17f03d);
	const cell = Math.max(8, W / 30);
	const cols = Math.ceil(W / cell) + 2;
	const rows = Math.ceil(H / cell) + 1;
	const dots: {x: number; y: number; th: number}[] = [];
	for (let r = 0; r < rows; r++) {
		for (let c = 0; c < cols; c++) {
			const x = (c + (r % 2 === 0 ? 0.25 : 0.75)) * cell;
			const y = (r + 0.5) * cell;
			const jitter = (next() - 0.5) * 0.22;
			dots.push({x, y, th: clamp01(x / W + jitter) * 0.62});
		}
	}
	return {dots, R: cell * 0.78};
};
const power1InOut = (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
const Halftone: React.FC<{dir: TDir; p: number; W: number; H: number; children: React.ReactNode}> = ({dir, p: p0, W, H, children}) => {
	const HT = useMemo(() => halftoneDots(W, H), [W, H]);
	if (dir === 'exiting') return <>{children}</>;
	const p = power1InOut(clamp01(p0));
	if (p >= 1) return <>{children}</>;
	const parts: string[] = [];
	const ink: React.ReactNode[] = [];
	HT.dots.forEach((d, i) => {
		const ri = HT.R * smooth(clamp01((p + 0.07 - d.th) / 0.38));
		if (ri > 0.25) ink.push(<circle key={i} cx={d.x} cy={d.y} r={ri} />);
		const rw = HT.R * smooth(clamp01((p - d.th) / 0.38));
		if (rw > 0.25) {
			const x0 = (d.x + rw).toFixed(2), xr = rw.toFixed(2), yy = d.y.toFixed(2);
			parts.push(`M ${x0} ${yy} A ${xr} ${xr} 0 1 0 ${(d.x - rw).toFixed(2)} ${yy} A ${xr} ${xr} 0 1 0 ${x0} ${yy} Z`);
		}
	});
	return (
		<div style={{position: 'absolute', inset: 0}}>
			<svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0}}>
				<g fill={INK}>{ink}</g>
			</svg>
			<div style={{position: 'absolute', inset: 0, clipPath: `path("${parts.length ? parts.join(' ') : 'M 0 0 Z'}")`}}>{children}</div>
		</div>
	);
};

// ---------------------------------------------------------------- torn paper (HyperFrames torn-paper-rip, port)
const TEAR = (() => {
	const rand = lcg(0x7a9e11cf);
	const valueNoise = (knots: number) => {
		const k: number[] = [];
		for (let i = 0; i <= knots; i++) k.push(rand() * 2 - 1);
		return (v: number) => {
			const f = v * knots;
			const i = Math.min(knots - 1, Math.floor(f));
			let u = f - i;
			u = u * u * (3 - 2 * u);
			return k[i] + (k[i + 1] - k[i]) * u;
		};
	};
	const roughnessNorm = (55 - 20) / 70;
	const PX = 100 / 1920;
	const ROWS = 180;
	const WANDER_PX = 22 + roughnessNorm * 36;
	const FIBRE_PX = 2 + roughnessNorm * 2;
	const DIAGONAL_PCT = 1 + roughnessNorm * 4;
	const wander = valueNoise(6);
	const coreWidth = valueNoise(14);
	const edge: {y: number; offset: number; rim: number}[] = [];
	for (let r = 0; r <= ROWS; r++) {
		const v = r / ROWS;
		let rimPx = 6 + (14 - 6) * (coreWidth(v) * 0.5 + 0.5);
		rimPx = Math.min(14, Math.max(6, rimPx + (rand() * 2 - 1) * FIBRE_PX));
		edge.push({y: v * 100, offset: (v - 0.5) * DIAGONAL_PCT + (wander(v) * WANDER_PX + (rand() * 2 - 1) * FIBRE_PX) * PX, rim: rimPx * PX});
	}
	const maxOffset = edge.reduce((m, row) => Math.max(m, Math.abs(row.offset)), 0);
	const MARGIN = maxOffset + 14 * PX + 0.5;
	return {edge, START: -MARGIN, END: 100 + MARGIN};
})();
const tearEase = (p: number) => (p < 0.3 ? 0.2 * Math.pow(p / 0.3, 2) : 0.2 + 0.8 * (1 - Math.pow(1 - (p - 0.3) / 0.7, 3)));
const Torn: React.FC<{dir: TDir; p: number; children: React.ReactNode}> = ({dir, p, children}) => {
	if (dir === 'entering') return <>{children}</>;
	const e = tearEase(clamp01(p));
	const bx = TEAR.START + (TEAR.END - TEAR.START) * e;
	let from = '100% 0%, 100% 100%';
	let rim = from;
	for (let i = TEAR.edge.length - 1; i >= 0; i--) {
		const row = TEAR.edge[i];
		const x = bx + row.offset;
		from += `, ${x.toFixed(2)}% ${row.y.toFixed(2)}%`;
		rim += `, ${(x - row.rim).toFixed(2)}% ${row.y.toFixed(2)}%`;
	}
	return (
		<div style={{position: 'absolute', inset: 0, transformOrigin: '100% 100%', transform: `translateX(${(3 * e).toFixed(3)}%) rotate(${(1.5 * e).toFixed(3)}deg)`,
			filter: `drop-shadow(0 ${(12 * e).toFixed(1)}px ${(24 * e).toFixed(1)}px rgba(0,0,0,0.25))`}}>
			<div style={{position: 'absolute', inset: 0, clipPath: `polygon(${rim})`, background: '#f6f1e7', filter: 'blur(1.3px)'}} />
			<div style={{position: 'absolute', inset: 0, clipPath: `polygon(${from})`}}>{children}</div>
		</div>
	);
};

// ---------------------------------------------------------------- iris (old cinema: out to black, a beat, in again)
export const Iris: React.FC<{dir: TDir | 'both'; p: number; W: number; H: number; children: React.ReactNode}> = ({dir, p, W, H, children}) => {
	const R = Math.hypot(W, H) / 2;
	const closing = 1 - Math.pow(clamp01(p / 0.45), 2);
	const opening = 1 - Math.pow(1 - clamp01((p - 0.55) / 0.45), 2);
	// 'both' (a time jump inside one shot): the same picture closes and opens again
	const ex = dir === 'exiting' || (dir === 'both' && p < 0.5);
	const r = ex ? R * closing : R * opening;
	const show = ex ? p < 0.45 : p > 0.55;
	return (
		<div style={{position: 'absolute', inset: 0, background: dir !== 'entering' || p >= 0.45 ? '#000' : 'transparent'}}>
			{show ? <div style={{position: 'absolute', inset: 0, clipPath: `circle(${r.toFixed(1)}px at 50% 50%)`}}>{children}</div> : null}
		</div>
	);
};

export const Transitioned: React.FC<{kind: TKind; dir: TDir; p: number; W: number; H: number; children: React.ReactNode}> = ({kind, dir, p, W, H, children}) => {
	if (kind === 'halftone') return <Halftone dir={dir} p={p} W={W} H={H}>{children}</Halftone>;
	if (kind === 'torn') return <Torn dir={dir} p={p}>{children}</Torn>;
	if (kind === 'iris') return <Iris dir={dir} p={p} W={W} H={H}>{children}</Iris>;
	return <>{children}</>;
};

// ---------------------------------------------------------------- case folder (act changes; carries the act title)
// Klot: the label text >= 2.8 % of the frame height (cap height), the tab inside the 6 % edge margin. Both are measured by
// the release checks (data-read: text_size_contrast; data-mark: edge_margin).
const easeOutCubic = (v: number) => 1 - Math.pow(1 - v, 3);
export const CaseFolder: React.FC<{f: number; n: number; fin: number; fout: number; W: number; H: number; title: string[]; font: string; titleFont: string; caseNo?: string}> = ({f, n, fin, fout, W, H, title, font, titleFont, caseNo = 'CASE No. 4'}) => {
	if (f < 0 || f >= n) return null;
	const u = H / 1080;
	const x = f < fin ? (W + 60 * u) * (1 - easeOutCubic(f / fin)) : f >= n - fout ? -(W + 60 * u) * Math.pow((f - (n - fout)) / fout, 3) : 0;
	const [act, name] = [title[0] ?? '', title[1] ?? ''];
	const nameSize = Math.min(150 * u, (W * 0.62) / Math.max(1, name.length * 0.6));
	return (
		<div style={{position: 'absolute', left: x, top: 0, width: W + 60 * u, height: H, transform: `translateX(${-30 * u}px)`}}>
			<div style={{position: 'absolute', inset: 0, background: 'linear-gradient(180deg, #d8b673 0%, #cfa962 100%)', border: `${6 * u}px solid #8a6a32`,
				boxShadow: `${-26 * u}px 0 ${40 * u}px rgba(0,0,0,0.35), ${26 * u}px 0 ${40 * u}px rgba(0,0,0,0.35)`}} />
			{/* the tab: the act number, inside the 6 % margin (left >= 6 % of W, top >= 6 % of H) */}
			<div data-mark="folder-tab" style={{position: 'absolute', left: 0.075 * W + 30 * u, top: 0.075 * H, width: 470 * u, height: 130 * u, background: '#e3c486',
				border: `${5 * u}px solid #8a6a32`, borderRadius: 14 * u, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
				<span data-read="1" style={{fontFamily: font, fontSize: 76 * u, lineHeight: 1, color: '#2a221a', letterSpacing: 6 * u}}>{act}</span>
			</div>
			<div style={{position: 'absolute', left: 0.075 * W + 30 * u, right: 0.075 * W, top: 0.075 * H + 175 * u, height: 4 * u, background: 'rgba(90,64,26,0.35)'}} />
			{/* the typed label on the folder: the act's name */}
			<div style={{position: 'absolute', left: 30 * u + W * 0.14, width: W * 0.72, top: H * 0.4, padding: `${44 * u}px ${48 * u}px`, background: '#f4ead2',
				border: `${3 * u}px solid #8a6a32`, textAlign: 'center', transform: 'rotate(-1.5deg)', boxShadow: `0 ${10 * u}px ${24 * u}px rgba(0,0,0,0.25)`}}>
				<div data-read="1" style={{fontFamily: titleFont, fontSize: nameSize, lineHeight: 1.08, color: '#2a221a', letterSpacing: 4 * u, whiteSpace: 'nowrap'}}>{name}</div>
			</div>
			<div data-read="1" style={{position: 'absolute', right: 0.075 * W + 30 * u, top: 0.075 * H + 30 * u, fontFamily: font, fontSize: 62 * u, color: '#7a2a1c', letterSpacing: 4 * u,
				border: `${4 * u}px solid #7a2a1c`, padding: `${6 * u}px ${18 * u}px`, transform: 'rotate(3deg)'}}>{caseNo}</div>
		</div>
	);
};
