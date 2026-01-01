import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "chat-stream.log"
OUT_PATH = ROOT / "tui-simulator-web" / "chat-stream.json"


def load_log_payloads():
    raw_text = LOG_PATH.read_text(encoding="utf-8").strip()
    if not raw_text:
        raise SystemExit("chat-stream.log appears to be empty")

    # New JSON snapshot format written by /chat/stream
    if raw_text.startswith("{"):
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"chat-stream.log JSON decode error: {exc}") from exc

        events = payload.get("events")
        if not isinstance(events, list) or not events:
            raise SystemExit("chat-stream.log JSON does not include any events")
        return events

    # Legacy SSE format (one 'data:' line per event)
    payloads = []
    for raw in raw_text.splitlines():
        raw = raw.strip()
        if not raw.startswith("data:"):
            continue
        try:
            payloads.append(json.loads(raw[6:]))
        except json.JSONDecodeError:
            continue

    if not payloads:
        raise SystemExit("chat-stream.log appears to be empty")
    return payloads


def extract_final_message(payloads):
    for payload in reversed(payloads):
        if payload.get("event") != "assistant_message":
            continue
        message = payload.get("data", {}).get("message", {})
        for block in message.get("content", []):
            text = block.get("text")
            if text and "Top 10 ziņas" in text:
                return text
    return ""


def parse_calendar_and_news(text: str):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    window_match = re.search(r"\((\d{4}\.\d{2}\.\d{2}) - (\d{4}\.\d{2}\.\d{2})\)", text)
    start, end = None, None
    if window_match:
        start = window_match.group(1).replace(".", "-")
        end = window_match.group(2).replace(".", "-")

    next_event_match = re.search(
        r"- \*\*(\d{4}\. gada \d{2}\. \w+)\*\* - \"([^\"]+)\"", text
    )
    next_event = None
    if next_event_match:
        next_event = {
            "label": next_event_match.group(1),
            "title": next_event_match.group(2),
        }

    news_items = []
    news_regex = re.compile(r"^(\d+)\.\s\*\*(.*?)\*\*\s-\s(.*)$")
    for line in lines:
        m = news_regex.match(line)
        if m:
            news_items.append({"rank": int(m.group(1)), "title": m.group(2), "summary": m.group(3)})

    summary_line = ""
    for line in lines:
        if "Nav ieplānotu notikumu" in line:
            summary_line = line

    sources = ""
    for line in lines[::-1]:
        if line.startswith("Avoti"):
            sources = line
            break

    return {
        "window": {"start": start, "end": end},
        "next_event": next_event,
        "calendar_summary": summary_line,
        "news": news_items,
        "final_sources": sources,
    }


def build_log_lines(payloads):
    lines = []
    seen_init = False

    for payload in payloads:
        event = payload.get("event")
        data = payload.get("data", {})

        if event == "message_start" and not seen_init:
            model = data.get("model")
            provider = data.get("provider") or data.get("agent_id")
            lines.append(
                {
                    "type": "system",
                    "text": f"Claude session init · model {model} via {provider}",
                }
            )
            seen_init = True

        elif event == "assistant_message":
            message = data.get("message", {})
            for block in message.get("content", []):
                tool_name = block.get("name")
                tool_input = block.get("input", {}) or {}
                if tool_name == "Task":
                    desc = tool_input.get("description", "Unknown task")
                    lines.append({"type": "command", "text": f"Task: {desc} (auto tool)"})
                elif tool_name == "mcp__google-calendar__list-events":
                    cal = tool_input.get("calendarId", "primary")
                    time_min = tool_input.get("timeMin", "")[:10]
                    time_max = tool_input.get("timeMax", "")[:10]
                    lines.append(
                        {
                            "type": "tool",
                            "text": f"Google Calendar list-events · {cal} · {time_min} → {time_max}",
                        }
                    )
                elif tool_name == "WebSearch":
                    query = tool_input.get("query", "")
                    lines.append({"type": "command", "text": f"WebSearch query: {query}"})

        elif event == "user_message":
            message = data.get("message", {})
            for block in message.get("content", []):
                # Tool responses can be either dicts or strings
                if "text" in block and block["text"]:
                    text = block["text"]
                    if "Permission to use WebSearch" in text:
                        lines.append({"type": "warning", "text": "WebSearch blocked (dontAsk mode)"})
                elif "content" in block and isinstance(block["content"], list):
                    for inner in block["content"]:
                        text = inner.get("text")
                        if not text:
                            continue
                        if text.startswith("{"):
                            try:
                                parsed = json.loads(text)
                            except json.JSONDecodeError:
                                continue
                            if parsed.get("totalCount") == 0:
                                lines.append({"type": "system", "text": "Calendar response: 0 events"})
                        elif "Permission to use WebSearch" in text:
                            lines.append({"type": "warning", "text": "WebSearch blocked (dontAsk mode)"})

    if not lines:
        lines.append({"type": "system", "text": "Claude session init"})
    return lines


def main():
    payloads = load_log_payloads()
    final_text = extract_final_message(payloads)
    if not final_text:
        raise SystemExit("Could not locate final assistant message in chat-stream.log")

    parsed = parse_calendar_and_news(final_text)
    log_lines = build_log_lines(payloads)

    next_event = parsed["next_event"] or {
        "label": "Nav pieejams",
        "title": "Nav atrasts nākamais notikums",
    }

    events = [
        {
            "id": "calendar-status",
            "title": "Nav ieplānotu notikumu tuvāko 7 dienu logā",
            "meta": parsed["calendar_summary"],
            "detail": f"Nākamais notikums: {next_event['label']} — \"{next_event['title']}\"",
        }
    ]

    for item in parsed["news"]:
        events.append(
            {
                "id": f"news-{item['rank']}",
                "title": f"{item['rank']}. {item['title']}",
                "meta": item["summary"],
            }
        )

    data = {
        "log_lines": log_lines,
        "events": events,
        "final_line": parsed["final_sources"],
        "window": parsed["window"],
        "next_event": next_event,
    }

    OUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
