---
name: bug comfyui endpoint drift
trigger: "ComfyUI /health works but /prompt is 404 or response is Hermes/gateway/ngrok HTML"
description: The ComfyUI URL points to the wrong service after ngrok/local endpoint drift. Re-probe endpoint identity and update COMFYUI URL.
category: bug
---

# Bug: ComfyUI endpoint drift

Crash/signature: `/health` returns 200 but `/prompt` returns 404/plain text/HTML or a non-ComfyUI body.

Cause: ngrok/local URL now points to a gateway/relay or stale service, not ComfyUI.

Fix:
1. Probe `/system_stats` and `/prompt`.
2. If identity is not ComfyUI, stop; update `COMFYUI_LOCAL_NGROK_URL` or use a real local address.
3. Do not debug workflow schemas against the wrong endpoint.
