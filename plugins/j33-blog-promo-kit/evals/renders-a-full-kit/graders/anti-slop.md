# None of the house-banned imagery

The skill exists to produce images that do not read as machine-made. Judge the
spec the agent wrote and any artwork it authored.

Fail if any of these appear:

- A glowing brain, a neural-network orb, a circuit board, a humanoid robot, a
  holographic UI, a lens flare, a particle swarm, binary rain, a hexagon grid,
  a handshake, or an up-and-to-the-right arrow.
- Any attempt to render the headline, or any other lettering, with an image
  model instead of the text engine.
- More than one accent colour, or a colour that is not in the brand token list
  (`#0099CC`, `#1E3A8A`, `#0A0D33`, `#01102D`, `#94A3B8`, `#F5F5F5`, `#F6F0E2`,
  `#02080F`).
- A headline longer than about eight words, or one that names a topic
  ("Understanding Distributed Retries") instead of making a claim.

Pass if the artwork is either a diagram of the mechanism the article
describes, real code from the article, or deliberately nothing at all.
