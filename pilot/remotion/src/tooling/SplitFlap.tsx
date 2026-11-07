// Split-flap board: a Remotion port of HyperFrames' split-flap-board block (vendor/hyperframes/registry/blocks/
// split-flap-board, Apache-2.0, HeyGen). Same mechanism and numbers: every cell walks its drum FORWARD through the
// intervening characters of a fixed alphabet; a flap falls with constant angular acceleration (theta = 180 * p^2, no
// ease-out), the two leaves are the two faces of one flap (hand-off at 90 deg), shade = 1 - 0.5 * sin(theta).
// Changes from the original: GSAP is not needed (the original is already a pure function of time, paint(t)), cells
// start from a `from` string instead of the blank flap ($30 -> $48), the look is ours (cream glyphs on dark flaps).
import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';

export const FLAP_ALPHABET = ' $0123456789.,+-%ABCDEFGHIJKLMNOPQRSTUVWXYZ';

export type SplitFlapProps = {
	from: string;
	to: string;
	startAt?: number; // seconds (local)
	flipDuration?: number; // seconds per flap
	cellStagger?: number;
	alphabet?: string;
	cellWidth?: number;
	fontFamily?: string;
	glyphColor?: string;
};

export const flapSteps = (from: string, to: string, alphabet = FLAP_ALPHABET) => {
	const N = alphabet.length;
	const n = Math.max(from.length, to.length);
	const pad = (s: string) => s.padStart(n, ' ');
	return [...pad(to)].map((ch, i) => {
		const a = Math.max(0, alphabet.indexOf(pad(from)[i]));
		const b = Math.max(0, alphabet.indexOf(ch));
		return {start: a, steps: (b - a + N) % N};
	});
};

/** Seconds until the last cell has landed (local to the board's start). */
export const flapLandsAt = (p: SplitFlapProps) => {
	const st = flapSteps(p.from, p.to, p.alphabet);
	return (p.startAt ?? 0) + Math.max(...st.map((c, i) => i * (p.cellStagger ?? 0.12) + c.steps * (p.flipDuration ?? 0.11)));
};

const Face: React.FC<{char: string; half: 'top' | 'bot'; w: number; h: number; font: string; color: string; style?: React.CSSProperties}> = ({
	char, half, w, h, font, color, style,
}) => (
	<div
		style={{
			position: 'absolute', left: 0, width: w, height: h / 2, top: half === 'top' ? 0 : h / 2, overflow: 'hidden',
			borderRadius: half === 'top' ? '9px 9px 0 0' : '0 0 9px 9px',
			background: half === 'top' ? 'linear-gradient(180deg, #2a2723 0%, #1c1a17 100%)' : 'linear-gradient(180deg, #1a1815 0%, #25221e 100%)',
			...style,
		}}
	>
		<span
			style={{
				position: 'absolute', left: 0, width: w, height: h, lineHeight: `${h}px`, top: half === 'top' ? 0 : -h / 2,
				textAlign: 'center', fontFamily: font, fontWeight: 700, fontSize: Math.round(w * 0.78), color, whiteSpace: 'pre',
			}}
		>
			{char}
		</span>
	</div>
);

export const SplitFlap: React.FC<SplitFlapProps> = (p) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const alphabet = p.alphabet ?? FLAP_ALPHABET;
	const N = alphabet.length;
	const flipDur = p.flipDuration ?? 0.11;
	const stagger = p.cellStagger ?? 0.12;
	const w = p.cellWidth ?? 190;
	const h = Math.round(w * 1.45);
	const font = p.fontFamily ?? 'monospace';
	const color = p.glyphColor ?? '#f1e6cc';
	const t = frame / fps - (p.startAt ?? 0);
	const cells = flapSteps(p.from, p.to, alphabet);
	return (
		<div style={{display: 'flex', gap: 14}}>
			{cells.map((c, i) => {
				const tl = t - i * stagger;
				let count = Math.floor(tl <= 0 ? 0 : tl / flipDur);
				let pr = tl <= 0 ? 0 : tl / flipDur - count;
				if (count >= c.steps) {
					count = c.steps;
					pr = 0;
				}
				const out = alphabet.charAt((c.start + count) % N);
				const inc = alphabet.charAt((c.start + count + 1) % N);
				const flipping = count < c.steps && pr > 0;
				const theta = 180 * pr * pr;
				const shade = 1 - 0.5 * Math.sin((theta * Math.PI) / 180);
				return (
					<div
						key={i}
						style={{
							position: 'relative', width: w, height: h, perspective: 900, borderRadius: 9, background: '#0e0d0b',
							boxShadow: '0 18px 34px rgba(0,0,0,0.55), 0 0 0 1px rgba(255,255,255,0.05)',
						}}
					>
						<Face char={flipping ? inc : out} half="top" w={w} h={h} font={font} color={color} />
						<Face char={out} half="bot" w={w} h={h} font={font} color={color} />
						{flipping && theta < 90 ? (
							<Face char={out} half="top" w={w} h={h} font={font} color={color}
								style={{transformOrigin: '50% 100%', transform: `rotateX(${(-theta).toFixed(2)}deg)`, filter: `brightness(${shade.toFixed(3)})`, zIndex: 3, backfaceVisibility: 'hidden'}} />
						) : null}
						{flipping && theta >= 90 ? (
							<Face char={inc} half="bot" w={w} h={h} font={font} color={color}
								style={{transformOrigin: '50% 0%', transform: `rotateX(${(180 - theta).toFixed(2)}deg)`, filter: `brightness(${shade.toFixed(3)})`, zIndex: 3, backfaceVisibility: 'hidden'}} />
						) : null}
						<div style={{position: 'absolute', left: 0, top: h / 2 - 1.5, width: w, height: 3, background: '#050505', zIndex: 4}} />
					</div>
				);
			})}
		</div>
	);
};
