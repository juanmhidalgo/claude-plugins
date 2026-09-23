# Stating Critical Rules in CLAUDE.md

Current Claude models follow instructions closely and literally. A rule written
in capitals, with "no exceptions" and no reason, gets applied everywhere it
could conceivably fit — including the gray-area cases it was never meant for.
When several rules are all marked critical, the markers stop carrying
information. Write the rule once, plainly, with the reason beside it.

## State the rule and why it exists

```xml
<rule id="tests-before-commit" priority="blocking">
Run the test suite before committing. CI does not gate merges here, so a red
commit reaches `master` unnoticed.
</rule>
```

The reason is what lets the model handle the case the rule didn't anticipate
(a docs-only commit, a test that was already red before the change).

## Prefer enforcement over prose

If a rule can be checked mechanically — tests pass, no secrets in the diff,
formatting, version bumps — put it in a hook, a pre-commit check, or CI. Prose
is for the judgment calls that code can't make.

## Reserve emphasis for an observed failure

Emphasis is a targeted fix, not a register. Add it to one rule only after you
have watched that specific rule get skipped, and keep it only if it fixes that.
If you find yourself marking most rules as critical, the problem is usually
missing reasons, not missing volume.
