const cv = document.createElement('canvas').getContext('2d');
export const measureText = ({text, fontFamily, fontSize}) => { cv.font = `${fontSize}px '${fontFamily}'`; return {width: cv.measureText(text).width, height: fontSize}; };
export const fitText = ({text, withinWidth, fontFamily}) => { const w = measureText({text, fontFamily, fontSize: 100}).width; return {fontSize: 100 * withinWidth / Math.max(w, 1)}; };
