export const meta = {
  name: 'replication-critique',
  description: 'Attack a replication from independent angles until a round finds nothing new',
  whenToUse: 'After building or changing a replication, before claiming it is done',
  phases: [
    { title: 'Attack', detail: 'independent critics, one lens each' },
    { title: 'Verify', detail: 'each defect re-checked by a skeptic told to refute it' },
  ],
}

// The objective and the files under attack are passed in, so the same harness
// works for any replication rather than being welded to one paper.
const {
  paper = '2606.04153',
  module: modulePath = 'alpha_archive/replications/decomp2026.py',
  checklist = 'data/checklists/2606.04153v1.json',
  artifacts = 'data/artifacts/2606.04153.json',
  text = 'data/cache/2606.04153_text.txt',
  objective = 'Rebuild every procedure this paper runs and score every printed number.',
  rounds = 3,
} = args || {}

const ROOT = 'C:\\Users\\reza\\dev\\alpha-archive'

// Each critic gets one lens. Redundant critics agree with each other; critics
// looking for different failures find different failures, and a replication
// can be wrong in ways that do not overlap at all.
const LENSES = [
  {
    key: 'lookahead',
    ask: `Hunt ONLY for look-ahead bias and information leakage in ${modulePath}. ` +
      `Check: are predictors lagged before use; is any model fitted on data that ` +
      `includes the month it forecasts; does the expanding window include t; is any ` +
      `variable standardised, winsorised or de-meaned using the full sample; does the ` +
      `magnitude fitted value used by the sign equation come from a regression that ` +
      `saw the outcome. Read the code line by line. A single leaked observation ` +
      `invalidates every out-of-sample number in the file.`,
  },
  {
    key: 'spec',
    ask: `Compare ${modulePath} against what the paper actually specifies in ${text}. ` +
      `Hunt ONLY for places where the code implements something different from the ` +
      `paper: wrong variable definition, wrong transformation, wrong sample split, ` +
      `wrong benchmark, wrong loss, a model the paper describes one way and the code ` +
      `builds another. Cite the page of the paper and the line of the code for each.`,
  },
  {
    key: 'scoring',
    ask: `Hunt ONLY for dishonest scoring. Read ${artifacts} against ${checklist}. ` +
      `Check every artifact: does its 'cell' address exist in the checklist; does its ` +
      `'published' value equal what the checklist harvested; was the tolerance chosen ` +
      `before the result or widened to fit it; is any artifact scored against a value ` +
      `paraphrased from prose rather than printed in a table; does any artifact claim ` +
      `REPRODUCED with a gap larger than its tolerance; is the reported coverage ` +
      `fraction arithmetically correct. This project already shipped one artifact ` +
      `graded against a bound invented from prose. Assume there are more.`,
  },
  {
    key: 'numerics',
    ask: `Hunt ONLY for numerical and statistical defects in ${modulePath}: ` +
      `silent NaN propagation, division by near-zero, a logit that does not converge ` +
      `and returns whatever it had, clipping that changes results, an unstable matrix ` +
      `solve, a random seed that makes results irreproducible, an off-by-one in an ` +
      `index or window, annualisation applied twice or not at all, a Sharpe ratio ` +
      `mixing monthly and annual units. Run the code if that helps.`,
  },
  {
    key: 'coverage',
    ask: `Hunt ONLY for gaps between what was claimed and what was built, for ${paper}. ` +
      `Read ${checklist} for what the paper prints and ${artifacts} for what was ` +
      `checked. Report every exhibit with zero coverage, every procedure named in the ` +
      `paper that has no implementation in ${modulePath}, and any place where a ` +
      `summary, README, docstring or headline states a count that disagrees with the ` +
      `checklist. State plainly what fraction of the paper is genuinely done.`,
  },
]

const FINDINGS = {
  type: 'object',
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['title', 'file', 'why_wrong', 'evidence'],
        properties: {
          title: { type: 'string' },
          file: { type: 'string' },
          line: { type: 'integer' },
          why_wrong: { type: 'string' },
          evidence: { type: 'string', description: 'concrete: a value, a line, a page' },
          severity: { type: 'string', enum: ['fatal', 'serious', 'minor'] },
        },
      },
    },
  },
}

const VERDICT = {
  type: 'object',
  required: ['real', 'reason'],
  properties: {
    real: { type: 'boolean' },
    reason: { type: 'string' },
    fix: { type: 'string' },
  },
}

const key = (f) => `${f.file}|${f.title}`.toLowerCase().replace(/\s+/g, ' ')

const seen = new Set()
const confirmed = []
let dry = 0

for (let round = 1; round <= rounds && dry < 2; round++) {
  log(`round ${round}: ${LENSES.length} critics on ${paper}`)

  // Every critic runs, then their findings are pooled before verification, so
  // a defect found by two lenses is verified once rather than twice.
  const found = (await parallel(LENSES.map((lens) => () =>
    agent(
      `You are reviewing a scientific replication. Work in ${ROOT}.\n\n` +
      `OBJECTIVE THE WORK IS BEING HELD TO: ${objective}\n\n` +
      `${lens.ask}\n\n` +
      `Report only defects you can point at with concrete evidence. An opinion ` +
      `about style is not a defect. If you find nothing, return an empty list — ` +
      `inventing a finding to look thorough is worse than finding nothing.`,
      { label: `critic:${lens.key}`, phase: 'Attack', schema: FINDINGS },
    ),
  ))).filter(Boolean).flatMap((r) => r.findings || [])

  const fresh = found.filter((f) => !seen.has(key(f)))
  log(`round ${round}: ${found.length} raised, ${fresh.length} new`)

  if (!fresh.length) { dry++; continue }
  dry = 0
  fresh.forEach((f) => seen.add(key(f)))

  // Each finding is put to a skeptic whose job is to kill it. Survivors are
  // the ones worth a person's time.
  const judged = await parallel(fresh.map((f) => () =>
    agent(
      `Work in ${ROOT}. Another reviewer claims this is a defect:\n\n` +
      `  title: ${f.title}\n  file: ${f.file}${f.line ? `:${f.line}` : ''}\n` +
      `  claim: ${f.why_wrong}\n  evidence: ${f.evidence}\n\n` +
      `Try to REFUTE it. Open the file, check the claim against what the code ` +
      `actually does and what the paper actually says. Default to real=false ` +
      `unless the evidence holds up under your own reading. If it is real, say ` +
      `in one sentence what the fix is.`,
      { label: `verify:${f.title.slice(0, 40)}`, phase: 'Verify', schema: VERDICT },
    ).then((v) => ({ ...f, verdict: v })),
  ))

  const kept = judged.filter(Boolean).filter((j) => j.verdict?.real)
  confirmed.push(...kept)
  log(`round ${round}: ${kept.length} of ${fresh.length} survived refutation`)
}

const order = { fatal: 0, serious: 1, minor: 2 }
confirmed.sort((a, b) => (order[a.severity] ?? 9) - (order[b.severity] ?? 9))

return {
  paper,
  confirmed: confirmed.map((f) => ({
    severity: f.severity, title: f.title, file: f.file, line: f.line,
    why_wrong: f.why_wrong, evidence: f.evidence, fix: f.verdict?.fix,
  })),
  clean: confirmed.length === 0,
}
