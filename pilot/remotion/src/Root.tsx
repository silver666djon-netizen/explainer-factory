import React from 'react';
import {Composition, staticFile} from 'remotion';
import {Piece} from './Piece';

export const RemotionRoot: React.FC = () => (
	<Composition
		id="Piece"
		component={Piece as any}
		width={1920}
		height={1080}
		fps={30}
		durationInFrames={30}
		defaultProps={{name: 'beat1_long', debug: 'none'} as any}
		calculateMetadata={async ({props}: any) => {
			const data = await fetch(staticFile(`${props.name}.json`)).then((r) => r.json());
			const frames = data.segments.reduce((a: number, s: any) => a + s.frames, 0);
			return {durationInFrames: frames, width: data.W, height: data.H, fps: data.fps, props: {...props, data}};
		}}
	/>
);
