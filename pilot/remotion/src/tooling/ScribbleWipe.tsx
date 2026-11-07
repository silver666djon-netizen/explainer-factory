// Scribble wipe: a Remotion port of HyperFrames' hw-scribble-transition block (vendor/hyperframes/registry/blocks/
// hw-scribble-transition, Apache-2.0, HeyGen). The original GSAP timeline, written out as a pure function of the frame
// with the same numbers: 7 fat zigzag bands scribble on (each 0.55 s, power2.in, staggered 0.04 s), a solid backstop
// fades in at 0.80-0.92 s and out at 1.42-1.57 s (the host hard-cuts beneath at ~0.9-1.35 s), the bands scribble off
// the other way (0.5 s, power2.out, from 1.42 s, staggered 0.035 s), everything hidden from 2.17 s. Our colour: red ink.
// (A first version ran the GSAP timeline through @remotion/gsap; in renders on the Actions runner it stayed on one pose,
// so the timeline is written out here — GSAP's power2.in is t^2, power2.out is 1-(1-t)^2.)
import React, {useMemo} from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';

const W = 1920;
const H = 1080;
const hash = (n: number, seed: number) => {
	const x = Math.sin(n * 127.1 + seed * 311.7) * 43758.5453;
	return (x - Math.floor(x)) * 2 - 1;
};
const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const in2 = (t: number) => t * t;
const out2 = (t: number) => 1 - (1 - t) * (1 - t);

// clearAt / hideAt: upstream 1.42 / 2.17 s. Klot (frame review): full red cover <= 0.25 s, so ours clears from 1.10 s.
export const ScribbleWipe: React.FC<{color?: string; bands?: number; seed?: number; strokeScale?: number; clearAt?: number; hideAt?: number}> = ({
	color = '#a8231c', bands = 7, seed = 17, strokeScale = 1, clearAt = 1.1, hideAt = 1.85,
}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const t = frame / fps;
	const bandH = H / bands;
	const paths = useMemo(() => {
		const out: {d: string; w: number; len: number}[] = [];
		for (let b = 0; b < bands; b++) {
			const y0 = b * bandH + bandH / 2;
			const pts: [number, number][] = [[-80, y0 + hash(b * 17, seed) * 20]];
			const zigs = 7;
			for (let i = 1; i <= zigs; i++) {
				pts.push([(W + 160) * (i / zigs) - 80, y0 + (i % 2 ? -1 : 1) * bandH * 0.32 + hash(b * 17 + i, seed) * 16]);
			}
			let len = 0;
			for (let i = 1; i < pts.length; i++) len += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
			const d = pts.map((p, i) => `${i ? 'L' : 'M'} ${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' ');
			out.push({d, w: Math.ceil(bandH * 0.85 * strokeScale), len});
		}
		return out;
	}, [bands, bandH, seed, strokeScale]);
	if (t >= hideAt) return null;
	const solid = t < 0.8 ? 0 : t < 0.92 ? (t - 0.8) / 0.12 : t < clearAt ? 1 : t < clearAt + 0.15 ? 1 - (t - clearAt) / 0.15 : 0;
	return (
		<AbsoluteFill style={{overflow: 'hidden'}}>
			<svg viewBox={`0 0 ${W} ${H}`} style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}>
				{paths.map((p, i) => {
					const sign = i % 2 ? -1 : 1;
					const on = in2(clamp01((t - 0.04 * i) / 0.55)); // 0 -> 1 draws the band on
					const off = out2(clamp01((t - (clearAt + 0.035 * i)) / 0.5)); // 0 -> 1 draws it off the other way
					const offset = t < clearAt + 0.035 * i ? sign * p.len * (1 - on) : -sign * p.len * off;
					return (
						<path key={i} d={p.d} strokeWidth={p.w} fill="none" stroke={color} strokeLinecap="round" strokeLinejoin="round"
							strokeDasharray={p.len} strokeDashoffset={offset} />
					);
				})}
			</svg>
			<div style={{position: 'absolute', inset: 0, background: color, opacity: solid}} />
		</AbsoluteFill>
	);
};
