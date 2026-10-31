---
name: show-me
description: Draw the flow, architecture, pipeline or sequence under discussion as a diagram page. Use when the user asks to graph, draw, diagram, sketch or visualize how something works ("graficame", "dibujame", "show me the flow"). Do NOT use for charts of data (numbers over time, distributions).
argument-hint: "[--local] [what to draw]"
allowed-tools: [Read, Glob, Grep, Write, "Bash(xdg-open *)", "Bash(open *)", "Bash(google-chrome *)", "Bash(chromium *)"]
---

Draw this: $ARGUMENTS

`--local` in the arguments is a delivery flag (see step 5), not part of what to draw.

If nothing is left besides the flag, draw the flow or system this conversation has been about most recently. If it could be two different things, ask which one, as one question.

## 1. Pick the form from the question

| The question is… | Form |
|---|---|
| What crosses from one side to the other, and what stays | **Flow**: boxes and labelled arrows, the boundary drawn as a container |
| Who talks to whom, through what, with which credential | **Topology**: grouped boxes (dashed groups for callers, a solid container for the core), arrows labelled with protocol or credential |
| Which stages exist, who acts at each, what each one emits | **Pipeline**: stages left to right, an actor row above, outputs below each stage, exits (reject, cancel) branching down |
| In what order the calls happen between services | **Sequence**: one lifeline per service, numbered arrows, a note box where a step does several things, dashed arrows for async or optional results |

One diagram per question. Draw two only when the question really has two parts (for example, the topology and then one request through it).

## 2. Draw only what you can source

- Every box and every arrow comes from something: the conversation, the code (`file:line`), or a document (section or decision id). Read the code or doc when you can; do not draw from memory of it.
- Confirmed: a solid line. Inferred, proposed, or not built yet: a dashed line, labelled as such. When the whole diagram is a proposal, add a caption at the top: "Proposed, unconfirmed by <who decides>".
- When you can't source a piece, leave it out and list it under **Gaps**. Don't draw a plausible guess.

## 3. Style

- An HTML page with inline SVG. The page has to work in light and dark mode.
- Light neutral background. White boxes, each with a bold title and at most two lines of grey subtitle.
- One accent colour, only for the boxes and arrows the point is about. Everything else stays neutral.
- Keep arrow labels short: a verb plus the payload ("writes", "status event, from the feed"). Put explanations in a note beside the diagram, not on the arrows.
- Use monospace for identifiers: event names, states, endpoints, fields.
- Labels use the language of the material being drawn (the code, the doc). The chat uses the language of the conversation.
- Make it legible at normal zoom: no crossing arrows when a reorder avoids them, and no text smaller than the subtitle.

## 4. Under the diagram

1. One sentence in bold: the takeaway, i.e. what the reader should see in the diagram.
2. At most three short lines on what to notice.
3. **Sources**: the `file:line`, sections and decision ids the boxes came from.
4. **Gaps**, only if there are any.

## 5. Deliver

- If the user is building a page or doc that already exists, add the diagram there instead of making a new one.
- **Local only** when the arguments include `--local` or the user asks to keep it local or off claude.ai: never use the artifact tool. Write the HTML file to the session scratchpad (or the system temp dir) and open it with `xdg-open` (Linux) or `open` (macOS). If neither exists, give the full path.
- Otherwise, if an artifact tool is available, load its design and diagramming guidance first, then publish the page privately.
- With no artifact tool, write the HTML file as in local-only mode.
- Never publish to a public host unless the user asks.
- Before you deliver, check what you drew. If a headless Chrome or Chromium is on the PATH, render the page to a screenshot (`--headless=new --screenshot`), look at it, and fix any text that overflows its box or overlaps a line. Repeat until none is left. Without a headless browser, check the SVG coordinates by hand: each label's width against its box.

In the chat, reply with only the link or path and the one-line takeaway. Don't describe the diagram again in prose.
