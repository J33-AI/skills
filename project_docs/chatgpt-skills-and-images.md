# ChatGPT skills and ChatGPT Images 2.0

Research notes behind `chatgpt-skills/`. Checked 2026-08-30.

## Skills in ChatGPT

- Same format as Claude Code: a folder with `SKILL.md` (frontmatter `name` and
  `description`) plus optional `scripts/`, `references/`, `assets/`, `agents/openai.yaml`.
  A skill exported from Claude Code uploads as-is.
- Upload: Skills → Create → Upload from your computer. ChatGPT scans the package before
  it becomes available.
- Invocation: implicit, from the description, or explicit with `@`. Descriptions may be
  shortened to fit the context budget, so the trigger words go first.
- `agents/openai.yaml` (optional): `display_name`, `short_description`, icons,
  `brand_color`, `allow_implicit_invocation`, `dependencies.tools`.
- Availability differs by plan; personal skills are on paid plans, not Free or Go.

Sources: [Build skills](https://learn.chatgpt.com/docs/build-skills),
[Skills in ChatGPT](https://help.openai.com/en/articles/20001066-skills-in-chatgpt),
[How to use skills in ChatGPT](https://www.tonyreviewsthings.com/how-to-use-skills-in-chatgpt/).

## ChatGPT Images 2.0 (`gpt-image-2`, April 2026)

- Any aspect ratio from 3:1 to 1:3, including 16:9, 9:16, 4:5, 3:4 and 1:1. Set it in
  the picker or state it in the prompt. Changing ratio recomposes; it does not crop.
- 2K output is standard in the app (4K is API beta). API constraints: edges multiples of
  16, max edge 3840, 655,360–8,294,400 pixels.
- Text rendering is reliable for short runs of exact quoted text. Still weak: precise
  layout placement and brand logos, so the skill keeps the wordmark to plain type with a
  stated hex and checks it after every render.
- Reference images are accepted at high fidelity, which is how the portrait and square
  masters are derived from the landscape one.

Sources: [Image generation guide](https://developers.openai.com/api/docs/guides/image-generation),
[ChatGPT Images 2.0 breakdown](https://www.buildfastwithai.com/blogs/chatgpt-images-2-0-gpt-image-2-2026),
[Images 2.0 explained](https://invideo.io/blog/chatgpt-images-2-0-explained/).

## Consequence for the ChatGPT skill

The Claude Code plugin forbids image-model text and generated plates because Chromium and
Pillow set the type. In ChatGPT there is no Chromium, so the skill lets the image model
set the type and moves the rigour into the prompt structure, the tells table and the
inspect step. Exact platform pixels come from a Pillow cover-fit in the Python tool.
