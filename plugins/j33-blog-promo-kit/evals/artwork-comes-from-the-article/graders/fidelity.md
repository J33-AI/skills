# The artwork is this article's, not a generic one

The article's mechanism is a retry counter that lives in the worker process
instead of in Redis, so a job that kills the worker retries forever without
ever registering a failure.

Pass only if the artwork the agent produced is drawn from that. Concretely,
at least one of:

- An SVG diagram whose labels are the article's own nouns — worker, Redis,
  the queue, the vendor API, `attempts`, `HINCRBY`. A diagram showing the
  counter's location, or the loop that never terminates, is the ideal answer.
- The article's actual Python snippet, reproduced accurately, with the line
  carrying the bug (`job["attempts"] += 1`) highlighted.

Fail if the artwork is decorative, uses invented component names the article
never mentions (an "AI Gateway", a "Data Layer"), reproduces code that is not
in the article, or is generic enough that it would suit any post about
queues.

Also fail if the agent silently dropped the artwork on a canvas without
saying so — deciding not to draw is allowed, but it has to be a stated
decision.
