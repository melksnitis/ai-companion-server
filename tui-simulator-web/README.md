# Event Stream CLI — Web Shell

Browser-based recreation of the streaming CLI we prototyped in Node. Renders a 50/50 log vs event feed window, animates incoming events one by one, and mirrors the `chat-stream.log` cadence for `search-events` + `list-events`.

## Preview

```
tui-simulator-web/
  index.html      ← layout scaffold
  style.css       ← color system, animations, responsive rules
  app.js          ← mocked stream logic, event queue, UI state
```

Open `index.html` directly or via a static server (e.g. `npx serve tui-simulator-web`).

## Color system

| Token            | Value     | Usage                                             |
| ---------------- | --------- | ------------------------------------------------- |
| `--cli-bg`       | `#04030f` | global background                                 |
| `--cli-panel`    | `#0e172a` | panels + header/footer                            |
| `--cli-ink`      | `#f8fbff` | primary text                                      |
| `--cli-muted`    | `#8da0c3` | tertiary text + dividers                          |
| `--cli-accent`   | `#12f7d6` | highlights, buttons, ready state                  |
| `--cli-amber`    | `#fcd34d` | tentative status + tool-call highlights           |
| `--cli-pink`     | `#ff6ad5` | hero gradients + emphasis accents                 |
| `--cli-green`    | `#4ade80` | confirmed status + power LED                      |
| `--cli-red`      | `#fb7185` | alerts / error state (reserved)                   |

Event cards inherit additional theme modifiers (`theme-aurora`, `theme-amber`, `theme-pink`, `theme-violet`) for subtle gradient glows.

## Animation vocabulary

- `slideUp`: entry for log lines + cards  
- `statusBlink`: header status icon while streaming  
- `expandIn` / `collapseOut`: detail sections toggled per event  
- `type-line`, `glow-frame`, `ticker-pulse`, `stagger-in`, etc. — descriptive chips rendered per event to signal which motion design to apply once real-time engine hooks in.

## Interaction flow

1. User submits prompt via bottom input.  
2. Header switches to busy state, log shows “AI> Izsaucu search-events + list-events.”  
3. Events appear sequentially in the right pane; each card expands on arrival, then auto-collapses depending on its `collapseAfter` rule (`next-event`, `tool-call`, `next-action`, `manual`).  
4. Clicking a card toggles it open/closed at any time.  
5. Log pane accumulates user/AI messages (left pane mirrors CLI output).

## Extensibility

- Replace `eventsFixture` in `app.js` with live data from the backend that parses `chat-stream.log`.  
- Map `collapseAfter` + `animations` to actual animation controllers (GSAP, Motion One, etc.).  
- Hook the form submission to a real API call, then stream SSE chunks into `appendLog`/`eventFeed`.
