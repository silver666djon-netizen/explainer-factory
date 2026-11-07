// Transition sample reel (Klot, after tooling test 2): the same two scenes as the test (A: the archive photo card,
// B: the split-flap board) joined 8 ways, ~2.2 s each, a big number 1-8 in the corner, the theme underneath.
// Only blocks we already have:
//   1 halftone-dissolve       HyperFrames component, ported (same seeded dot grid, thresholds and radii; our red ink)
//   2 torn-paper-rip          HyperFrames component, ported (same 180-row seeded edge, rim, tear ease, lift)
//   3 page-turn               @remotion/transitions bookFlip (A turns like a case-file page)
//   4 paper-collage-reveal    HyperFrames component, ported (same seeded torn panels and exits; the panels carry A)
//   5 ink-bleed-reveal        HyperFrames component, ported as cover-and-reveal (same gooey blur + alpha threshold
//                             recipe; the ink floods over A, the cut happens under it, the ink dies back off B)
//   6 iris                    old-cinema iris out to black and in again (the @remotion/transitions iris, closed to black)
//   7 film burn               @remotion/transitions filmBurn
//   8 case folder             a manila case folder slides in over the shot and off again (drawn in code)
// Each sample: A holds 0.4 s, the transition takes 1.2 s, B holds 0.6 s. No transition here is approved for episodes
// until Klot picks (R50).
import React, {useMemo} from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import type {TransitionPresentation, TransitionPresentationComponentProps} from '@remotion/transitions';
import {bookFlip} from '@remotion/transitions/book-flip';
import {filmBurn} from '@remotion/transitions/film-burn';
import {SceneA, SceneB, fonts} from './ToolingTest';

const W = 1920;
const H = 1080;
export const HOLD_A = 12;
export const TRANS = 36;
export const HOLD_B = 18;
export const SAMPLE = HOLD_A + TRANS + HOLD_B; // 66 frames = 2.2 s
export const KINDS = ['halftone', 'torn', 'page', 'collage', 'ink', 'iris', 'burn', 'folder'] as const;
export const LABELS = ['HALFTONE DISSOLVE', 'TORN PAPER', 'PAGE TURN', 'PAPER COLLAGE', 'INK BLEED', 'IRIS', 'FILM BURN', 'CASE FOLDER'];
export const REEL_FRAMES = SAMPLE * KINDS.length; // 528 = 17.6 s
const INK = '#a8231c';
const CREAM = '#f3e8cf';

const clamp01 = (v: number) => (v < 0 ? 0 : v > 1 ? 1 : v);
const smooth = (v: number) => v * v * (3 - 2 * v);
const lcg = (seed: number) => {
	let state = seed >>> 0;
	return () => {
		state = (Math.imul(1664525, state) + 1013904223) >>> 0;
		return state / 4294967296;
	};
};
type PP = TransitionPresentationComponentProps<Record<string, unknown>>;
const make = (component: React.FC<PP>): TransitionPresentation<Record<string, unknown>> => ({component, props: {}});

