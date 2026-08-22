---
name: simplification-cascades
description: Find one insight that eliminates multiple components - "if this is true, we don't need X, Y, or Z"
when_to_use: when implementing the same concept multiple ways, accumulating special cases, or complexity is spiraling
version: 1.1.0
---

# Simplification Cascades

## Overview

Sometimes one insight eliminates 10 things. Look for the unifying principle that makes multiple components unnecessary.

**Core principle:** "Everything is a special case of..." collapses complexity dramatically.

## Quick Reference

| Symptom | Likely Cascade |
|---------|----------------|
| Same thing implemented 5+ ways | Abstract the common pattern |
| Growing special case list | Find the general case |
| Complex rules with exceptions | Find the rule that has no exceptions |
| Excessive config options | Find defaults that work for 95% |

## The Pattern

**Look for:**
- Multiple implementations of similar concepts
- Special case handling everywhere
- "We need to handle A, B, C, D differently..."
- Complex rules with many exceptions

**Ask:** "What if they're all the same thing underneath?"

## Examples

### Cascade 1: Stream Abstraction
**Before:** Separate handlers for batch/real-time/file/network data
**Insight:** "All inputs are streams - just different sources"
**After:** One stream processor, multiple stream sources
**Eliminated:** 4 separate implementations

### Cascade 2: Resource Governance
**Before:** Session tracking, rate limiting, file validation, connection pooling (all separate)
**Insight:** "All are per-entity resource limits"
**After:** One ResourceGovernor with 4 resource types
**Eliminated:** 4 custom enforcement systems

### Cascade 3: Immutability
**Before:** Defensive copying, locking, cache invalidation, temporal coupling
**Insight:** "Treat everything as immutable data + transformations"
**After:** Functional programming patterns
**Eliminated:** Entire classes of synchronization problems

### Cascade 4: File-Only Artifacts (Kinodel ownership pitfall)
**Before:** Treating every local JSON artifact as a simple disk mutation, which tempted Producer to write specialist-owned creative/planner artifacts directly and break ownership boundaries.
**Insight:** "Local file I/O is not the ownership boundary; artifact ownership is." Deterministic Producer-owned state repairs can be direct writes, but specialist-owned artifacts must still go through their owner skill/subagent.
**After:** Producer may directly repair its own deterministic state/metadata, then validate. Producer must delegate creative/planner artifacts (`story.json`, `wardrobe_request.json`, `storyboard_requests.json`, `video_requests.json`) to the owner skill even when the JSON shape looks obvious.
**Eliminated:** Wrong Producer shortcuts while still avoiding unnecessary subagents for true Producer-owned deterministic repairs.

### Cascade 5: Minimal BriefGate (Kinodel creative ownership)
**Before:** Producer collected or inferred a large 9-field creative brief (`story_seed`, `hook`, `intrigue`, `world`, `ending`, etc.). This made Producer accidentally act as the screenwriter and produced mediocre pre-shaped stories before `storytell-kinodel` ran.
**Insight:** "BriefGate captures constraints; Storytell creates story." A start brief is not the narrative artifact. It should preserve the user's intent and production constraints, then hand off to the screenwriter.
**After:** Producer captures only `user_vibe`, `characters`/subjects, `feature`/must-keep, and workflow/format defaults. `storytell-kinodel` owns hook, intrigue, world/style, ending, emotional arc, and shot beats in `story.json`.
**Eliminated:** Producer-authored plot summaries, duplicated story fields in `brief.json`, weak invented hooks, and context-heavy approval cards that confuse runtime ownership.

## Process

1. **List the variations** - What's implemented multiple ways?
2. **Find the essence** - What's the same underneath?
3. **Extract abstraction** - What's the domain-independent pattern?
4. **Test it** - Do all cases fit cleanly?
5. **Measure cascade** - How many things become unnecessary?

## Red Flags You're Missing a Cascade

- "We just need to add one more case..." (repeating forever)
- "These are all similar but different" (maybe they're the same?)
- Refactoring feels like whack-a-mole (fix one, break another)
- Growing configuration file
- "Don't touch that, it's complicated" (complexity hiding pattern)

## Remember

- Simplification cascades = 10x wins, not 10% improvements
- One powerful abstraction > ten clever hacks
- The pattern is usually already there, just needs recognition
- Measure in "how many things can we delete?"
