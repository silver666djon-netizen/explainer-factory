// Tooling v2 test render (Klot, item 14): one 8-second 1080p composition that exercises every new piece once.
//   0.0-3.0  A  paper + speckle background (@remotion/effects), an LoC photo printed in halftone, a Special Elite title,
//               a red-ink rough-notation circle around the $30 tag
//   2.0-4.2     HyperFrames hw-scribble-transition, rendered by the hyperframes CLI as a transparent WebM (red ink);
//               the A -> B hard cut sits under its full-coverage window
//   3.0-6.0  B  split-flap board $30 -> $48 (our Remotion port of HyperFrames split-flap-board)
//   5.4-6.0     clockWipe (@remotion/transitions) B -> C
//   5.4-8.0  C  paper card, Special Elite line, a LottieFiles "approved" stamp (@remotion/lottie); the stamp SFX on its hit
// Audio (the ElevenLabs theme + stamp SFX) is mixed after the render (tools/tooling_test.py), as in the episode pipeline.
// `only` renders one element alone (for the per-element timing and checks); `fx: false` drops the effects and `font:
// 'fallback'` the web fonts, so the checks can compare each element against its own absence.
import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, Sequence, Solid, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import {clockWipe} from '@remotion/transitions/clock-wipe';
import {halftone} from '@remotion/effects/halftone';
import {paper} from '@remotion/effects/paper';
import {speckle} from '@remotion/effects/speckle';
import {Circle} from '@remotion/rough-notation';
import {Lottie} from '@remotion/lottie';
import {loadFont as loadSpecialElite} from '@remotion/google-fonts/SpecialElite';
import {loadFont as loadCourierPrime} from '@remotion/google-fonts/CourierPrime';
import {SplitFlap} from './SplitFlap';

// loaded on first use (not at import), so the episode compositions in the same bundle never fetch these fonts
let FONTS: {SE: string; CP: string} | null = null;
const fonts = () => {
	if (!FONTS) {
		FONTS = {SE: loadSpecialElite('normal', {weights: ['400'], subsets: ['latin']}).fontFamily,
			CP: loadCourierPrime('normal', {weights: ['700'], subsets: ['latin']}).fontFamily};
	}
	return FONTS;
};

export type ToolingProps = {
	only?: 'all' | 'effects' | 'title' | 'circle' | 'overlay' | 'flap' | 'wipe' | 'lottie';
	fx?: boolean;
	font?: 'web' | 'fallback';
	lottie?: any; // animation JSON (loaded in calculateMetadata)
	lottieAt?: number; // seconds into C
	flap?: {from: string; to: string; startAt: number};
};

export const FPS = 30;
export const A_LEN = 90; // 0-3.0 s
export const B_LEN = 90; // 3.0-6.0 s
export const WIPE = 18; // 5.4-6.0 s
export const C_LEN = 78; // 5.4-8.0 s
export const TOTAL = A_LEN + B_LEN + C_LEN - WIPE; // 240
export const SCRIBBLE_AT = 60; // 2.0 s

const INK = '#a8231c';
const CREAM = '#efe4cb';

const on = (p: ToolingProps, el: string) => !p.only || p.only === 'all' || p.only === el;

const PaperBg: React.FC<{p: ToolingProps; seed: number}> = ({p, seed}) => {
	const fx = p.fx !== false && on(p, 'effects');
	return (
		<AbsoluteFill style={{background: '#2a241e'}}>
			<Solid width={1920} height={1080} color={CREAM}
				effects={fx ? [paper({colorFront: '#b9a47c', colorBack: CREAM, amount: 0.9, roughness: 0.45, fiber: 0.35, crumples: 0.25, folds: 0.4, foldCount: 3, drops: 0.15, seed}),
					speckle({density: 0.05, size: 3.5, randomness: 1})] : []} />
		</AbsoluteFill>
	);
};

