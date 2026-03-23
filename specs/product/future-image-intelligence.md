# Future: Image Intelligence Pipeline

## Problem

When a user uploads a non-document image (a photo, screenshot, diagram, artwork), the current system says "No fields have been extracted yet" because it only handles document extraction. The chat has no context about the image.

## Expected Behavior

1. **Auto-classify** the upload: Is this a document (KTP, invoice, contract) or a general image (photo, screenshot, diagram)?
2. If **document** → existing extraction pipeline
3. If **general image** → Image Intelligence pipeline:
   - Generate caption/description via VLM ("A man wearing a black TabLogs shirt, standing with arms crossed in an office setting")
   - Detect objects, text overlays, logos, faces (metadata)
   - Extract any visible text (OCR on screenshots, signs, labels)
   - Store caption + metadata as the "extracted fields" for chat context
   - Chat can then discuss the image: "What brand is on his shirt?" → "TabLogs"

## Pipeline

```
Upload → Classify (document vs image vs screenshot vs diagram)
  ├── Document → Extraction Pipeline (existing)
  └── Image → Image Intelligence Pipeline (new)
       ├── VLM Caption: "Describe this image in detail"
       ├── VLM OCR: "Extract any visible text"
       ├── VLM Objects: "List objects, logos, people"
       └── Store as context for chat
```

## Data Model

```python
# Reuse extracted_fields table with special field types:
field_type = "image_caption"  # VLM-generated description
field_type = "image_text"     # OCR text found in image
field_type = "image_objects"  # Detected objects/logos
field_type = "image_metadata" # EXIF, dimensions, format
```

## Implementation Notes

- Use the same DashScope Qwen-VL provider (already supports image input)
- Classification prompt: "Is this a formal document (ID card, invoice, form, letter) or a general image (photo, screenshot, diagram)? Return: document or image"
- Caption prompt: "Describe this image in detail. Include: people, objects, text, setting, colors, logos, brands."
- The chat system prompt changes based on classification:
  - Document: "Answer based on extracted fields"
  - Image: "Answer based on the image description and visible content"

## Priority

P3 — Nice to have for demo, not blocking core functionality.

## Depends On

- P2-02 (Auto-Classification) — shares the classification step
- P2-10 (Document Chat Fix) — chat needs to work first
