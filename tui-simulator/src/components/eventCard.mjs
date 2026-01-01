import chalk from 'chalk';
import { DateTime } from 'luxon';
import { palette, symbols } from '../theme.mjs';

const statusGlyph = {
  confirmed: chalk.hex(palette.success)('●'),
  tentative: chalk.hex(palette.warning)('◐'),
  cancelled: chalk.gray('×')
};

const tagFormat = (tag) =>
  chalk.bgHex(palette.bg).hex(palette.accent)(` ${tag.toUpperCase()} `);

export function renderEventCard(event) {
  const dt = DateTime.fromISO(event.date);
  const dateStr = dt.toFormat('ccc, dd MMM HH:mm');
  const status = statusGlyph[event.status] ?? chalk.gray('?');
  const tags = event.tags.map(tagFormat).join(' ');

  return [
    chalk.hex(palette.accent)(`${status} ${event.title}`),
    chalk.hex(palette.textMuted)(`${dateStr} • ${event.location}`),
    chalk.hex(palette.textMuted)(tags),
    chalk.hex(palette.panel)(symbols.divider)
  ].join('\n');
}
