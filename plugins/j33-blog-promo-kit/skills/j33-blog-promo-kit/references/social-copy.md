# Social copy

Write `copy.md` into the output folder with one section per channel, each in a fenced
block so it can be copied without picking up stray markdown.

Voice is J33.AI "we", the register the articles use. Direct, technical, states a position
and backs it. No exclamation marks.

## Platform limits and shapes

### X

- 280 characters, including the link (which counts as 23 whatever its length). Budget
  ~250 for prose.
- The first line is what shows in a quoted or embedded view.
- 1–2 hashtags at most. Often zero is right.
- Link at the end, on its own line.
- If the article has 4+ distinct points, offer a thread as an alternative: hook tweet,
  one tweet per point at ≤280 each, final tweet with the link. Do not pad a two-idea
  article into a seven-tweet thread.

Shape that works:

```
A client asked us to let employees query an internal Postgres database from ChatGPT.

The tempting version — hand ChatGPT a connection string, write a careful system prompt —
fails for one reason: a prompt is a suggestion, not a security control.

So we built it the other way around.

https://j33.ai/articles/<slug>
```

### LinkedIn

- 3000 character limit; the useful range is 1300–1900.
- Only the first ~210 characters show before "…see more". The hook and the reason to
  expand both have to land inside that.
- Short paragraphs, one to three lines, blank lines between. Walls of text get skipped.
- 3–5 hashtags at the very end, after a blank line. One broad (`#AI`), one specific
  (`#MCP`), one industry (`#EnterpriseAI`).
- A link in the post is fine; no "link in comments" unless the user asks.
- Never open with "I'm excited to share" or "Thrilled to announce".

Shape that works:

```
A client asked us for something that sounds simple: let authorised employees query an
internal PostgreSQL database from ChatGPT.

The tempting shortcut is to hand ChatGPT a connection string and write a careful system
prompt telling it to behave.

That fails for a reason worth stating plainly. A prompt is a suggestion, not a security
control. Anything depending on the model choosing to follow instructions will eventually
be bypassed — by a clever user, a confused model, or an instruction hiding in retrieved data.

So we built the integration the other way around. ChatGPT never sees the database. It
talks to a small custom service that sits in between, and that service decides what is
allowed.

[2–4 more lines on the substance]

Full write-up: https://j33.ai/articles/<slug>

#EnterpriseAI #MCP #AISecurity #Postgres
```

### Instagram

- 2200 character caption limit. Only the first ~125 characters show before "more".
- Line breaks survive; use them.
- Up to 30 hashtags allowed; 5–10 is the working range for a technical B2B account. Put
  them in a block after the caption, separated by a blank line.
- No clickable link in the caption. End with a pointer, "Full article at j33.ai" or
  "Link in bio", and say which.
- Instagram's audience overlaps least with the article's. Write the caption to stand
  alone for someone who never clicks.

## What makes copy read as machine-written

Cut these on sight.

**Opening formulas**: "In today's fast-paced world", "In an era where", "Let's dive in",
"Picture this", "Here's the thing", "I'm excited to share", "Ever wondered".

**Vocabulary**: delve, leverage (as a verb), robust, seamless, unlock, harness, elevate,
game-changer, revolutionise, cutting-edge, transformative, landscape, realm, tapestry,
navigate (metaphorically), testament, crucial, pivotal, moreover, furthermore.

**Negative parallelism**: "It's not just X, it's Y." "This isn't about X. It's about Y."
Once in a long piece is a choice; twice is a signature.

**Rule of three everywhere**: "faster, cheaper, and more reliable", "build, deploy, and
scale". Real lists are uneven. Vary the count.

**Em dash density**: one or two in a LinkedIn post is normal. Six is a tell. Use full
stops and commas; break the sentence.

**Superficial -ing analysis**: "highlighting the importance of", "showcasing its ability
to", "underscoring the need for", "demonstrating how". They add nothing. Delete them.

**Hollow closers**: "The future of X is here." "One thing is clear." "Only time will
tell." "What are your thoughts?" as a reflexive sign-off.

**Emoji bullets**: 🚀 ✅ 💡 🔥 as list markers. One emoji in a whole post, because it
means something, is fine. A column of them is not.

**Vague attribution**: "experts say", "studies show", "it's widely known", "many
organisations are finding". Name the source or drop the claim.

## What to do instead

Lead with the specific thing that happened. "A client asked us to let employees query an
internal Postgres database from ChatGPT" is a real opening because it is a real event.

Include a number, a constraint, or a name: eight security requirements, one functional
one; a read-only first release; Azure Container Apps.

State the position plainly and then earn it. "a prompt is a suggestion, not a security
control" works because it is a claim, stated without hedging, followed by the reasoning.

Vary sentence length. Machine prose trends toward uniform medium-length sentences. A
four-word sentence after a long one does more for readability than formatting.

Write the ending as an ending, not a call to action. "Read more here" is fine. "Let me
know your thoughts in the comments 👇" is not.

## Hashtag bank

Specific first; broad tags do little on their own.

- Broad: `#AI` `#MachineLearning` `#SoftwareEngineering` `#CloudComputing`
- Positioning: `#EnterpriseAI` `#AIEngineering` `#MLOps` `#PlatformEngineering`
- Topical: `#MCP` `#LLM` `#RAG` `#OAuth` `#AppSec` `#Postgres` `#Azure` `#Kubernetes`
- Brand: `#J33AI`

Pick tags the article earns. A post about OAuth scopes tagged `#MachineLearning` reads as
reach-chasing.

## The copy.md template

```markdown
# <Article title> — social kit

## X
> 247 / 280 characters

```
<post text>
```

## LinkedIn
> 1,482 characters · hook lands in first 198

```
<post text>
```

## Instagram
> 1,104 characters · first 118 visible

```
<caption text>

<hashtag block>
```
```

State the character count you measured, so the user can see the post will not be
truncated.
