Надо будет сюда упаковать контекст comfyui тулы

Comfyui это локальный софт, в котором можно запустить opensource дифузионные модели для генерации контента.

## Generation Tool Calls

Мы планируем как минимум эти генерации запустить на mvp, для создания полноценного cinematic.

| Creative node | Following tool node | Saved selected media |
|---|---|---|
| Wardrobe | `anchor-gen` | `anchor_frames` |
| Storyboard | `frames-gen` | `story_frames` |
| Filmmaker | `video-gen` | `shot_videos` |


## Rest api

С comfyui можно общаться двумя способами:
1. Local (http), Comfyui запущенный локально, или https через ngrok.
Реквесты работают по схеме REST API (см. skills\comfyui-skill\references\rest-api.md)
Сссылки на воркеров храним в .env

2. Serverless Endpoint (https), runpod с dockerfile comfyui-worker. POST MVP feature, потому что там немного другие реквесты, нам достаточно будет local варианта для mvp.