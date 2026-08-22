---
title: Gemini Embedding 2
created: 2026-05-04
updated: 2026-05-22
type: entity
tags: [embedding, rag, model, guide, knowledge-graph]
sources:
  - raw/rag/gemini-embedding-2-en.md
  - raw/rag/gemini-embedding-2-ru.md
  - raw/rag/gemini-embedding-full-docs.md
  - raw/rag/mrl.md
  - raw/rag/embedding-2-hermes-deep-research.md
confidence: high
contested: false
contradictions: []
---

# Gemini Embedding 2

`gemini-embedding-2` — актуальная мультимодальная embedding-модель Google Gemini API. Она отображает текст, изображения, аудио, видео и PDF в единое векторное пространство, поэтому подходит для RAG, semantic search, classification, clustering и cross-modal retrieval. Эта страница — компактный рабочий гайд по `gemini-embedding-2`. full docs ^[raw/rag/gemini-embedding-full-docs.md]

## TL;DR для проекта

- **Модель:** использовать `gemini-embedding-2`.
- **Python SDK:** использовать `google-genai`: `from google import genai`.
- **Размерность:** по умолчанию 3072; для RAG обычно выбирать 768 или 1536 через `output_dimensionality`.
- **Task instruction:** для `gemini-embedding-2` не использовать API-поле `task_type`; задачу писать прямо в тексте/prompt prefix.
- **Совместимость:** query vectors и document vectors должны иметь одинаковые `model`, `output_dimensionality` и совместимую схему форматирования.
- **Мультимодальность:** текст, image, audio, video и PDF можно индексировать в одном пространстве, но для production лучше явно хранить modality/source metadata.

## Core specs

| Параметр | Значение |
|:---|:---|
| API model code | `gemini-embedding-2` |
| Input modalities | text, image, audio, video, PDF |
| Output | text embedding vector |
| Input token limit | 8,192 tokens |
| Output dimensions | 128–3072 |
| Recommended dimensions | 768, 1536, 3072 |
| Languages | 100+ |
| Stable update | April 2026 |

## Архитектура RAG

### Индексация

1. **Normalize source:** привести markdown/PDF/transcript/media metadata к стабильному internal format.
2. **Chunk:** нарезать текст на небольшие смысловые блоки.
3. **Format document text:** добавить `title` и `text`, чтобы embedding отражал retrieval context.
4. **Embed:** вызвать `client.models.embed_content(model="gemini-embedding-2", ...)`.
5. **Store:** сохранить vector + metadata в vector DB / sqlite-vec / pgvector / другой индекс.

### Runtime retrieval

1. **Format query:** добавить task prefix для нужного режима поиска.
2. **Embed query:** использовать ту же модель и ту же `output_dimensionality`, что у индекса.
3. **Retrieve:** ANN/vector search + metadata filters.
4. **Optional rerank:** rerank кандидатных чанков более дорогой размерностью или LLM.
5. **Synthesize:** передать найденные chunks в генеративную модель.

### Chunking recommendations

Контекст 8192 tokens — это максимальный вход, а не оптимальный размер чанка.

| Тип данных | Рекомендация |
|:---|:---|
| Markdown/wiki docs | 512–1024 tokens |
| Плотный technical text/code | 400–700 tokens |
| Narrative/story material | 800–1200 tokens |
| Overlap | 10–15% |
| Metadata | `source`, `path`, `title`, `section`, `modality`, `created_at`, `project_id` |

Для [[rag-memory]] и [[kinodel-rag-concept]] полезно хранить не только vector, но и короткий `retrieval_text`, из которого этот vector был получен.

## Task formatting для `gemini-embedding-2`

Для text-only задач Google рекомендует задавать задачу прямо в строке. Для RAG чаще всего нужен asymmetric retrieval: query и document форматируются по-разному.

### Asymmetric retrieval

| Use case | Query format | Document format |
|:---|:---|:---|
| Search | `task: search result \| query: {content}` | `title: {title} \| text: {content}` |
| Question answering | `task: question answering \| query: {content}` | `title: {title} \| text: {content}` |
| Fact checking | `task: fact checking \| query: {content}` | `title: {title} \| text: {content}` |
| Code retrieval | `task: code retrieval \| query: {content}` | `title: {title} \| text: {content}` |

### Symmetric tasks

| Use case | Input format |
|:---|:---|
| Classification | `task: classification \| query: {content}` |
| Clustering | `task: clustering \| query: {content}` |
| Semantic similarity | `task: sentence similarity \| query: {content}` |

Не использовать `sentence similarity` как основной формат для RAG search: он предназначен для сравнения близости фраз, а не для document retrieval.

## Matryoshka Representation Learning (MRL)

MRL — ключевая причина, почему `gemini-embedding-2` удобен для многоуровневого RAG. Модель обучена так, что первые компоненты embedding vector несут плотное семантическое ядро, а дополнительные компоненты добавляют детализацию. Поэтому можно запрашивать разные `output_dimensionality` под разные уровни recall/rerank/storage без смены модели.^[raw/rag/mrl.md]

