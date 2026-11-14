# Creative Cinematic handoff (no API cost)

This experimental workflow is intentionally **not a generative AI model**. It prepares a strict ChatGPT image-edit prompt and composites the **original facial pixels** back over the generated result.

1. Run `python cinematic_workflow.py`.
2. Select an original JPEG/PNG (export a JPEG from RAW first).
3. Copy the prompt, attach the original image in ChatGPT and generate a cinematic edit.
4. Download the result **at exactly the original dimensions**. If ChatGPT changes dimensions, resize/crop/align manually first; the app intentionally rejects a mismatch.
5. Select generated result, output JPEG path, then composite.
6. Inspect every face at 100% before delivering. The compositor may have visible seams or fail on rotated, occluded, or very small faces.

## Limitations

- Haar face detection is a baseline; no guarantee of correct detection, matching, identity, anatomy, or artifact removal.
- Handles only small face translations, not rotation, significant scale change or changed expressions.
- Hair and hands are **not** protected yet; generated errors in those regions may persist.
- This workflow is a prototype, not production-quality portrait retouching.
- ChatGPT image generation is subject to plan limits; OpenAI API is not used.
