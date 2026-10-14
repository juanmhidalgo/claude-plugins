# PR body: the Summary visual

Adapted from [mattpocock/skills `pr`](https://github.com/mattpocock/skills/blob/main/skills/engineering/pr/SKILL.md) (Copyright (c) 2026 Matt Pocock, MIT License), which credits Dex Horthy's `show-me` skill (HumanLayer).

The Summary is one sentence of *why*, plus at most **one** visual: the smallest view that makes the change clear.

## When to skip the visual

Skip it for a one-file change, a prose-docs or config-only diff, or a dependency bump. Prompt files that steer an agent (skills, commands, agent definitions) are code here: a change to their flow gets a visual like any other. One sentence is the whole Summary.

Add one when the diff spans several functions or files, or changes control flow, state, or layout.

## Derive it from the diff

Build the visual from `git diff <default-branch>...HEAD`, never from memory of the session: a wrong call tree misleads more than prose does. Keep only the calls, files, or states the change touches, and stay under ~15 lines.

## Pick the shape

| The change is about | Use |
|---|---|
| Logic or an algorithm | Pseudocode |
| Runtime control flow | A call tree |
| UI structure | A component tree, with the state and module boundaries that matter |
| File responsibility or a broad refactor | A shallow file tree with one comment per entry |
| Interaction between services or processes | A Mermaid `sequenceDiagram` |
| What changed inside a shape that already exists | A `diff` block of that shape |

A `diff` of the shape is usually the best fit, because it shows what moved:

```diff
 submit_order
   validate_cart
+  reserve_stock
   charge_payment
-  send_confirmation
+  enqueue_confirmation
```

```diff
 app/
 ├── orders/
+│   └── services.py      # owns reservation and charge
 ├── payments/
-└── tasks.py
+└── tasks/
+    └── confirmation.py
```

Place the visual right under the sentence it supports. One visual; if you feel the need for a second, the PR is probably two PRs.
