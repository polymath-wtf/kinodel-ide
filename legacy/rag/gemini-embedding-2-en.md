## Preview

Gemini Embedding 2 is Google's embedding generation model that's
ideal for complex retrieval and analytics tasks.

Gemini Embedding 2 accepts multimodal inputs to generate
3072-dimensional vectors. It accepts images, text, documents, audio, and video
inputs and semantically maps the generated vectors into a unified semantic
space. This lets you perform tasks, such as searching for an image based on a
text description.

Gemini Embedding 2 introduces several features to optimize
embedding quality and flexibility:

- **Custom task instructions:** By specifying task instructions---for
  example, `task:code retrieval` or `task:search result`---optimize
  the embeddings for the intended relationships and retrieve more accurate results
  for the specific goal.

- **Adjustable result size:** The model generates a 3072-dimensional float
  vector, by default. However, you can retrieve a smaller dimensional output by
  specifying the `output_dimensionality` parameter.

- **Document OCR:** Read OCR from document inputs.

- **Audio track extraction:** Extract audio tracks from video inputs and
  interleave them with video frames.


[Try in Vertex AI](https://console.cloud.google.com/vertex-ai/generative/multimodal/create/text?model=gemini-embedding-2-preview) [(Preview) Deploy example app](https://console.cloud.google.com/vertex-ai/studio/multimodal?suggestedPrompt=How+does+AI+work&deploy=true&model=gemini-embedding-2-preview)
Note: To use the "Deploy example app" feature, you need a Google Cloud project with billing and Vertex AI API enabled.

| Model ID | `gemini-embedding-2-preview` ||
| Supported inputs \& outputs | - Inputs: Text, Images, Audio, Video, PDF - Outputs: Embeddings ||
| Token limits | - Maximum input tokens: 8,192 - Maximum output tokens: N/A ||
| Maximum sequence length | 8,192 tokens ||
| Output dimensions | Up to 3,072 (with MRL support) ||
| Consumption options | - Supported - [Standard PayGo](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/standard-paygo) - Not supported - [Provisioned Throughput](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/provisioned-throughput) - [Flex PayGo](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/flex-paygo) - [Priority PayGo](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/priority-paygo) - [Batch prediction](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/multimodal/batch-prediction-gemini) ||
| Consumption options |
|---|---|---|
| See [Consumption options](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/deploy/consumption-options) for more information. ||
| **Images** | - Maximum images per prompt: 6 - Maximum file size per file for inline data or direct uploads through the console: No limit - Maximum file size per file from Google Cloud Storage: No limit - Maximum number of output images per prompt: N/A - Supported MIME types: `image/png`, `image/jpeg` |
| **Documents** | - Maximum number of files per prompt: 1 - Maximum number of pages per file: 6 - Maximum file size per file: N/A - Supported MIME types: `application/pdf` |
| **Video** | - Maximum video length (with audio): 80 seconds - Maximum video length (without audio): 120 seconds - Maximum number of videos per prompt: 1 - Supported MIME types: `video/mpeg`, `video/mp4` |
| **Audio** | - Maximum audio length per prompt: 80 seconds - Maximum number of audio files per prompt: 1 - Supported MIME types: `audio/mp3`, `audio/wav` |
| **Parameter defaults** |   |
| Model availability | - United States - us-central1 |
| See [Deployments and endpoints](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/locations) for more information. 