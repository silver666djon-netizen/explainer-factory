// QC harness: the real V2 composition rendered in a plain page (remotion mocked), so the release checks can read the DOM:
// where the drawing hand is, where the faces of a picture are, every mark/tag box and every text we want read.
import React from 'react';
import {createRoot} from 'react-dom/client';
import {Ctx} from 'remotion';
import {V2} from '../../pilot/remotion/src/V2.tsx';
window.renderAt = async (data, frame) => {
	if (!window.__fonts) {
		window.__fonts = Promise.all(Object.entries(data.fonts).map(([f, fam]) => new FontFace(fam, `url(/pub/fonts/${f})`).load().then((x) => document.fonts.add(x)).catch(() => 0)));
	}
	await window.__fonts;
	const root = document.getElementById('root');
	root.style.width = data.W + 'px'; root.style.height = data.H + 'px';
	window.__r = window.__r || createRoot(root);
	window.__r.render(React.createElement(Ctx.Provider, {value: {frame, fps: data.fps}}, React.createElement(V2, {data, name: 'x'})));
	await new Promise((r) => setTimeout(r, 60));
	const imgs = [...document.images].filter((i) => !i.complete);
	await Promise.all(imgs.map((i) => new Promise((r) => { i.onload = i.onerror = r; setTimeout(r, 1500); })));
};
const vis = (el) => el.checkVisibility ? el.checkVisibility({opacityProperty: true, visibilityProperty: true}) : true;
const box = (r) => [r.left, r.top, r.right, r.bottom];
window.collect = () => {
	const hands = [...document.querySelectorAll('img[data-hand]')].filter(vis).map((el) => {
		const pr = el.offsetParent ? el.offsetParent.getBoundingClientRect() : {left: 0, top: 0};
		return {tip: [pr.left + +el.dataset.tx, pr.top + +el.dataset.ty], sh: +el.dataset.sh, src: el.getAttribute('src')};
	});
	const stampHands = [...document.querySelectorAll('img[data-stamphand]')].filter(vis).map((el) => box(el.getBoundingClientRect()));
	const faces = [...document.querySelectorAll('[data-face]')].filter((el) => !el.closest('[data-covered]')).map((el) => ({kind: el.dataset.face, box: box(el.getBoundingClientRect())}));
	const marks = [...document.querySelectorAll('[data-mark]')].filter(vis).map((el) => ({kind: el.dataset.mark, box: box(el.getBoundingClientRect()), text: (el.textContent || '').trim().slice(0, 40)}));
	const reads = [...document.querySelectorAll('[data-read]')].filter(vis).filter((el) => (el.textContent || '').trim()).map((el) => {
		const r = el.getBoundingClientRect();
		const cs = getComputedStyle(el);
		const svg = el instanceof SVGElement;
		let fs = parseFloat(svg ? el.getAttribute('font-size') : cs.fontSize);
		let scale;
		if (svg) {
			const bb = el.getBBox();
			scale = bb.height ? r.height / bb.height : 1;
		} else {
			scale = el.offsetHeight ? r.height / el.offsetHeight : 1;
		}
		const fam = (svg ? el.getAttribute('font-family') : cs.fontFamily) || '';
		const col = svg ? (el.getAttribute('fill') || cs.fill) : cs.color;
		return {text: el.textContent.trim().slice(0, 40), box: box(r), fs, scale, fam, col};
	});
	// props with text we want read (plan: read_cap = cap height of the smallest such line, in the prop's own units)
	const propReads = [...document.querySelectorAll('[data-propread]')].filter(vis).map((el) => {
		const r = el.getBoundingClientRect();
		return {src: (el.getAttribute('href') || '').split('/').pop(), box: box(r), cap: (+el.dataset.propread / +el.dataset.proph) * r.height};
	});
	return {hands, stampHands, faces, marks, reads, propReads};
};
