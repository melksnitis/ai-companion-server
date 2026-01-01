import chalk from 'chalk';
import { palette, symbols } from '../theme.mjs';

const signalColors = {
  'macro-risk': palette.warning,
  'supply-chain': '#38bdf8',
  'defense-tech': '#f472b6',
  humanitarian: '#fb7185',
  'public-safety': '#a78bfa'
};

export function renderNewsBoard(newsItems) {
  return newsItems
    .map((item, idx) => {
      const color = signalColors[item.signal] ?? palette.accent;
      const badge = chalk.hex(color)(`#${idx + 1} ${item.signal.toUpperCase()}`);
      const headline = chalk.bold.hex(palette.accentAlt)(item.headline);
      const summary = chalk.hex(palette.textMuted)(item.summary);
      const source = chalk.hex(palette.textMuted)(`avots: ${item.source}`);

      return [badge, headline, summary, source, chalk.hex(palette.panel)(symbols.divider)].join('\n');
    })
    .join('\n');
}
