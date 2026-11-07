// QC harness stand-in for @remotion/rough-notation (its bundle needs remotion/no-react): the annotated text keeps its
// place and size; the hand-drawn ink is not needed for the DOM checks.
import React from 'react';
const wrap = ({children}) => React.createElement('span', {style: {position: 'relative', display: 'inline-block'}}, children);
export const Circle = wrap;
export const Underline = wrap;
export const Box = wrap;
export const Highlight = wrap;
export const StrikeThrough = wrap;
export const CrossedOff = wrap;
export const Bracket = wrap;
