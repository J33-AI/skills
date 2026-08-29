# Eval cases

Agent-level cases: given an article, does Claude produce a kit that is correct, on-brand,
and honest about what went wrong?

```bash
cd plugins/j33-blog-promo-kit
claude plugin eval . --allow-tools Bash Write Edit
claude plugin eval . --case renders-a-full-kit --runs 1     # one case
```

The cases need `Bash`, `Write` and `Edit`: the skill writes a spec, runs `kit.py`, and
runs `verify.py`.

| Case | Checks |
| ---- | ------ |
| `renders-a-full-kit` | The happy path: five files at exact dimensions, real slug, `copy.md`, verifier run and clean, nothing from the banned-imagery list. |
| `artwork-comes-from-the-article` | The diagram uses the article's own labels and the code is the article's actual code. |
| `responds-to-the-verifier` | Given an unusable headline, the agent reports the bad fit instead of editing `profiles.py` to lower the floor. |

## Status

Not yet executed: `claude plugin eval` is in early access and not enabled on the account
this suite was written on. The cases follow the documented `prompt.md` + `graders/*.md`
layout, but nothing has been run or tuned against real transcripts, so expect thresholds
to need adjusting. Until then the deterministic suite is the one that counts:

```bash
python skills/j33-blog-promo-kit/tests/test_kit.py
```
