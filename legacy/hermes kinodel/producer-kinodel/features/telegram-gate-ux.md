# Telegram Gate UX + Progress Notes

Session-derived notes for Kinodel production in Telegram.

## Progress updates during long operations
- Do not go silent during multi-minute renders or worker waits.
- Send short status updates at meaningful milestones:
  - request written
  - worker started
  - still polling / still running
  - worker finished
  - compact manifest promoted
- Keep these updates brief; the user prefers signal over narration.

## Gate reply normalization
- ReviewGate prompts remain text-first A/B/C/D.
- If the user replies immediately after a gate with a bare continuation phrase like `go`, `дальше`, or `иди дальше` and does not attach edit notes, treat it as approval-equivalent `A` and continue.
- If there are notes, treat the reply as `C`/edit-fix instead.

## Preview hygiene
- Copy preview URLs exactly from `render_results/*.json`.
- Never retype, truncate, or “clean up” media URLs for Telegram previews.
- For Telegram ReviewGate previews, send rendered media as native attachments from `selected_outputs[].path`, not just text links.
- For storyboard/p7 image gates and video gates, send all current selected outputs together as one Telegram media group/album whenever there are 2-10 images/videos. Telegram supports 1-10 media items in one grouped message; prefer one grouped message over separate per-shot messages.
- If there are more than 10 outputs, split into ordered albums of max 10 while preserving shot order.
- The text gate prompt (A/B/C/D) can be a separate message after the media group, with exact fallback URLs listed only if useful for debugging.
