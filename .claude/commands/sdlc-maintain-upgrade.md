---
description: Explicitly maintain this SDLC AI SPEC repository by building and verifying an upstream Spec Kit upgrade candidate.
disable-model-invocation: true
argument-hint: "[latest|vX.Y.Z|tag|commit]"
---

Resolve the current Git repository root. Read `.agents/skills/sdlc-maintain-upgrade/SKILL.md` from that root in full and follow it as the single authoritative `sdlc-maintain-upgrade` maintenance Skill.

If that exact file is missing, its frontmatter name is not `sdlc-maintain-upgrade`, or the repository is not SDLC AI SPEC, stop instead of reproducing the workflow from this adapter.

Preserve the user's invocation target as `$ARGUMENTS` when following the canonical Skill.
