import chalk from 'chalk';
import { palette, symbols } from '../theme.mjs';

const orbit = symbols.orbitFrames;

export function createTicker(messages) {
  let frame = 0;
  let cursor = 0;
  const spacing = '   ';

  const normalized = messages.map((msg) =>
    chalk.hex(palette.textMuted)(msg.toUpperCase())
  );

  return {
    next() {
      const prefix = chalk.hex(palette.accent)(`${orbit[frame % orbit.length]} SIGNAL`);
      const payload = normalized
        .map((msg, idx) => (idx === cursor ? chalk.hex(palette.accentAlt)(msg) : msg))
        .join(spacing);

      frame = (frame + 1) % orbit.length;
      cursor = (cursor + 1) % normalized.length;
      return `${prefix}${spacing}${payload}`;
    }
  };
}