// ---------------------------------------------------------------- 1 halftone dissolve
const HT = (() => {
	const next = lcg(0x4a17f03d);
	const cell = Math.max(8, W / 30); // dot_size medium
	const cols = Math.ceil(W / cell) + 2;
	const rows = Math.ceil(H / cell) + 1;
	const dots: {x: number; y: number; th: number}[] = [];
	for (let r = 0; r < rows; r++) {
		for (let c = 0; c < cols; c++) {
			const x = (c + (r % 2 === 0 ? 0.25 : 0.75)) * cell;
			const y = (r + 0.5) * cell;
			const jitter = (next() - 0.5) * 0.22; // direction ltr
			dots.push({x, y, th: clamp01(x / W + jitter) * 0.62});
		}
	}
	return {dots, R: cell * 0.78};
})();
const power1InOut = (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
const Halftone: React.FC<PP> = ({children, presentationDirection, presentationProgress}) => {
	if (presentationDirection === 'exiting') return <AbsoluteFill>{children}</AbsoluteFill>;
	const p = power1InOut(presentationProgress);
	if (p >= 1) return <AbsoluteFill>{children}</AbsoluteFill>;
	const parts: string[] = [];
	const ink: React.ReactNode[] = [];
	HT.dots.forEach((d, i) => {
		const ri = HT.R * smooth(clamp01((p + 0.07 - d.th) / 0.38));
		if (ri > 0.25) ink.push(<circle key={i} cx={d.x} cy={d.y} r={ri} />);
		const rw = HT.R * smooth(clamp01((p - d.th) / 0.38));
		if (rw > 0.25) {
			const x0 = (d.x + rw).toFixed(2);
			const xr = rw.toFixed(2);
			const yy = d.y.toFixed(2);
			parts.push(`M ${x0} ${yy} A ${xr} ${xr} 0 1 0 ${(d.x - rw).toFixed(2)} ${yy} A ${xr} ${xr} 0 1 0 ${x0} ${yy} Z`);
		}
	});
	return (
		<AbsoluteFill style={{zIndex: 2}}>
			<svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
				<g fill={INK}>{ink}</g>
			</svg>
			<AbsoluteFill style={{clipPath: `path("${parts.length ? parts.join(' ') : 'M 0 0 Z'}")`}}>{children}</AbsoluteFill>
		</AbsoluteFill>
	);
};

// ---------------------------------------------------------------- 2 torn paper rip
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
const Torn: React.FC<PP> = ({children, presentationDirection, presentationProgress}) => {
	if (presentationDirection === 'entering') return <AbsoluteFill>{children}</AbsoluteFill>;
	const e = tearEase(clamp01(presentationProgress));
	const bx = TEAR.START + (TEAR.END - TEAR.START) * e; // left-to-right: the sheet that stays is on the right
	let from = '100% 0%, 100% 100%';
	let rim = from;
	for (let i = TEAR.edge.length - 1; i >= 0; i--) {
		const row = TEAR.edge[i];
		const x = bx + row.offset;
		from += `, ${x.toFixed(2)}% ${row.y.toFixed(2)}%`;
		rim += `, ${(x - row.rim).toFixed(2)}% ${row.y.toFixed(2)}%`;
	}
	return (
		<AbsoluteFill style={{zIndex: 2, transformOrigin: '100% 100%', transform: `translateX(${(3 * e).toFixed(3)}%) rotate(${(1.5 * e).toFixed(3)}deg)`,
			filter: `drop-shadow(0 ${(12 * e).toFixed(1)}px ${(24 * e).toFixed(1)}px rgba(0,0,0,0.25))`}}>
			<AbsoluteFill style={{clipPath: `polygon(${rim})`, background: '#f6f1e7', filter: 'blur(1.3px)'}} />
			<AbsoluteFill style={{clipPath: `polygon(${from})`}}>{children}</AbsoluteFill>
		</AbsoluteFill>
	);
};

// ---------------------------------------------------------------- 4 paper collage
const COLLAGE = (() => {
	const next = lcg(0x2c6b8f19);
	const range = (lo: number, hi: number) => lo + next() * (hi - lo);
	const COUNT = 6;
	const cols = 3;
	const rows = 2;
	const OVERSCAN = 3.2;
	range(75, 105); // scatterBaseAngle (drawn by the original even in "outward" mode: keeps the seed sequence)
	const SIDES = [[0, 0, 100, 0, 0, 1], [100, 0, 100, 100, -1, 0], [100, 100, 0, 100, 0, -1], [0, 100, 0, 0, 1, 0]];
	const torn = (w: number, h: number) => {
		const pts: string[] = [];
		SIDES.forEach((s) => {
			for (let k = 0; k < 6; k++) {
				const t = (k === 0 ? 0 : k + range(-0.3, 0.3)) / 6;
				const d = range(-1.1, 1.1);
				pts.push(`${(s[0] + (s[2] - s[0]) * t + (s[4] * d * 100) / w).toFixed(2)}% ${(s[1] + (s[3] - s[1]) * t + (s[5] * d * 100) / h).toFixed(2)}%`);
			}
		});
		return pts.join(', ');
	};
	const panels = [];
	for (let i = 0; i < COUNT; i++) {
		const row = Math.floor(i / cols);
		const col = i % cols;
		const cellW = 100 / cols;
		const cellH = 100 / rows;
		const x = col * cellW - OVERSCAN + range(-1, 1);
		const y = row * cellH - OVERSCAN + range(-1, 1);
		const w = cellW + OVERSCAN * 2;
		const h = cellH + OVERSCAN * 2;
		const poly = torn(w, h);
		next(); // tone pick (mixed) in the original
		const ang = Math.atan2(y + h / 2 - 50, x + w / 2 - 50); // spread outward
		const ux = Math.cos(ang);
		const uy = Math.sin(ang);
		const arcAmp = ux > 0 ? -9 : 9;
		const rotation = range(8, 15) * (next() < 0.5 ? -1 : 1);
		const lag = i === 0 ? 0 : range(0, 0.4); // the original's start jitter: start = first + (i - lag) * gap
		panels.push({x, y, w, h, poly, exitX: ux * 130, exitY: uy * 130, arcX: -uy * arcAmp, arcY: ux * arcAmp, rotation, i, lag});
	}
	return panels;
})();
const Collage: React.FC<PP> = ({children, presentationDirection, presentationProgress}) => {
	if (presentationDirection === 'entering') return <AbsoluteFill>{children}</AbsoluteFill>;
	const dur = TRANS / 30;
	const squeeze = Math.min(1, dur / 1.35);
	const first = 0.1 * squeeze;
	const travel = 0.45 * squeeze;
	const last = 1.35 * squeeze - travel;
	const gap = (last - first) / 5;
	const t = presentationProgress * dur;
	return (
		<AbsoluteFill style={{zIndex: 2}}>
			{COLLAGE.map((p) => {
				const start = p.i === 0 ? first : first + (p.i - p.lag) * gap;
				const q = clamp01((t - start) / travel);
				const e = q * q; // power2.in
				const a = 1 - (1 - q) * (1 - q); // power1.out on the arc layer
				const tx = (p.exitX * e * W) / 100 + (p.arcX * a * H) / 100;
				const ty = (p.exitY * e * H) / 100 + (p.arcY * a * H) / 100;
				return (
					<div key={p.i} style={{position: 'absolute', left: `${p.x}%`, top: `${p.y}%`, width: `${p.w}%`, height: `${p.h}%`, zIndex: 6 - p.i,
						transform: `translate(${tx.toFixed(1)}px, ${ty.toFixed(1)}px) rotate(${(p.rotation * e).toFixed(2)}deg)`,
						filter: `drop-shadow(0 ${(4 + 18 * q).toFixed(1)}px ${(6 + 22 * q).toFixed(1)}px rgba(0,0,0,${(0.18 + 0.2 * q).toFixed(2)}))`}}>
						<div style={{position: 'absolute', inset: 0, clipPath: `polygon(${p.poly})`, background: '#fbf6ea'}}>
							<div style={{position: 'absolute', left: `${(-p.x / p.w) * 100}%`, top: `${(-p.y / p.h) * 100}%`, width: W, height: H}}>{children}</div>
						</div>
					</div>
				);
			})}
		</AbsoluteFill>
	);
};

// ---------------------------------------------------------------- 5 ink bleed (cover, cut under the ink, die back)
const BLOBS = (() => {
	const next = lcg(0x1b1eedca);
	const minDim = H;
	const n = 6;
	const rows = [];
	for (let i = 0; i < n; i++) {
		const angle = (i / n) * Math.PI * 2 + next() * 0.9;
		rows.push({dirX: Math.cos(angle), dirY: Math.sin(angle), spread: (0.16 + 0.16 * next()) * minDim * 2.4,
			// the drop in the middle floods the whole frame at its peak (radius > half the diagonal); the others give the edge its bleed
			size: (i === 0 ? 2.3 : 0.5 + 0.45 * next()) * minDim, birth: i === 0 ? 0 : 0.04 + 0.3 * next(),
			wobbleAmp: (0.02 + 0.03 * next()) * minDim, wobblePhase: next() * Math.PI * 2, wobbleFreq: 2 + Math.floor(next() * 3)});
	}
	return rows;
})();
const easeOutCubic = (v: number) => 1 - Math.pow(1 - v, 3);
const InkLayer: React.FC<{grow: number; die: number; t: number}> = ({grow, die, t}) => (
	<svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
		<defs>
			<filter id="cs-goo" x="-20%" y="-20%" width="140%" height="140%" colorInterpolationFilters="sRGB">
				<feGaussianBlur stdDeviation={H * 0.028} />
				<feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 22 -9" />
			</filter>
		</defs>
		<g filter="url(#cs-goo)" fill="#73201a">
			{BLOBS.map((b, i) => {
				const g = easeOutCubic(clamp01((grow - b.birth) / 0.66));
				const k = g * (1 - die);
				const r = (b.size / 2) * k;
				if (r <= 0.5) return null;
				const reach = b.spread * k;
				const wob = Math.sin(t * Math.PI * 2 * b.wobbleFreq + b.wobblePhase) * b.wobbleAmp * k;
				return <circle key={i} cx={W / 2 + b.dirX * reach + wob * b.dirY} cy={H / 2 + b.dirY * reach - wob * b.dirX} r={r} />;
			})}
		</g>
	</svg>
);
const Ink: React.FC<PP> = ({children, presentationDirection, presentationProgress: p}) => {
	if (presentationDirection === 'exiting') return <AbsoluteFill style={{opacity: p < 0.5 ? 1 : 0}}>{children}</AbsoluteFill>;
	const grow = p < 0.5 ? p / 0.5 : 1;
	const die = p < 0.5 ? 0 : power1InOut(clamp01((p - 0.5) / 0.5));
	return (
		<AbsoluteFill style={{zIndex: 2}}>
			<AbsoluteFill style={{opacity: p < 0.5 ? 0 : 1}}>{children}</AbsoluteFill>
			<InkLayer grow={grow} die={die} t={p} />
		</AbsoluteFill>
	);
};

// ---------------------------------------------------------------- 6 iris (old cinema: out to black, a beat, in again)
const Iris: React.FC<PP> = ({children, presentationDirection, presentationProgress: p}) => {
	const R = Math.hypot(W, H) / 2;
	const closing = 1 - Math.pow(clamp01(p / 0.45), 2); // A: iris closes to a point
	const opening = 1 - Math.pow(1 - clamp01((p - 0.55) / 0.45), 2); // B: opens from a point
	const r = presentationDirection === 'exiting' ? R * closing : R * opening;
	const show = presentationDirection === 'exiting' ? p < 0.45 : p > 0.55;
	return (
		// black behind A while it closes; the incoming layer stays clear until A has closed (else it would hide A)
		<AbsoluteFill style={{background: presentationDirection === 'exiting' || p >= 0.45 ? '#000' : 'transparent', zIndex: presentationDirection === 'entering' ? 2 : 1}}>
			{show ? <AbsoluteFill style={{clipPath: `circle(${r.toFixed(1)}px at 50% 50%)`}}>{children}</AbsoluteFill> : null}
		</AbsoluteFill>
	);
};

// ---------------------------------------------------------------- 8 case folder
const Folder: React.FC<{x: number}> = ({x}) => {
	const {SE} = fonts();
	return (
		<div style={{position: 'absolute', left: x, top: 0, width: W + 60, height: H, transform: 'translateX(-30px)'}}>
			<div style={{position: 'absolute', inset: 0, background: 'linear-gradient(180deg, #d8b673 0%, #cfa962 100%)', border: '6px solid #8a6a32',
				boxShadow: '-26px 0 40px rgba(0,0,0,0.35), 26px 0 40px rgba(0,0,0,0.35)'}} />
			{/* the tab with the case number, on the folder's top edge */}
			<div style={{position: 'absolute', left: 140, top: 40, width: 520, height: 120, background: '#e3c486', border: '5px solid #8a6a32', borderRadius: 14,
				display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: SE, fontSize: 64, color: '#2a221a', letterSpacing: 4}}>
				CASE No. 4
			</div>
			<div style={{position: 'absolute', left: 140, right: 200, top: 250, height: 4, background: 'rgba(90,64,26,0.35)'}} />
			{/* a typed label */}
			<div style={{position: 'absolute', left: 620, top: 420, width: 800, padding: '40px 48px', background: '#f4ead2', border: '3px solid #8a6a32',
				fontFamily: SE, fontSize: 60, color: '#2a221a', textAlign: 'center', letterSpacing: 6, transform: 'rotate(-1.5deg)'}}>
				THE SEVEN-MINUTE HEIST
			</div>
		</div>
	);
};
const CaseFolder: React.FC<PP> = ({children, presentationDirection, presentationProgress: p}) => {
	if (presentationDirection === 'exiting') return <AbsoluteFill style={{opacity: p < 0.5 ? 1 : 0}}>{children}</AbsoluteFill>;
	// in from the right, off to the left; the folder is W + 60 wide (30 px past each edge), so it travels W + 60 each way
	const x = p < 0.5 ? (W + 60) * (1 - easeOutCubic(p / 0.5)) : -(W + 60) * Math.pow((p - 0.5) / 0.5, 3);
	return (
		<AbsoluteFill style={{zIndex: 2}}>
			<AbsoluteFill style={{opacity: p < 0.5 ? 0 : 1}}>{children}</AbsoluteFill>
			<Folder x={x} />
		</AbsoluteFill>
	);
};

const presentation = (k: (typeof KINDS)[number]): TransitionPresentation<any> => {
	switch (k) {
		case 'halftone': return make(Halftone);
		case 'torn': return make(Torn);
		case 'page': return bookFlip({direction: 'from-right'});
		case 'collage': return make(Collage);
		case 'ink': return make(Ink);
		case 'iris': return make(Iris);
		case 'burn': return filmBurn({seed: 2.31});
		default: return make(CaseFolder);
	}
};

const Badge: React.FC<{n: number; label: string}> = ({n, label}) => {
	const {SE} = fonts();
	return (
		<div style={{position: 'absolute', right: 56, top: 44, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 14, zIndex: 50}}>
			<div style={{width: 190, height: 190, borderRadius: '50%', background: INK, border: `8px solid ${CREAM}`, boxShadow: '0 10px 26px rgba(0,0,0,0.45)',
				display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: SE, fontSize: 150, lineHeight: 1, color: CREAM, paddingTop: 10}}>
				{n}
			</div>
			<div style={{background: 'rgba(20,16,12,0.82)', color: CREAM, fontFamily: SE, fontSize: 40, letterSpacing: 4, padding: '8px 18px'}}>{label}</div>
		</div>
	);
};

export const TransitionReel: React.FC<{only?: number}> = ({only}) => {
	const a = useMemo(() => ({only: 'all' as const, fx: true, font: 'web' as const}), []);
	const b = useMemo(() => ({only: 'all' as const, fx: true, font: 'web' as const, flap: {from: '$48', to: '$48', startAt: 0}}), []);
	return (
		<AbsoluteFill style={{background: '#000'}}>
			{KINDS.map((k, i) =>
				only !== undefined && only !== i + 1 ? null : (
					<Sequence key={k} from={only !== undefined ? 0 : i * SAMPLE} durationInFrames={SAMPLE}>
						<TransitionSeries>
							<TransitionSeries.Sequence durationInFrames={HOLD_A + TRANS}>
								<SceneA p={a} />
							</TransitionSeries.Sequence>
							<TransitionSeries.Transition presentation={presentation(k)} timing={linearTiming({durationInFrames: TRANS})} />
							<TransitionSeries.Sequence durationInFrames={TRANS + HOLD_B}>
								<SceneB p={b} />
							</TransitionSeries.Sequence>
						</TransitionSeries>
						<Badge n={i + 1} label={LABELS[i]} />
					</Sequence>
				),
			)}
		</AbsoluteFill>
	);
};
