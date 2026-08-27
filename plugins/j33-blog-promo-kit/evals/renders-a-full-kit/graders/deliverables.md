# The five images and the copy, at exact sizes

Pass only if all of these hold.

1. `out/` contains exactly these five PNGs, and the two website filenames use
   the article's slug:
   - `why-we-stopped-trusting-retry-counts.png`
   - `why-we-stopped-trusting-retry-counts-card.png`
   - `instagram.png`
   - `x.png`
   - `linkedin.png`
2. Their pixel dimensions are exactly 1600x873, 1659x948, 1080x1350, 1600x900
   and 1200x1200 respectively. A file that is one pixel out is a fail — these
   are a contract with the site and the platforms, not a target.
3. `out/copy.md` exists and carries separate copy for Instagram, X and
   LinkedIn rather than one block reused three times.
4. The transcript shows the images were produced by running the skill's
   scripts (`kit.py`, or `render.py`/`compose.py`), not by any image
   generation tool.
5. `verify.py` was run against `out/` and its final report showed no
   outstanding issues. If it reported issues, the agent fixed them and re-ran
   it rather than explaining them away.

Fail if the agent produced fewer than five images, hand-waved a dimension, or
declared success without running the verifier.
