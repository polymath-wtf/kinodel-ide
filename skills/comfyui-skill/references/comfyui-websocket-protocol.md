---
title: "ComfyUI WebSocket Protocol"
created: 2026-06-26
updated: 2026-06-26
type: concept
tags: [comfyui, comfyui-api, websocket, reference, protocol]
sources:
  - https://github.com/PGCRT/CRT-Nodes.git
  - ComfyUI server.py source
  - user:cli:2026-06-26-crt-save-jpeg-websocket
confidence: high
contested: false
contradictions: []
---

# ComfyUI WebSocket Protocol

ComfyUI использует WebSocket (`ws://host:port/ws`) для двусторонней связи между фронтендом/бэкендом и сервером. WebSocket передаёт как text-фреймы (JSON), так и binary-фреймы (изображения, видео).

## Binary Event Types

```python
class BinaryEventTypes:
    PREVIEW_IMAGE = 1             # PNG-encoded preview
    UNENCODED_PREVIEW_IMAGE = 2   # Unencoded / format-marked image
    TEXT = 3                      # Text data
    SAVED_VIDEO = 4               # Video file path
    UNENCODED_PREVIEW_VIDEO = 5   # Video preview
```

## send_sync

```python
PromptServer.instance.send_sync(event_type, data, client_id)
```

- `event_type` — int из `BinaryEventTypes`.
- `data` — tuple, формат зависит от event_type.
- `client_id` — string ID клиента-получателя. Если `None`, сообщение не отправляется.

### UNENCODED_PREVIEW_IMAGE (type=2)

`data = ("JPEG", pil_image, None)` — ComfyUI кодирует PIL Image в JPEG и отправляет binary frame.

`data = ("PNG", pil_image, None)` — то же, но PNG.

`data = (bytes, max_rate)` — отправляет сырые байты напрямую.

## Binary frame layout

При получении binary frame от ComfyUI WebSocket:

```
[4 bytes: event_type (big-endian int)]
[4 bytes: image_type_id (big-endian int)]
[N bytes: payload (JPEG/PNG/...)]
```

См. `comfy/server.py`, функция `send_sync` и фронтенд `comfyui/web/...`.

## Client ID lifecycle

1. Клиент подключается к `ws://host:port/ws`.
2. ComfyUI отправляет `{"type": "status", "data": {"status": {"client_id": "xxx"}}}`.
3. Клиент использует `client_id` в `POST /prompt` payload.
4. ComfyUI связывает промпт с `client_id`.
5. Ноды могут вызывать `send_sync(..., s.client_id)` → сообщение уходит этому клиенту.

Если `POST /prompt` без `client_id` или без активного WS-подключения, `s.client_id` будет `None`.

## См. также

- [[crt-save-jpeg-websocket]] — нода, использующая `send_sync` с типом 2
- [[kinodel-comfyui-provider-architecture]] — архитектура ComfyUI provider