### Почему это важно для chunk architecture

Разные chunk types имеют разную цену ошибки:

- **Мелкий chunk:** должен быстро находиться по точному смыслу.
- **Крупный section/artifact chunk:** должен сохранять широкий контекст.
- **Multimodal asset:** часто требует больше fidelity, потому что вектор кодирует не только текст.
- **Final memory chunk:** должен быть стабильным и пригодным для будущего retrieval.

MRL позволяет хранить несколько профилей одного и того же знания: дешёвый vector для first-pass retrieval и более дорогой vector для точного rerank.

### Dimension profiles

| Profile | `output_dimensionality` | Роль | Что индексировать |
|:---|---:|:---|:---|
| `fast_recall` | 256 | быстрый широкий поиск | заголовки, short summaries, metadata-heavy chunks |
| `default_rag` | 768 | основной production retrieval | wiki chunks, markdown sections, обычные project notes |
| `deep_retrieval` | 1536 | rerank / сложная семантика | длинные sections, mixed-domain docs, важные design notes |
| `full_fidelity` | 3072 | максимальная точность | multimodal assets, финальные memory artifacts, research snapshots |

### MRL memory economics

Storage cost почти линейно зависит от `output_dimensionality`: меньше координат — меньше RAM/disk в vector DB и быстрее ANN search.

| Dimension | Relative storage | Экономия против 3072 | Практический смысл |
|:---|---:|---:|:---|
| 3072 | 100% | 0% | maximum fidelity для самых важных multimodal/final memory chunks |
| 1536 | 50% | 50% | глубокий rerank и сложные архитектурные chunks |
| 768 | 25% | 75% | основной balanced режим для production RAG |
| 256 | 8.3% | ~91.7% | дешёвый first-pass retrieval по большому vault |

Главный trade-off: 256/768 резко уменьшают индекс и ускоряют поиск, но для нюансных multimodal/story/contract chunks лучше держать 1536 или 3072.^[raw/rag/mrl.md]

### Suggested chunk profiles for our wiki/Kinodel memory

| Chunk level | Пример | Dimension | Причина |
|:---|:---|---:|:---|
| `summary_chunk` | краткое описание страницы / артефакта | 256 | дешёвый recall по всему vault |
| `text_chunk` | обычный markdown/RAG chunk | 768 | баланс качества, скорости и storage |
| `section_chunk` | крупный раздел с архитектурой | 768 или 1536 | больше контекста, меньше потерь смысла |
| `code_or_contract_chunk` | схемы, JSON contracts, API notes | 1536 | важны детали и точное совпадение intent |
| `multimodal_chunk` | image/PDF/video/audio embedding | 1536 или 3072 | больше semantic fidelity для non-text signals |
| `final_memory_chunk` | `final_chunk`, season/episode memory, durable artifact | 1536 или 3072 | высокая цена ошибки при future retrieval |

### Hard invariants

- **Не смешивать размерности в одном vector index:** query vector и indexed vectors должны иметь одинаковую длину.
- **Каждый dimension profile — отдельная колонка или отдельный индекс:** например `embedding_256`, `embedding_768`, `embedding_1536`.
- **Смена dimension требует rebuild:** если индекс построен на 768, query тоже должен быть 768.
- **Смена модели требует rebuild:** embeddings разных моделей нельзя сравнивать напрямую.
- **Task formatting должен быть стабильным:** document/query prefixes являются частью embedding contract.

### Retrieval cascade

Практичная схема:

1. **Metadata/FTS filter:** path, project, modality, type, date.
2. **256-dim first pass:** дешёвый recall по большой базе.
3. **768-dim default retrieval:** основной candidate set.
4. **1536/3072 rerank:** только для top-K важных кандидатов.
5. **LLM synthesis:** финальная сборка ответа из найденных chunks.

`gemini-embedding-2` автоматически нормализует non-default dimensions, поэтому для cosine similarity не нужен отдельный manual normalization step.^[raw/rag/gemini-embedding-full-docs.md]

## Python setup

```python
from google import genai
from google.genai import types

client = genai.Client()
```

`genai.Client()` берёт credentials из окружения. Для Gemini API обычно нужен `GEMINI_API_KEY`.

## Python: simple text embedding

```python
from google import genai

client = genai.Client()

result = client.models.embed_content(
    model="gemini-embedding-2",
    contents="What is the meaning of life?",
)

embedding = result.embeddings[0].values
print(len(embedding))
```

## Python: RAG document/query embeddings

