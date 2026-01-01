import chalk from 'chalk';
import { DateTime } from 'luxon';
import { palette } from '../theme.mjs';

export function formatEventSummary(event, index) {
  const dt = DateTime.fromISO(event.date).toFormat('dd MMM HH:mm');
  const prefix = chalk.hex(palette.accent)(`#${index.toString().padStart(2, '0')}`);
  const title = chalk.bold(event.title);
  const status = chalk.hex(event.status === 'confirmed' ? palette.success : palette.warning)(
    event.status.toUpperCase()
  );
  return `${prefix} ${title} ${chalk.gray('·')} ${dt} ${chalk.gray('·')} ${status}`;
}

export function formatEventDetail(event) {
  const dt = DateTime.fromISO(event.date).setLocale('lv');
  const dateLine = `${dt.toFormat('cccc, dd LLLL yyyy')} @ ${dt.toFormat('HH:mm')}`;
  const tags = event.tags.map((tag) => chalk.inverse(` ${tag.toUpperCase()} `)).join(' ');

  return [
    chalk.bold.hex(palette.accent)(event.title),
    chalk.hex(palette.textMuted)(`${dateLine} // ${event.location}`),
    '',
    event.brief ?? 'Nav papildu piezīmju — simulēts notikums.',
    '',
    chalk.hex(palette.accentAlt)('Tagi: '),
    tags
  ].join('\n');
}
