// A flat 1950s rubber stamp that comes down onto a document, hits it and leaves its ink imprint (Klot's frame review:
// replaces the Lottie "Approved Stamp"; R49: the tool touches its target). Drawn in flat print style — two-tone wood,
// a red rubber face, a thick dark outline — so it sits with the paper, the typewriter text and the halftone photo.
// The imprint appears on the contact frame, under the rubber face, and stays; the stamp lifts away and leaves the frame.
// Pure function of the frame: contact at `hitAt` (seconds, local to the Sequence it is placed in).
import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';

// the imprint box (frame px, before the document's own -2.5 deg tilt) — the checks read the same numbers
export const IMPRINT = {x: 1160, y: 640, w: 440, h: 150};
export const DOC_TILT = -2.5; // the document, the imprint and the stamp share this tilt (around the document's centre)
const TILT = {transform: `rotate(${DOC_TILT}deg)`, transformOrigin: '1380px 540px'};
const INK = '#a8231c';
const OUT = '#2a1a10';

const ease = (t: number) => t * t * t; // the stamp accelerates into the paper (a hand pushing down)
const lift = (t: number) => 1 - (1 - t) * (1 - t);
const clamp01 = (x: number) => Math.max(0, Math.min(1, x));

const Imprint: React.FC<{word: string; font: string}> = ({word, font}) => (
	<svg width={IMPRINT.w + 40} height={IMPRINT.h + 40} style={{position: 'absolute', left: IMPRINT.x - 20, top: IMPRINT.y - 20, overflow: 'visible'}}>
		<defs>
			{/* worn rubber: fractal-noise holes in the ink, fixed seed (the same on every frame) */}
			<filter id="cs-ink" x="-5%" y="-5%" width="110%" height="110%">
				<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="11" result="n" />
				<feComponentTransfer in="n" result="m">
					<feFuncA type="discrete" tableValues="0 1 1 1 1 1 1 1" />
				</feComponentTransfer>
				<feComposite in="SourceGraphic" in2="m" operator="in" />
			</filter>
		</defs>
		<g filter="url(#cs-ink)" opacity={0.92} transform="translate(20 20)">
			<rect x={4} y={4} width={IMPRINT.w - 8} height={IMPRINT.h - 8} rx={10} fill="none" stroke={INK} strokeWidth={9} />
			<rect x={20} y={20} width={IMPRINT.w - 40} height={IMPRINT.h - 40} rx={5} fill="none" stroke={INK} strokeWidth={3.5} />
			<text x={IMPRINT.w / 2} y={IMPRINT.h / 2 + 30} textAnchor="middle" fontFamily={font} fontWeight={700} fontSize={86} letterSpacing={14} fill={INK}>
				{word}
			</text>
		</g>
	</svg>
);

/** The stamp itself, side-on, its rubber face `IMPRINT.w` wide. (x, y) = the bottom centre of the rubber face. */
const Stamp: React.FC<{x: number; y: number; squash: number}> = ({x, y, squash}) => {
	const w = IMPRINT.w + 20;
	const mountH = 110;
	const rubberH = 22;
	return (
		<svg width={w + 20} height={420} style={{position: 'absolute', left: x - (w + 20) / 2, top: y - 420, overflow: 'visible'}}>
			<g transform={`translate(10 0) translate(0 ${420 * (1 - squash)}) scale(1 ${squash})`} strokeLinejoin="round">
				{/* knob + neck */}
				<ellipse cx={w / 2} cy={120} rx={62} ry={56} fill="#8a5232" stroke={OUT} strokeWidth={7} />
				<ellipse cx={w / 2 - 18} cy={104} rx={22} ry={16} fill="#b7774c" />
				<path d={`M ${w / 2 - 34} 168 L ${w / 2 - 46} ${420 - mountH - rubberH - 18} L ${w / 2 + 46} ${420 - mountH - rubberH - 18} L ${w / 2 + 34} 168 Z`}
					fill="#8a5232" stroke={OUT} strokeWidth={7} />
				<rect x={w / 2 - 30} y={176} width={14} height={110} rx={6} fill="#b7774c" />
				{/* wooden mount */}
				<rect x={0} y={420 - mountH - rubberH - 22} width={w} height={mountH + 22} rx={10} fill="#a8683f" stroke={OUT} strokeWidth={7} />
				<rect x={14} y={420 - mountH - rubberH - 10} width={w - 28} height={18} rx={6} fill="#c58a5c" />
				{/* red rubber face */}
				<rect x={10} y={420 - rubberH - 4} width={w - 20} height={rubberH} rx={4} fill={INK} stroke={OUT} strokeWidth={6} />
			</g>
		</svg>
	);
};