```python
from google import genai
from google.genai import types

client = genai.Client()


def prepare_document(content: str, title: str | None = None) -> str:
    if title is None:
        title = "none"
    return f"title: {title} | text: {content}"


def prepare_query(query: str) -> str:
    return f"task: search result | query: {query}"


doc_result = client.models.embed_content(
    model="gemini-embedding-2",
    contents=prepare_document(
        content="Embeddings turn source material into vectors for semantic retrieval.",
        title="RAG architecture notes",
    ),
    config=types.EmbedContentConfig(output_dimensionality=768),
)

query_result = client.models.embed_content(
    model="gemini-embedding-2",
    contents=prepare_query("How should I build a RAG index?"),
    config=types.EmbedContentConfig(output_dimensionality=768),
)

doc_vector = doc_result.embeddings[0].values
query_vector = query_result.embeddings[0].values
```

## Python: choose output dimensionality

```python
from google import genai
from google.genai import types

client = genai.Client()

result = client.models.embed_content(
    model="gemini-embedding-2",
    contents="What is the meaning of life?",
    config=types.EmbedContentConfig(output_dimensionality=768),
)

embedding = result.embeddings[0].values
print(f"Length of embedding: {len(embedding)}")
```

## Python: cosine similarity

```python
import numpy as np


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a)
    vb = np.array(b)
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)))


score = cosine_similarity(query_vector, doc_vector)
print(score)
```

## Multimodal embeddings

`gemini-embedding-2` кладёт разные modalities в одно vector space. Это позволяет искать image/PDF/video/audio через text query, если они были проиндексированы как embeddings с корректными metadata.

### Modality limits

| Modality | Limit |
|:---|:---|
| Text | up to 8,192 tokens |
| Image | up to 6 images, PNG/JPEG |
| Audio | up to 180 seconds, MP3/WAV |
| Video | up to 120 seconds, MP4/MOV; max 32 processed frames |
| PDF | up to 6 pages |

### Python: image embedding

```python
from google import genai
from google.genai import types

client = genai.Client()

with open("example.png", "rb") as f:
    image_bytes = f.read()

result = client.models.embed_content(
    model="gemini-embedding-2",
    contents=[
        types.Part.from_bytes(
            data=image_bytes,
            mime_type="image/png",
        ),
    ],
)

image_vector = result.embeddings[0].values
```

### Python: text + image as one aggregated embedding

Если передать несколько parts прямо в `contents`, модель вернёт один aggregated embedding для всего объекта.

```python
from google import genai
from google.genai import types

client = genai.Client()

with open("dog.png", "rb") as f:
    image_bytes = f.read()

result = client.models.embed_content(
    model="gemini-embedding-2",
    contents=[
        "An image of a dog",
        types.Part.from_bytes(
            data=image_bytes,
            mime_type="image/png",
        ),
    ],
)

post_vector = result.embeddings[0].values
```

### Python: text and image as separate embeddings

Если нужны отдельные vectors, обернуть каждый input в отдельный `types.Content`.

```python
from google import genai
from google.genai import types

client = genai.Client()

with open("dog.png", "rb") as f:
    image_bytes = f.read()

result = client.models.embed_content(
    model="gemini-embedding-2",
    contents=[
        types.Content(parts=[types.Part.from_text(text="An image of a dog")]),
        types.Content(
            parts=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type="image/png",
                ),
            ]
        ),
    ],
)

text_vector = result.embeddings[0].values
image_vector = result.embeddings[1].values
```

### Python: generic file embedding

```python
from google import genai
from google.genai import types

client = genai.Client()


def embed_file(path: str, mime_type: str) -> list[float]:
    with open(path, "rb") as f:
        data = f.read()

    result = client.models.embed_content(
        model="gemini-embedding-2",
        contents=[
            types.Part.from_bytes(
                data=data,
                mime_type=mime_type,
            ),
        ],
    )
    return result.embeddings[0].values


audio_vector = embed_file("example.mp3", "audio/mpeg")
video_vector = embed_file("example.mp4", "video/mp4")
pdf_vector = embed_file("example.pdf", "application/pdf")
```

## Production notes

- **Keep vector contracts stable:** changing model or dimension requires rebuilding the index.
- **Store metadata separately:** never rely on vector alone; keep `source`, `title`, `chunk_id`, `modality`, and project-specific IDs.
- **Use aggregated embeddings intentionally:** good for post-level representation, bad when you need per-item retrieval.
- **Use separate embeddings for retrieval granularity:** chunk/page/shot/asset should each have its own vector if they must be independently retrieved.
- **Use Batch API for throughput:** useful when latency is not critical and many embeddings can be generated offline.

## Integration with Hermes Agent

Hermes-oriented default profile:

| Setting | Value |
|:---|:---|
| Provider | `google-genai` |
| Model | `gemini-embedding-2` |
| Default dimension | 768 |
| Local vector store | sqlite-vec or equivalent |
| Hybrid search | FTS5 + vector retrieval + RRF |

Для Kinodel archival RAG см. [[kinodel-rag-concept]]. Для general agent memory см. [[rag-memory]].

## Relationships

- Используется в [[rag-memory]] как embedding backbone для semantic memory.
- Используется в [[kinodel-rag-concept]] для векторизации cinematic artifacts и final chunks.
- Связан с [[comparisons-index]] как кандидат для model/provider comparisons.

