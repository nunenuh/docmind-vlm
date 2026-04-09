# Image Intelligence for Document Chat

## Problem

When a user uploads an image (photo, not a structured document), the extraction pipeline extracts some fields but the chat only uses text fields as context. The VLM never sees the actual image during chat, so it can't answer visual questions.

## Solution: Caption + Image Pass-through (Option 3)

### At Extraction Time
After normal field extraction, if the document is an image (not PDF), generate a detailed caption:

```
Image → VLM Extract (normal fields) → VLM Caption (detailed description) → store both
```

Caption is stored as a special extracted field:
```python
{
    "field_type": "image_caption",
    "field_key": "image_description",
    "field_value": "A man wearing a black t-shirt with TabLogs logo, standing with arms crossed in a modern office...",
    "confidence": 0.95,
}
```

### At Chat Time
Download the document image from storage and pass it alongside text context to the VLM:

```
User asks question
  → Download image from Supabase Storage
  → Load extracted fields (including caption)
  → Send to VLM: images=[document_image] + system_prompt with fields
  → VLM sees both text context AND the actual image
```

## Implementation

### 1. Postprocess node — add caption generation for images

In `library/pipeline/extraction/postprocess.py`, after confidence merging, if the document is a single-page image, call VLM to generate caption:

```python
CAPTION_PROMPT = """Describe this image in detail. Include:
- People (appearance, clothing, pose, expression)
- Objects (logos, text, items, accessories)
- Setting (indoor/outdoor, background, lighting)
- Text visible in the image
- Overall context and purpose of the image

Be thorough and specific."""
```

Store as an extracted field with `field_type="image_caption"`.

### 2. ChatService — pass image to VLM

In `modules/chat/services.py`, add a method to load the document image:

```python
class ChatService:
    async def stream_chat(self, message, system_prompt, history, document_image=None):
        provider = get_vlm_provider()
        images = [document_image] if document_image is not None else []
        async for event in provider.chat_stream(
            images=images,
            message=message,
            history=history,
            system_prompt=system_prompt,
        ):
            yield event
```

### 3. ChatUseCase — download image before streaming

In `modules/chat/usecase.py`, download the image from storage:

```python
# Load document image for visual grounding
image = None
if doc.file_type in ("png", "jpg", "jpeg", "webp", "tiff"):
    file_bytes = self.storage_service.load_file_bytes(doc.storage_path)
    image = cv2.imdecode(np.frombuffer(file_bytes, np.uint8), cv2.IMREAD_COLOR)
```

### 4. System prompt update

When image is available, append to system prompt:
```
You can see the actual document image. Use both the extracted fields AND the image to answer questions.
If asked about visual details not in the extracted fields, describe what you see in the image.
```

## Files to modify

| File | Change |
|------|--------|
| `modules/chat/services.py` | Add `document_image` param to `stream_chat()` |
| `modules/chat/usecase.py` | Download image from storage, pass to service |
| `modules/documents/services.py` | Add `load_document_image()` to `DocumentStorageService` |
| `library/pipeline/extraction/postprocess.py` | Add caption generation for image documents |

## Priority

P1 — improves chat quality significantly for image documents.
