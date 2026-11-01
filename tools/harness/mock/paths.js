export const evolvePath = (p, d) => {
	const el = document.createElementNS('http://www.w3.org/2000/svg', 'path'); el.setAttribute('d', d);
	const L = el.getTotalLength();
	return {strokeDasharray: `${L} ${L}`, strokeDashoffset: L * (1 - p)};
};
const _p = (d) => { const el = document.createElementNS('http://www.w3.org/2000/svg', 'path'); el.setAttribute('d', d); return el; };
export const getLength = (d) => _p(d).getTotalLength();
export const getPointAtLength = (d, l) => { const q = _p(d).getPointAtLength(l); return {x: q.x, y: q.y}; };
