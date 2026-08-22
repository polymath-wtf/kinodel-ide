# Understand and count tokens

Gemini and other generative AI models process input and output at a granularity
called a *token*.

**For Gemini models, a token is equivalent to about 4 characters.
100 tokens is equal to about 60-80 English words.**

## About tokens

Tokens can be single characters like `z` or whole words like `cat`. Long words
are broken up into several tokens. The set of all tokens used by the model is
called the vocabulary, and the process of splitting text into tokens is called
*tokenization*.

When billing is enabled, the [cost of a call to the Gemini API](https://ai.google.dev/pricing) is
determined in part by the number of input and output tokens, so knowing how to
count tokens can be helpful.

You can try out counting tokens in our Colab.

|---|---|---|
| [![](https://ai.google.dev/static/site-assets/images/docs/notebook-site-button.png)View on ai.google.dev](https://ai.google.dev/gemini-api/docs/tokens) | [![](https://www.tensorflow.org/images/colab_logo_32px.png)Try a Colab notebook](https://colab.research.google.com/github/google-gemini/cookbook/blob/main/quickstarts/Counting_Tokens.ipynb) | [![](https://www.tensorflow.org/images/GitHub-Mark-32px.png)View notebook on GitHub](https://colab.research.google.com/github/google-gemini/cookbook/blob/main/quickstarts/Counting_Tokens.ipynb) |

## Count tokens

All input to and output from the Gemini API is tokenized, including text, image
files, and other non-text modalities.

You can count tokens in the following ways:

- **Call [`count_tokens`](https://ai.google.dev/api/rest/v1/models/countTokens) with the input
  of the request.**   
  This returns the total number of tokens in *the
  input only*. You can make this call before sending the input to the
  model to check the size of your requests.

- **Use the `usage_metadata` attribute on the `response` object after
  calling `generate_content`.**   
  This returns the total number of
  tokens in *both the input and the output* : `total_token_count`.  
  It
  also returns the token counts of the input and output separately:
  `prompt_token_count` (input tokens) and `candidates_token_count`
  (output tokens).

  If you are using a [thinking
  model](https://ai.google.dev/gemini-api/docs/thinking), the token used during the thinking
  process are returned in `thoughts_token_count`. And if you are using
  [Context caching](https://ai.google.dev/gemini-api/docs/caching), the cached token
  count will be in `cached_content_token_count`.

### Count text tokens

If you call `count_tokens` with a text-only input, it returns the token count of
the text in *the input only* (`total_tokens`). You can make this call before
calling `generate_content` to check the size of your requests.

Another option is calling `generate_content` and then using the `usage_metadata`
attribute on the `response` object to get the following:

- The separate token counts of the input (`prompt_token_count`), the cached content (`cached_content_token_count`) and the output (`candidates_token_count`)
- The token count for the thinking process (`thoughts_token_count`)
- The total number of tokens in *both the input and the output*
  (`total_token_count`)

### Python

    from google import genai

    client = genai.Client()
    prompt = "The quick brown fox jumps over the lazy dog."

    total_tokens = client.models.count_tokens(
        model="gemini-3-flash-preview", contents=prompt
    )
    print("total_tokens: ", total_tokens)

    response = client.models.generate_content(
        model="gemini-3-flash-preview", contents=prompt
    )

    print(response.usage_metadata)

### Count multi-turn (chat) tokens

If you call `count_tokens` with the chat history, it returns the total token
count of the text from each role in the chat (`total_tokens`).

Another option is calling `send_message` and then using the `usage_metadata`
attribute on the `response` object to get the following:

- The separate token counts of the input (`prompt_token_count`), the cached content (`cached_content_token_count`) and the output (`candidates_token_count`)
- The token count for the thinking process (`thoughts_token_count`)
- The total number of tokens in *both the input and the output* (`total_token_count`)

To understand how big your next conversational turn will be, you need to append
it to the history when you call `count_tokens`.

### Python

    from google import genai
    from google.genai import types

    client = genai.Client()

    chat = client.chats.create(
        model="gemini-3-flash-preview",
        history=[
            types.Content(
                role="user", parts=[types.Part(text="Hi my name is Bob")]
            ),
            types.Content(role="model", parts=[types.Part(text="Hi Bob!")]),
        ],
    )

    print(
        client.models.count_tokens(
            model="gemini-3-flash-preview", contents=chat.get_history()
        )
    )

    response = chat.send_message(
        message="In one sentence, explain how a computer works to a young child."
    )
    print(response.usage_metadata)

    extra = types.UserContent(
        parts=[
            types.Part(
                text="What is the meaning of life?",
            )
        ]
    )
    history = [*chat.get_history(), extra]
    print(client.models.count_tokens(model="gemini-3-flash-preview", contents=history))

### Count multimodal tokens

All input to the Gemini API is tokenized, including text, image files, and other
non-text modalities. Note the following high-level key points about tokenization
of multimodal input during processing by the Gemini API:

- Image inputs with both dimensions \<=384 pixels are counted as
  258 tokens. Images larger in one or both dimensions are cropped and scaled as
  needed into tiles of 768x768 pixels, each counted as 258 tokens.

- Video and audio files are converted to tokens at the following fixed rates:
  video at 263 tokens per second and audio at 32 tokens per second.

#### Media resolutions

[Gemini 3 models](https://ai.google.dev/gemini-api/docs/models#gemini-3) introduce granular control over
multimodal vision processing with the `media_resolution` parameter. The
`media_resolution` parameter determines the
**maximum number of tokens allocated per input image or video frame.**
Higher resolutions improve the model's ability to
read fine text or identify small details, but increase token usage and latency.

For more details about the parameter and how it can impact token calculations,
see the [media resolution](https://ai.google.dev/gemini-api/docs/media-resolution) guide.

#### Image files

If you call `count_tokens` with a text-and-image input, it returns the combined
token count of the text and the image in *the input only* (`total_tokens`). You
can make this call before calling `generate_content` to check the size of your
requests. You can also optionally call `count_tokens` on the text and the file
separately.

Another option is calling `generate_content` and then using the `usage_metadata`
attribute on the `response` object to get the following:

- The separate token counts of the input (`prompt_token_count`), the cached content (`cached_content_token_count`) and the output (`candidates_token_count`)
- The token count for the thinking process (`thoughts_token_count`)
- The total number of tokens in *both the input and the output* (`total_token_count`)

Example that uses an uploaded image from the File API:

### Python

    from google import genai

    client = genai.Client()
    prompt = "Tell me about this image"
    your_image_file = client.files.upload(file=media / "organ.jpg")

    print(
        client.models.count_tokens(
            model="gemini-3-flash-preview", contents=[prompt, your_image_file]
        )
    )

    response = client.models.generate_content(
        model="gemini-3-flash-preview", contents=[prompt, your_image_file]
    )
    print(response.usage_metadata)

Example that provides the image as inline data:

### Python

    from google import genai
    import PIL.Image

    client = genai.Client()
    prompt = "Tell me about this image"
    your_image_file = PIL.Image.open(media / "organ.jpg")

    print(
        client.models.count_tokens(
            model="gemini-3-flash-preview", contents=[prompt, your_image_file]
        )
    )

    response = client.models.generate_content(
        model="gemini-3-flash-preview", contents=[prompt, your_image_file]
    )
    print(response.usage_metadata)

#### Video or audio files

Audio and video are each converted to tokens at the following fixed rates:

- Video: 263 tokens per second
- Audio: 32 tokens per second

If you call `count_tokens` with a text-and-video/audio input, it returns the
combined token count of the text and the video/audio file in *the input only*
(`total_tokens`). You can make this call before calling `generate_content` to
check the size of your requests. You can also optionally call `count_tokens` on
the text and the file separately.

Another option is calling `generate_content` and then using the `usage_metadata`
attribute on the `response` object to get the following:

- The separate token counts of the input (`prompt_token_count`), the cached content (`cached_content_token_count`) and the output (`candidates_token_count`)
- The token count for the thinking process (`thoughts_token_count`)
- The total number of tokens in *both the input and the output*
  (`total_token_count`).

### Python

    from google import genai
    import time

    client = genai.Client()
    prompt = "Tell me about this video"
    your_file = client.files.upload(file=media / "Big_Buck_Bunny.mp4")

    while not your_file.state or your_file.state.name != "ACTIVE":
        print("Processing video...")
        print("File state:", your_file.state)
        time.sleep(5)
        your_file = client.files.get(name=your_file.name)

    print(
        client.models.count_tokens(
            model="gemini-3-flash-preview", contents=[prompt, your_file]
        )
    )

    response = client.models.generate_content(
        model="gemini-3-flash-preview", contents=[prompt, your_file]
    )
    print(response.usage_metadata)

## Context windows

The models available through the Gemini API have context windows that are
measured in tokens. The context window defines how much input you can provide
and how much output the model can generate. You can determine the size of the
context window by calling the [`models.get` endpoint](https://ai.google.dev/api/rest/v1/models/get)
or by looking in the [models documentation](https://ai.google.dev/gemini-api/docs/models).

### Python

    from google import genai

    client = genai.Client()
    model_info = client.models.get(model="gemini-3-flash-preview")
    print(f"{model_info.input_token_limit=}")
    print(f"{model_info.output_token_limit=}")