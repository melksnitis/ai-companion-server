# Event TUI Simulator

Experimental terminal UI inspired by the `chat-stream.log` calendar/news output. Built for modular reuse: replace the fixtures or component renderers to port the UX into other stacks later.

## Stack

- [blessed](https://github.com/chjj/blessed) for layout + input handling  
- [chalk](https://github.com/chalk/chalk) and [gradient-string](https://github.com/bokub/gradient-string) for neon styling  
- [luxon](https://moment.github.io/luxon/) for timeline math

## Getting started

```bash
cd tui-simulator
npm install
npm start
```

Controls:

| Key        | Action                               |
| ---------- | ------------------------------------ |
| `q` / `esc`| Exit                                 |
| `space`    | Pause / resume news ticker animation |
| `r`        | Rotate mocked calendar events        |

## Architecture

```
src/
  fixtures/events.mjs     ← mocked calendar + news data
  theme.mjs               ← palette + shared symbols
  components/
    hero.mjs              ← header banner with gradient + next event
    eventCard.mjs         ← calendar item renderer
    newsBoard.mjs         ← stacked news signals
    ticker.mjs            ← animated status ticker
  index.mjs               ← blessed layout wiring + animation loop
```

To swap the UX later, reuse `fixtures/` as your data contract and rewrite components to match the new design system.
