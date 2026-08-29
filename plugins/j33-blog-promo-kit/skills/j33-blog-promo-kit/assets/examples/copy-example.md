# Why ChatGPT Should Never Touch Your Database Directly — social kit

A worked example of the `copy.md` output. Written for the article in
`signal-diagram.json`. Character counts are measured, not estimated.

---

## X
> 267 / 280 characters (the link counts as 23 regardless of length)

```
A client asked us to let employees query an internal Postgres database from ChatGPT.

The tempting version is a connection string and a carefully worded system prompt. It fails for one reason: a prompt is a suggestion, not a security control.

https://j33.ai/articles/why-chatgpt-should-never-touch-your-database
```

## LinkedIn
> 1,508 characters · the claim lands inside the first 210, before the "see more" fold

```
A client asked us for something that sounds simple: let authorised employees query an internal PostgreSQL database from ChatGPT.

The tempting shortcut is to hand ChatGPT a connection string and write a careful system prompt telling it to behave.

That fails for a reason worth stating plainly. A prompt is a suggestion, not a security control. Anything that depends on the model choosing to follow instructions will eventually be bypassed, whether by a clever user, a confused model, or an instruction hiding inside retrieved data.

The functional requirement was one sentence. The security requirements were eight, and none of them can be met by prompt engineering. No database credentials in ChatGPT. Sign-in with existing Microsoft accounts. Locked to the organisation's Entra tenant. Read-only for the first release. Every token validated server-side. The database stays on a private network.

So we built the integration the other way around. ChatGPT never sees the database. It talks to a small custom MCP server that sits in between, and that server decides what is allowed: which tools exist, which queries pass, which rows come back.

The boundary is the product. Everything else is detail.

Part 1 of three. This one covers the architecture and why the shortcut fails. Part 2 covers the two Entra app registrations. Part 3 covers hosting it on Azure Container Apps.

https://j33.ai/articles/why-chatgpt-should-never-touch-your-database

#EnterpriseAI #MCP #AISecurity #Postgres #AzureContainerApps
```

## Instagram
> 900 characters · first 125 visible before "more"

```
A client wanted employees to query an internal Postgres database from ChatGPT. The shortcut is a connection string and a well-written system prompt.

It does not work, and the reason is worth saying plainly: a prompt is a suggestion, not a security control. Anything that depends on a model choosing to follow instructions gets bypassed eventually — by a clever user, a confused model, or an instruction hidden in retrieved data.

So we built it backwards. ChatGPT never sees the database at all. It talks to a small service in between, and that service decides which tools exist, which queries pass, and which rows come back.

Eight security requirements. One functional one. The boundary is the whole design.

Part 1 of three, on the architecture and why the shortcut fails.

Full article at j33.ai — link in bio.

#EnterpriseAI #MCP #AISecurity #Postgres #SoftwareEngineering #AIEngineering #J33AI
```

---

## Why this passes the anti-slop checklist

Worth reading alongside `references/social-copy.md`, because the reasons are the
transferable part:

- **Opens on a real event**, not a trend statement. "A client asked us for something
  that sounds simple" is a thing that happened.
- **The claim is stated flat and then earned.** "A prompt is a suggestion, not a
  security control" is the article's own line, and the paragraph after it does the work.
- **Specifics carry the credibility** — eight requirements against one, read-only first
  release, Entra tenant, Azure Container Apps. Named things, not "robust enterprise-grade
  security".
- **Sentence length varies.** "The boundary is the product. Everything else is detail."
  lands because the paragraph before it was long.
- **One em dash per post**, not six. **No** "delve", "leverage", "seamless", "unlock".
- **No reflexive CTA.** It ends by telling you where the article is, which is the honest
  reason the post exists.
- The three-part structure at the end is stated because the series genuinely has three
  parts, not to hit a rule of three.
