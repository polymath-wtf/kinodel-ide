# Endpoint liveness checks for Kinodel render jobs

Use this when a project stores a `COMFYUI_LOCAL_NGROK_URL` or similar tunnel URL.

## What to verify first
1. `GET /system_stats`
2. `POST /prompt` with a tiny test prompt
3. `GET /history/{prompt_id}` after submit
4. `GET /health` only if the deployment explicitly exposes it

Note: some ComfyUI/Ngrok deployments return 404 on `/health` even when the server is live. Do not treat `/health` alone as a liveness check.

## Failure signatures
- HTML 404 page from ngrok: tunnel is offline or misrouted; do not treat as a ComfyUI validation error.
- `Connection refused` on localhost: nothing is listening locally; the tunnel must be used or restarted.
- 200 from an unrelated service: the URL is not pointing at ComfyUI.

## Practical rule
If the tunnel URL is stale, stop before queueing render jobs. Refresh the tunnel or switch to a live endpoint; otherwise the pipeline will fail after prompt submission.

## Session note
In the pigeon-meme session, `COMFYUI_LOCAL_NGROK_URL` was present in `.env` but the tunnel at `https://normal-pleased-buck.ngrok-free.app` returned HTML 404 on `/prompt`, so renders could not proceed even though the env var looked valid.