export type RubberStampProps = {hitAt?: number; word?: string; font?: string};

export const RubberStampOnDocument: React.FC<RubberStampProps & {docFont: string}> = ({hitAt = 0.95, word = 'PAID', font = 'monospace', docFont}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const t = frame / fps;
	const down0 = hitAt - 0.38; // enters from above the frame
	const up0 = hitAt + 0.2; // pressed for 0.2 s, then lifts
	const up1 = up0 + 0.45;
	const rest = IMPRINT.y + IMPRINT.h; // the rubber face's bottom on the paper = the imprint's bottom edge
	let y: number | null = null;
	let squash = 1;
	if (t >= down0 && t < hitAt) y = -40 + (rest + 40) * ease(clamp01((t - down0) / (hitAt - down0)));
	else if (t >= hitAt && t < up0) {
		y = rest;
		squash = 1 - 0.04 * Math.sin(Math.PI * clamp01((t - hitAt) / 0.12)); // the rubber gives a little on impact
	} else if (t >= up0 && t < up1) y = rest - (rest + 480) * lift(clamp01((t - up0) / (up1 - up0)));
	const shadow = y === null ? 0 : clamp01(1 - (rest - y) / 520);
	const docShake = t >= hitAt && t < hitAt + 0.1 ? Math.sin(((t - hitAt) / 0.1) * Math.PI) * 3 : 0;
	return (
		<>
			{/* the document: a box-office statement, typewritten */}
			<div style={{position: 'absolute', left: 1040, top: 150, width: 680, height: 780, background: '#f4ead2', transform: `translateY(${docShake}px) rotate(${DOC_TILT}deg)`,
				boxShadow: '0 18px 36px rgba(0,0,0,0.28)', border: '2px solid #d8c7a2', padding: '56px 52px', fontFamily: docFont, color: '#2a221a', fontSize: 30, lineHeight: 1.75}}>
				<div data-read style={{fontSize: 34, letterSpacing: 3, marginBottom: 26}}>BOX OFFICE · STATEMENT</div>
				<div data-read>1 SEAT .............. $30.00</div>
				<div data-read>SERVICE FEE .......... $8.00</div>
				<div data-read>FACILITY FEE ......... $6.00</div>
				<div data-read>PROCESSING ........... $4.00</div>
				<div data-read style={{borderTop: '2px solid #2a221a', marginTop: 14, paddingTop: 10}}>TOTAL ............... $48.00</div>
			</div>
			<div style={{position: 'absolute', inset: 0, transformOrigin: TILT.transformOrigin, transform: `translateY(${docShake}px) ${TILT.transform}`}}>
			{t >= hitAt ? <Imprint word={word} font={font} /> : null}
			{shadow > 0 ? (
				<div style={{position: 'absolute', left: IMPRINT.x - 20 + (IMPRINT.w + 40) * (0.5 - 0.35 * (0.6 + 0.4 * shadow)), top: rest - 26,
					width: (IMPRINT.w + 40) * 0.7 * (0.6 + 0.4 * shadow), height: 36, borderRadius: '50%', background: `rgba(40,25,15,${0.28 * shadow})`, filter: 'blur(8px)'}} />
			) : null}
			{y !== null ? <Stamp x={IMPRINT.x + IMPRINT.w / 2} y={y} squash={squash} /> : null}
			</div>
		</>
	);
};
