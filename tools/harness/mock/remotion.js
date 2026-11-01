import React from 'react';
export const Ctx = React.createContext({frame: 0, fps: 30});
export const useCurrentFrame = () => React.useContext(Ctx).frame;
export const useVideoConfig = () => ({fps: React.useContext(Ctx).fps, width: 1920, height: 1080});
export const AbsoluteFill = ({style, children}) => React.createElement('div', {style: {position: 'absolute', left: 0, top: 0, right: 0, bottom: 0, ...style}}, children);
export const Img = (p) => React.createElement('img', p);
export const OffthreadVideo = ({src, style}) => React.createElement('div', {style: {...style, background: 'repeating-linear-gradient(45deg,#733,#733 20px,#955 20px,#955 40px)'}});
export const staticFile = (f) => '/pub/' + f;
export const delayRender = () => 1;
export const continueRender = () => {};
export const Sequence = ({from, durationInFrames, children}) => {
	const c = React.useContext(Ctx);
	if (c.frame < from || c.frame >= from + durationInFrames) return null;
	return React.createElement(Ctx.Provider, {value: {...c, frame: c.frame - from}}, children);
};
export const interpolate = (x, inp, out, o = {}) => {
	let t = (x - inp[0]) / (inp[1] - inp[0]);
	if (o.extrapolateLeft === 'clamp' && t < 0) t = 0;
	if (o.extrapolateRight === 'clamp' && t > 1) t = 1;
	if (o.easing) t = o.easing(t);
	return out[0] + (out[1] - out[0]) * t;
};
const cubic = (t) => t * t * t;
export const Easing = {
	inOut: (f) => (t) => (t < 0.5 ? f(t * 2) / 2 : 1 - f((1 - t) * 2) / 2),
	out: (f) => (t) => 1 - f(1 - t),
	cubic, quad: (t) => t * t,
};
export const spring = ({frame, fps, config = {}}) => {
	const d = config.damping ?? 10, k = config.stiffness ?? 100, m = 1;
	let x = 0, v = 0; const dt = 1 / fps / 4;
	for (let i = 0; i < Math.max(0, frame) * 4; i++) { const a = (-k * (x - 1) - d * v) / m; v += a * dt; x += v * dt; }
	return frame <= 0 ? 0 : x;
};
