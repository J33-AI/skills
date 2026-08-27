# Social copy

Write `copy.md` into the output folder with one section per channel, each in a fenced
block so it can be copied without picking up stray markdown.

Voice is **J33.AI "we"** — the register the articles already use. Direct, technical,
willing to state a position and then back it. No exclamation marks.

## Platform limits and shapes

### X

- **280 characters** hard limit, including the link (which counts as 23 regardless of
  actual length). Budget ~250 for prose.
- The first line is the whole game — it is what shows before the fold in a quoted or
  embedded view.
- **1–2 hashtags maximum.** X users treat hashtag stacks as spam. Often zero is right.
- Link at the end, on its own line.
- If the article genuinely has 4+ distinct points, offer a thread as an alternative:
  hook tweet, one tweet per point at ≤280 each, final tweet with the link. Do not pad a
  two-idea article into a seven-tweet thread.

Shape that works:

```
A client asked us to let employees query an internal Postgres database from ChatGPT.

The tempting version — hand ChatGPT a connection string, write a careful system prompt —
fails for one reason: a prompt is a suggestion, not a security control.

So we built it the other way around.

https://j33.ai/articles/<slug>
```

### LinkedIn

- **3000 character** limit; the useful range is **1300–1900**. Longer posts do not get
  penalised, but attention runs out.
- Only the **first ~210 characters** show before "…see more". The hook and the reason to
  expand must both land inside that.
- Short paragraphs, one to three lines each, with blank lines between. LinkedIn renders
  walls of text badly and readers skip them.
- **3–5 hashtags**, at the very end, after a blank line. Mix one broad (`#AI`), one
  specific (`#MCP`), one industry (`#EnterpriseAI`).
- No "link in comments" games unless the user asks; a link in the post is fine and
  the reach penalty is largely folklore now.
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

- **2200 character** caption limit. Only the first **~125 characters** show before "more".
- Line breaks survive; use them.
- Up to 30 hashtags, but **5–10 is the working range** for a technical B2B account.
  Put them in a block after the caption, separated by a blank line.
- No clickable link in the caption. End with a pointer — "Full article at j33.ai" or
  "Link in bio" — and say which.
- Instagram's audience overlaps least with the article's; write the caption so it stands
  alone even for someone who never clicks.

## What makes copy read as machine-written

Cut these on sight. Each is a reliable tell.

**Opening formulas** — "In today's fast-paced world", "In an era where", "Let's dive in",
"Picture this", "Here's the thing", "I'm excited to share", "Ever wondered".

**Vocabulary** — delve, leverage (as a verb), robust, seamless, unlock, harness, elevate,
game-changer, revolutionise, cutting-edge, transformative, landscape, realm, tapestry,
navigate (metaphorically), testament, crucial, pivotal, moreover, furthermore.

**Negative parallelism** — "It's not just X, it's Y." "This isn't about X. It's about Y."
Once in a long piece is a rhetorical choice; twice is a signature.

**Rule of three everywhere** — "faster, cheaper, and more reliable", "build, deploy, and
scale". Real writing has uneven lists. Vary the count.

**Em dash density** — one or two in a LinkedIn post is normal prose. Six is a tell. Use
full stops and commas instead; break the sentence.

**Superficial -ing analysis** — "highlighting the importance of", "showcasing its ability
to", "underscoring the need for", "demonstrating how". These clauses add no information.
Delete them and the sentence improves.

**Hollow closers** — "The future of X is here." "One thing is clear." "Only time will
tell." "What are your thoughts?" as a reflexive sign-off.

**Emoji bullets** — 🚀 ✅ 💡 🔥 as list markers. One emoji in a whole post, used because
it means something, is fine. A column of them is not.

**Vague attribution** — "experts say", "studies show", "it's widely known", "many
organisations are finding". Name the source or drop the claim.

## What to do instead

Lead with the specific thing that happened. "A client asked us to let employees query an
internal Postgres database from ChatGPT" is a real opening because it is a real event.

Include a number, a constraint, or a name — eight security requirements, one functional
one; a read-only first release; Azure Container Apps. Specificity is the cheapest
credibility available.

State the position plainly and then earn it. The article's own line — "a prompt is a
suggestion, not a security control" — works because it is a claim, stated without hedging,
followed by the reasoning.

Let sentence lengths vary. Machine prose trends toward uniform medium-length sentences.
A four-word sentence after a long one does more for readability than any amount of
formatting.

Write the ending as an ending, not as a call to action. Trailing off into "Read more here"
is fine. "Let me know your thoughts in the comments 👇" is not.

## Hashtag bank

Reach for the specific ones first; broad tags are close to useless on their own.

- **Broad** — `#AI` `#MachineLearning` `#SoftwareEngineering` `#CloudComputing`
- **Positioning** — `#EnterpriseAI` `#AIEngineering` `#MLOps` `#PlatformEngineering`
- **Topical** — `#MCP` `#LLM` `#RAG` `#OAuth` `#AppSec` `#Postgres` `#Azure` `#Kubernetes`
- **Brand** — `#J33AI`

Pick tags the article actually earns. A post about OAuth scopes tagged `#MachineLearning`
reads as reach-chasing and gets treated as such.

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

Always state the character count you actually measured. It is the fastest way for the user
to trust the post will not be truncated.
