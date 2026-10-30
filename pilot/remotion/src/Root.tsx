import React from 'react';
import {Composition, staticFile} from 'remotion';
import {Piece} from './Piece';
import {Reel, WIPE_FRAMES} from './Reel';

const meta = async ({props}: any) => {
	const data = await fetch(staticFile(`${props.name}.json`)).then((r) => r.json());
	const frames = data.segments.reduce((a: number, s: any) => a + s.frames, 0);
	const wipes = data.segments.slice(0, -1).filter((s: any) => s.wipeOut).length;
	return {durationInFrames: frames - wipes * WIPE_FRAMES, width: data.W, height: data.H, fps: data.fps, props: {...props, data}};
};

export const RemotionRoot: React.FC = () => (
	<>
		<Composition id="Piece" component={Piece as any} width={1920} height={1080} fps={30} durationInFrames={30}
			defaultProps={{name: 'beat1_long', debug: 'none'} as any} calculateMetadata={meta} />
		<Composition id="Reel" component={Reel as any} width={1920} height={1080} fps={30} durationInFrames={30}
			defaultProps={{name: 'reel_long'} as any} calculateMetadata={meta} />
	</>
);
