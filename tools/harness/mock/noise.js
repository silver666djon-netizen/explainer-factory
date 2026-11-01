export const noise2D = (seed, x, y) => Math.sin(x * 12.9898 + y * 78.233 + seed.length * 3.1) * 0.5;
