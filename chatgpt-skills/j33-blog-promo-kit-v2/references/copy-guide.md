# Social copy guide

Write from the article's substance. Each platform should express the same core point in a form native to that feed; do not paste the same paragraph three times.

## Voice

- Human, clear and professional.
- Direct opening; no throat-clearing.
- Concrete nouns and active verbs.
- Explain specialized terms briefly when the intended reader may not know them.
- Make only claims supported by the article.
- Use ordinary punctuation. Avoid em-dash chains, canned contrast formulas and fragments arranged for fake drama.
- No engagement bait, emoji chains or generic calls to “join the conversation.”

## Platform rules

### Instagram

- Hard ceiling: 2,200 characters. Editorial target: 500–1,100.
- Lead with a relatable observation or practical consequence.
- Use short paragraphs suitable for mobile.
- End with a simple invitation to read the article and the URL.
- Use 3–5 specific hashtags; avoid broad filler such as `#innovation`.

### LinkedIn

- Hard ceiling: 3,000 characters. Editorial target: 700–1,500.
- Lead with the useful professional insight, not an announcement that a blog was published.
- Add enough context for engineering or business readers to understand why it matters.
- Use 0–3 specific hashtags. Avoid motivational phrasing and sales copy.

### X

- Keep the standard post at or below 280 characters, including the raw URL and hashtags.
- State one sharp takeaway, then the link.
- Use no more than two hashtags, and omit them when the prose is stronger without them.
- Do not rely on Premium long-post limits unless the user asks for a long post.

## Machine-readable validation file

Create `post-copy.json` temporarily with this shape, run the checker, then remove it from the final deliverables folder:

```json
{
  "instagram": "Complete Instagram text",
  "linkedin": "Complete LinkedIn text",
  "x": "Complete X text"
}
```
