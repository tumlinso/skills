# Search Boundaries

Use this reference when choosing sources or explaining confidence.

## PubMed

- Best first stop for biomedical background, mechanistic, clinical, and review-style support.
- Strongest source in this skill for claims about prevalence, mortality, disease biology, and experimental evidence.
- Can return both review-like and primary literature.

## arXiv

- Best first stop for computational methods, algorithms, benchmarks, and fast-moving technical framing.
- Use heavily when the manuscript is method-first, model-first, or benchmarking-heavy.
- Treat results as preprints unless metadata clearly indicates otherwise.

## bioRxiv

- Useful for recent life-science and computational-biology preprints.
- Official API is metadata and abstract oriented, but not a true full-archive free-text search surface.
- In this skill, bioRxiv search is implemented as a recent-window metadata scan followed by local ranking over title plus abstract text.
- Because of that limitation, lower confidence when a claim needs deep historical coverage and bioRxiv is the only source producing candidates.

## Abstract-First Rule

- The shortlist should be built from metadata plus abstracts only.
- The skill should read `shortlist.txt` first.
- Only inspect raw abstract bodies when the shortlist looks weak or ambiguous.
- Full-text reading belongs in a later, explicit step if the user asks for it.
