# J33-AI Skills

Shared Claude Code skills for the J33-AI team, packaged as an installable plugin marketplace.

## Install

In Claude Code:

```
/plugin marketplace add J33-AI/skills
/plugin install koboyo@j33-skills
```

(Private repo — your `gh` auth must have access to J33-AI.)

Manual alternative: copy any `plugins/<name>/skills/<name>/` directory into `~/.claude/skills/`.

## Skills

| Skill | What it does |
|---|---|
| **koboyo** | Diagram-as-code on [koboyo.com](https://koboyo.com): the full verified DSL (nodes, edges, groups, icons, 20 diagram families incl. sequence blocks, ERD crow's-foot, orgchart) plus the battle-tested browser rendering workflow — clean-canvas recipe, export gotchas, layout model. Everything was verified by live rendering; includes the traps (flowchart family is single-lane, Cmd+A misses off-viewport shapes, export needs two round-trips) so agents don't rediscover them. |

## Contributing

One directory per plugin under `plugins/`, with `.claude-plugin/plugin.json` and `skills/<name>/SKILL.md` (agentskills spec: `name` + `description` frontmatter, description starts with "Use when..."). Add an entry to `.claude-plugin/marketplace.json`. Skills must be tested before publishing — baseline an agent without the skill, verify compliance with it.
