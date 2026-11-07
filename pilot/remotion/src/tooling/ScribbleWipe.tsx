// Scribble wipe: a Remotion port of HyperFrames' hw-scribble-transition block (vendor/hyperframes/registry/blocks/
// hw-scribble-transition, Apache-2.0, HeyGen), through @remotion/gsap: the original GSAP timeline, unchanged in its
// numbers (7 fat zigzag bands scribble on 0-0.85 s, a solid backstop 0.8-1.57 s so the host can hard-cut beneath at
// ~0.9-1.35 s, the bands scribble off 1.42-1.95 s, hidden at 2.17 s). Our colour: red ink. Transparent elsewhere.
import React, {useMemo} from 'react';
import {AbsoluteFill} from 'remotion';
import {useGsapTimeline} from '@remotion/gsap';

const W = 1920;
const H = 1080;
const hash = (n: number, seed: number) => {
	const x = Math.sin(n * 127.1 + seed * 311.7) * 43758.5453;
	return (x - Math.floor(x)) * 2 - 1;
};

export const ScribbleWipe: React.FC<{color?: string; bands?: number; seed?: number; strokeScale?: number}> = ({
	color = '#a8231c', bands = 7, seed = 17, strokeScale = 1,
}) => {
	const bandH = H / bands;
	const paths = useMemo(() => {
		const out: {d: string; w: number}[] = [];
		for (let b = 0; b < bands; b++) {
			const y0 = b * bandH + bandH / 2;
			let d = `M -80 ${(y0 + hash(b * 17, seed) * 20).toFixed(1)}`;
			const zigs = 7;
			for (let i = 1; i <= zigs; i++) {
				const x = (W + 160) * (i / zigs) - 80;
				const y = y0 + (i % 2 ? -1 : 1) * bandH * 0.32 + hash(b * 17 + i, seed) * 16;
				d += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
			}
			out.push({d, w: Math.ceil(bandH * 0.85 * strokeScale)});
		}
		return out;
	}, [bands, bandH, seed, strokeScale]);

	const scope = useGsapTimeline<HTMLDivElement>(({timeline, selector, scope: root}) => {
		const ps = selector('path') as unknown as SVGPathElement[];
		ps.forEach((p, i) => {
			const len = p.getTotalLength();
			timeline.set(p, {strokeDasharray: len, strokeDashoffset: i % 2 ? -len : len}, 0);
			timeline.to(p, {strokeDashoffset: 0, duration: 0.55, ease: 'power2.in'}, 0.04 * i);
		});
		const solid = selector('[data-solid]');
		timeline.to(solid, {opacity: 1, duration: 0.12, ease: 'none'}, 0.8);
		timeline.to(solid, {opacity: 0, duration: 0.15, ease: 'none'}, 1.42);
		ps.forEach((p, i) => {
			const len = p.getTotalLength();
			timeline.to(p, {strokeDashoffset: i % 2 ? len : -len, duration: 0.5, ease: 'power2.out'}, 1.42 + 0.035 * i);
		});
		timeline.set(root, {visibility: 'hidden'}, 2.17);
	});

	return (
		<AbsoluteFill ref={scope} style={{overflow: 'hidden'}}>
			<svg viewBox={`0 0 ${W} ${H}`} style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}>
				{paths.map((p, i) => (
					<path key={i} d={p.d} strokeWidth={p.w} fill="none" stroke={color} strokeLinecap="round" strokeLinejoin="round" />
				))}
			</svg>
			<div data-solid style={{position: 'absolute', inset: 0, background: color, opacity: 0}} />
		</AbsoluteFill>
	);
};
