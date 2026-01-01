import blessed from 'blessed';
import chalk from 'chalk';
import { palette } from './theme.mjs';
import {
  calendarWindow,
  calendarEvents,
  newsItems,
  newsTickerSeeds
} from './fixtures/events.mjs';
import { renderHero } from './components/hero.mjs';
import { renderEventCard } from './components/eventCard.mjs';
import { renderNewsBoard } from './components/newsBoard.mjs';
import { createTicker } from './components/ticker.mjs';

const screen = blessed.screen({
  smartCSR: true,
  dockBorders: true,
  title: 'Letta Event Simulator — Prototype TUI'
});

screen.key(['escape', 'q', 'C-c'], () => {
  cleanup();
  process.exit(0);
});

const heroBox = blessed.box({
  top: 0,
  left: 0,
  width: '100%',
  height: 6,
  padding: {
    top: 1,
    left: 2
  },
  tags: true,
  style: {
    fg: palette.accent,
    bg: palette.bg
  }
});

const eventsBox = blessed.box({
  top: 6,
  left: 0,
  width: '50%',
  bottom: 3,
  padding: 1,
  label: ' Calendar Sim ',
  border: 'line',
  style: {
    fg: '#ffffff',
    bg: palette.bg,
    border: {
      fg: palette.panel
    }
  },
  scrollable: true,
  alwaysScroll: true,
  tags: true
});

const newsBox = blessed.box({
  top: 6,
  left: '50%',
  width: '50%',
  bottom: 3,
  padding: 1,
  label: ' News Signals ',
  border: 'line',
  style: {
    fg: '#ffffff',
    bg: palette.bg,
    border: {
      fg: palette.panel
    }
  },
  scrollable: true,
  tags: true
});

const tickerBox = blessed.box({
  bottom: 0,
  left: 0,
  width: '100%',
  height: 3,
  padding: {
    left: 2,
    top: 0
  },
  style: {
    fg: palette.accent,
    bg: palette.panel
  }
});

const helpBox = blessed.box({
  bottom: 3,
  right: 0,
  width: 28,
  height: 5,
  padding: {
    left: 1,
    right: 1
  },
  tags: true,
  content: chalk.hex(palette.textMuted)(
    ['q / esc: exit', 'r: reshuffle events', 'space: freeze ticker'].join('\n')
  ),
  border: 'line',
  style: {
    fg: palette.textMuted,
    border: {
      fg: palette.panel
    },
    bg: palette.bg
  }
});

screen.append(heroBox);
screen.append(eventsBox);
screen.append(newsBox);
screen.append(tickerBox);
screen.append(helpBox);

const ticker = createTicker(newsTickerSeeds);
let heroFrame = 0;
let tickerFrozen = false;
let tickerInterval;

function paintEvents(data = calendarEvents) {
  const content = data.map(renderEventCard).join('\n\n');
  eventsBox.setContent(content);
}

function paintNews() {
  newsBox.setContent(renderNewsBoard(newsItems));
}

function paintHero() {
  heroBox.setContent(renderHero(calendarWindow, heroFrame));
  heroFrame += 1;
}

function startTicker() {
  tickerInterval = setInterval(() => {
    if (tickerFrozen) return;
    tickerBox.setContent(ticker.next());
    screen.render();
  }, 400);
}

function stopTicker() {
  if (tickerInterval) {
    clearInterval(tickerInterval);
    tickerInterval = null;
  }
}

function cleanup() {
  stopTicker();
}

screen.key('space', () => {
  tickerFrozen = !tickerFrozen;
});

screen.key('r', () => {
  const rotated = calendarEvents.slice(1).concat(calendarEvents[0]);
  paintEvents(rotated);
  screen.render();
});

paintHero();
paintEvents();
paintNews();
startTicker();

const heroInterval = setInterval(() => {
  paintHero();
  screen.render();
}, 160);

screen.on('destroy', () => {
  cleanup();
  clearInterval(heroInterval);
});

screen.render();
