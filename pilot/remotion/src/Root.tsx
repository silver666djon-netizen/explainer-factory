import React from 'react';
import {Composition, staticFile} from 'remotion';
import {Piece} from './Piece';
import {Reel, WIPE_FRAMES} from './Reel';
import {V2} from './V2';
import {ToolingTest, TOTAL} from './tooling/ToolingTest';
import {ScribbleWipe} from './tooling/ScribbleWipe';
import {TransitionReel, REEL_FRAMES, SAMPLE} from './tooling/TransitionReel';
import {Lottie} from '@remotion/lottie';
import {AbsoluteFill} from 'remotion';

const meta = async ({props}: any) => {
	const data = await fetch(staticFile(`${props.name}.json`)).then((r) => r.json());
	const frames = data.segments.reduce((a: number, s: any) => a + s.frames, 0);
	const wipes = data.segments.slice(0, -1).filter((s: any) => s.wipeOut).length;
	return {durationInFrames: frames - wipes * WIPE_FRAMES, width: data.W, height: data.H, fps: data.fps, props: {...props, data}};
};

const metaV2 = async ({props}: any) => {
	const data = await fetch(staticFile(`${props.name}.json`)).then((r) => r.json());
	return {durationInFrames: data.frames, width: data.W, height: data.H, fps: data.fps, props: {...props, data}};
};

// tooling v2: public/tooling/test.json (written by tools/tooling_test.py) carries the Lottie data and the timings
const metaTooling = async ({props}: any) => {
	const cfg = await fetch(staticFile('tooling/test.json')).then((r) => r.json()).catch(() => ({}));
	const lottie = cfg.lottie ? await fetch(staticFile(cfg.lottie)).then((r) => r.json()) : null;
	return {props: {...cfg, ...props, lottie}};
};

const LottieProbe: React.FC<{lottie: any}> = ({lottie}) => (
	<AbsoluteFill>{lottie ? <Lottie animationData={lottie} loop={false} style={{width: '100%', height: '100%'}} /> : null}</AbsoluteFill>
);
const metaLottie = async ({props}: any) => {
	const cfg = await fetch(staticFile('tooling/test.json')).then((r) => r.json());
	const lottie = await fetch(staticFile(cfg.lottie)).then((r) => r.json());
	const frames = Math.max(1, Math.round(((lottie.op - lottie.ip) / lottie.fr) * 30));
	return {durationInFrames: frames, props: {...props, lottie}};
};

export const RemotionRoot: React.FC = () => (
	<>
		<Composition id="Piece" component={Piece as any} width={1920} height={1080} fps={30} durationInFrames={30}
			defaultProps={{name: 'beat1_long', debug: 'none'} as any} calculateMetadata={meta} />
		<Composition id="Reel" component={Reel as any} width={1920} height={1080} fps={30} durationInFrames={30}
			defaultProps={{name: 'reel_long'} as any} calculateMetadata={meta} />
		<Composition id="V2" component={V2 as any} width={1920} height={1080} fps={30} durationInFrames={30}
			defaultProps={{name: 'v2_long'} as any} calculateMetadata={metaV2} />
		<Composition id="ToolingTest" component={ToolingTest as any} width={1920} height={1080} fps={30} durationInFrames={TOTAL}
			defaultProps={{only: 'all', fx: true, font: 'web'} as any} calculateMetadata={metaTooling} />
		<Composition id="TransitionReel" component={TransitionReel as any} width={1920} height={1080} fps={30} durationInFrames={REEL_FRAMES}
			defaultProps={{} as any} calculateMetadata={async ({props}: any) => ({durationInFrames: props.only ? SAMPLE : REEL_FRAMES})} />
		<Composition id="ScribblePort" component={ScribbleWipe as any} width={1920} height={1080} fps={30} durationInFrames={66}
			defaultProps={{color: '#a8231c'} as any} />
		<Composition id="LottieProbe" component={LottieProbe as any} width={480} height={480} fps={30} durationInFrames={30}
			defaultProps={{lottie: null} as any} calculateMetadata={metaLottie} />
	</>
);
