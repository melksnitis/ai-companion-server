import chalk from 'chalk';
import gradient from 'gradient-string';
import { DateTime } from 'luxon';
import { gradients, palette, symbols } from '../theme.mjs';

export function renderHero(calendarWindow, frameIndex = 0) {
  const range = `${calendarWindow.start} → ${calendarWindow.end}`;
  const next = calendarWindow.nextEvent;
  const pulse = symbols.pulseFrames[frameIndex % symbols.pulseFrames.length];
  const gradientText = gradient(gradients.hero)(` ${range} `);

  const nextLabel = next
    ? `${DateTime.fromISO(next.date).toFormat('dd LLL yyyy')} • ${next.label} @ ${next.location}`
    : 'Nav nākamā notikuma';

  return [
    chalk.bold.hex(palette.accent)(`${pulse} TERMINAL FUTURE WINDOW ${pulse}`),
    gradientText,
    chalk.hex(palette.textMuted)(nextLabel)
  ].join('\n');
}