const SceneA: React.FC<{p: ToolingProps}> = ({p}) => {
	const {SE} = fonts();
	const f = useCurrentFrame();
	const fx = p.fx !== false && on(p, 'effects');
	const font = p.font === 'fallback' ? 'monospace' : SE;
	const circle = interpolate(f, [30, 54], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	return (
		<AbsoluteFill>
			{on(p, 'effects') || on(p, 'title') || on(p, 'circle') ? <PaperBg p={p} seed={11} /> : <AbsoluteFill style={{background: CREAM}} />}
			{on(p, 'effects') ? (
				<div data-el="photo" style={{position: 'absolute', left: 120, top: 210, width: 900, height: 640, background: '#f7f1e3', padding: 22,
					transform: 'rotate(-2deg)', boxShadow: '0 22px 40px rgba(0,0,0,0.35)'}}>
					<Img src={staticFile('tooling/photo.jpg')} style={{width: 856, height: 596, objectFit: 'cover', display: 'block'}}
						effects={fx ? [halftone({colorMode: 'source', shape: 'circle', dotSize: 7, dotSpacing: 7, rotation: 15})] : []} />
				</div>
			) : null}
			{on(p, 'title') ? (
				<div data-el="title" style={{position: 'absolute', left: 120, top: 70, fontFamily: font, fontSize: 92, color: '#1f1a14', letterSpacing: 2}}>
					CASE FILE No. 4
				</div>
			) : null}
			{on(p, 'title') ? (
				<div style={{position: 'absolute', left: 1110, top: 300, width: 690, fontFamily: font, fontSize: 54, lineHeight: 1.25, color: '#2b241c'}}>
					THE SEVEN-MINUTE HEIST
				</div>
			) : null}
			{on(p, 'circle') ? (
				<div data-el="tag" style={{position: 'absolute', left: 1240, top: 560, padding: '26px 54px', background: '#f6ecd4', border: '3px solid #3a3027',
					transform: 'rotate(3deg)', fontFamily: p.font === 'fallback' ? 'monospace' : SE, fontSize: 120, color: '#1f1a14'}}>
					<Circle progress={circle} color={INK} strokeWidth={9} roughness={1.6} iterations={2} padding={{left: 34, right: 34, top: 26, bottom: 26}}>
						$30
					</Circle>
				</div>
			) : null}
		</AbsoluteFill>
	);
};

const SceneB: React.FC<{p: ToolingProps}> = ({p}) => {
	const {SE, CP} = fonts();
	const fl = p.flap ?? {from: '$30', to: '$48', startAt: 0.6};
	return (
		<AbsoluteFill style={{background: 'radial-gradient(120% 90% at 50% 42%, #2c2721 0%, #15120f 62%, #0b0a08 100%)', alignItems: 'center', justifyContent: 'center'}}>
			{on(p, 'flap') ? (
				<div data-el="flap" style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 46}}>
					<SplitFlap from={fl.from} to={fl.to} startAt={fl.startAt} fontFamily={p.font === 'fallback' ? 'monospace' : CP} cellWidth={200} />
					<div style={{fontFamily: p.font === 'fallback' ? 'monospace' : SE, fontSize: 44, color: '#d9ccb0', letterSpacing: 4}}>SAME SEAT · LAST SCREEN</div>
				</div>
			) : null}
		</AbsoluteFill>
	);
};

const SceneC: React.FC<{p: ToolingProps}> = ({p}) => {
	const {SE} = fonts();
	const at = Math.round((p.lottieAt ?? 0.7) * FPS);
	return (
		<AbsoluteFill>
			{on(p, 'lottie') || on(p, 'effects') || on(p, 'title') ? <PaperBg p={p} seed={23} /> : <AbsoluteFill style={{background: CREAM}} />}
			{on(p, 'title') ? (
				<div style={{position: 'absolute', left: 160, top: 400, width: 980, fontFamily: p.font === 'fallback' ? 'monospace' : SE, fontSize: 96, lineHeight: 1.15, color: '#1f1a14'}}>
					+$18 IN FEES.
				</div>
			) : null}
			{on(p, 'lottie') && p.lottie ? (
				<Sequence from={at} layout="none">
					<div data-el="lottie" style={{position: 'absolute', left: 1230, top: 250, width: 560, height: 560}}>
						<Lottie animationData={p.lottie} loop={false} style={{width: 560, height: 560}} />
					</div>
				</Sequence>
			) : null}
		</AbsoluteFill>
	);
};

export const ToolingTest: React.FC<ToolingProps> = (p) => {
	return (
		<AbsoluteFill style={{background: '#000'}}>
			<TransitionSeries>
				<TransitionSeries.Sequence durationInFrames={A_LEN}>
					<SceneA p={p} />
				</TransitionSeries.Sequence>
				<TransitionSeries.Sequence durationInFrames={B_LEN}>
					<SceneB p={p} />
				</TransitionSeries.Sequence>
				{on(p, 'wipe') ? (
					<TransitionSeries.Transition presentation={clockWipe({width: 1920, height: 1080})} timing={linearTiming({durationInFrames: WIPE})} />
				) : (
					<TransitionSeries.Transition presentation={clockWipe({width: 1920, height: 1080})} timing={linearTiming({durationInFrames: 1})} />
				)}
				<TransitionSeries.Sequence durationInFrames={on(p, 'wipe') ? C_LEN : C_LEN - WIPE + 1}>
					<SceneC p={p} />
				</TransitionSeries.Sequence>
			</TransitionSeries>
			{on(p, 'overlay') ? (
				<Sequence from={SCRIBBLE_AT} durationInFrames={66} layout="none">
					<AbsoluteFill>
						<OffthreadVideo src={staticFile('tooling/overlay.webm')} transparent muted />
					</AbsoluteFill>
				</Sequence>
			) : null}
		</AbsoluteFill>
	);
};
