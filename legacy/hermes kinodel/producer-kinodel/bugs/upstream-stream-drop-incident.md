# Upstream Stream Drop Incident

**Date:** 2026-05-15
**Symptom:** Agent appeared to “lag” heavily. User sent “wtf? debug log” and “почему ты так жёстко лагаешь?”

## Root Cause
OpenRouter provider (`moonshotai/kimi-k2.6`) dropped the streaming connection after ~253s with `RemoteProtocolError: peer closed connection without sending complete message body`. Retries 2/3 and 3/3 also failed with the same error. This was upstream Cloudflare/Telegram/network latency, not agent-level slowness.

## User Impact
User perceived the agent as “lagging” and was frustrated. The agent had not proactively explained that a long operation was in progress.

## Lesson
When upstream LLM inference hangs or streams drop, the Producer must:
1. Proactively explain the delay (“Upstream stream dropped, retrying...”).
2. Offer alternatives (retry, switch approach, background the task).
3. Never stay silent during extended waits.

For Kinodel specifically: background render workers (`terminal(background=true, notify_on_complete=true)`) prevent the agent process from being tied up during long provider polling, keeping the conversation responsive.
