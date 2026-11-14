export const meta = {
  name: 'okf-layer-ticket',
  description: 'Build one okf-builder ticket: pre-flight, builder PR in a worktree, two-lens review, bar classification, up to two fix rounds; or a fix round on given findings, or the review of a rebase',
  phases: [
    { title: 'Preflight', detail: 'check the ticket against the code' },
    { title: 'Build', detail: 'builder in a worktree opens a draft PR' },
    { title: 'Review', detail: 'correctness and tests lenses, fresh context' },
    { title: 'Classify', detail: 'one fresh agent rules each finding against the bar' },
    { title: 'Fix', detail: 'at most two rounds on blocking findings' },
    { title: 'Rebase', detail: 'one fresh reviewer checks a rebase changed only the conflicting files' },
  ],
}
// Carries out the runbook knowledge/base/runbooks/build-in-layers.md (step 5) and the doctrine knowledge/base/doctrine/building-with-agents.md.

const { ticket, ticketPath, commonPath, bead } = args
const READ = `Read ${commonPath} (context for every ticket) and ${ticketPath} (ticket ${ticket}, stored in bead ${bead}).`
const VERIFIED = `If the ticket names human-verified concepts it must edit, lint --strict is expected to report VERIFIED_STALE on each of them and nothing else: that warning is not a defect, and their verified field is never touched (the owner verifies them again after the merge).`
const LINT = `Run just test and just lint. ${VERIFIED} When the ticket names such concepts, just lint fails on purpose: run uv run -q plugin/okf-builder/skills/okf-standard/scripts/okf_lint.py knowledge --strict --json and paste that every finding is VERIFIED_STALE on a concept the ticket names, then run the second line of the lint recipe (the example bundle) on its own.`

const PRE = { type: 'object', properties: {
  proceed: { type: 'boolean' },
  false_premises: { type: 'array', items: { type: 'string' } },
  ambiguities: { type: 'array', items: { type: 'string' } },
  owner_decisions: { type: 'array', items: { type: 'string' } },
}, required: ['proceed', 'false_premises', 'ambiguities', 'owner_decisions'] }

const BUILD = { type: 'object', properties: {
  pr_number: { type: 'integer' }, branch: { type: 'string' },
  criteria: { type: 'array', items: { type: 'object', properties: { criterion: { type: 'string' }, proven: { type: 'boolean' }, evidence: { type: 'string' } }, required: ['criterion', 'proven', 'evidence'] } },
  unclear: { type: 'array', items: { type: 'object', properties: { point: { type: 'string' }, choice: { type: 'string' } }, required: ['point', 'choice'] } },
  stopped_reason: { type: 'string' },
}, required: ['pr_number', 'branch', 'criteria', 'unclear', 'stopped_reason'] }

const REVIEW = { type: 'object', properties: {
  head_sha: { type: 'string' },
  findings: { type: 'array', items: { type: 'object', properties: {
    severity: { type: 'string', enum: ['blocking', 'fix', 'nit'] }, file: { type: 'string' }, summary: { type: 'string' }, why_blocking_per_bar: { type: 'string' },
  }, required: ['severity', 'file', 'summary', 'why_blocking_per_bar'] } },
}, required: ['head_sha', 'findings'] }

const CLASSIFY = { type: 'object', properties: {
  rulings: { type: 'array', items: { type: 'object', properties: {
    index: { type: 'integer' }, blocking: { type: 'boolean' }, bar_item: { type: 'string' }, reason: { type: 'string' },
  }, required: ['index', 'blocking', 'bar_item', 'reason'] } },
}, required: ['rulings'] }

const REBASE = { type: 'object', properties: {
  head_sha: { type: 'string' },
  changed_files: { type: 'array', items: { type: 'string' } },
  only_conflicting: { type: 'boolean' },
  findings: { type: 'array', items: { type: 'string' } },
}, required: ['head_sha', 'changed_files', 'only_conflicting', 'findings'] }

if (args.rebase) {
  const { pr, reviewed_sha, files } = args.rebase
  phase('Rebase')
  const r = await agent(`${READ}
You are a reviewer with fresh context. PR #${pr} of jisequilla/j3r3-okf-builder was reviewed at commit ${reviewed_sha}, then rebased onto main to resolve a conflict in ${files.join(', ')}. Check that the rebase changed nothing else. In a fresh clone in the scratchpad: git fetch origin; git fetch origin ${reviewed_sha}; head = gh pr view ${pr} --json headRefOid; old base = git merge-base ${reviewed_sha} origin/main; new base = git merge-base <head> origin/main. Run git range-diff <old base>..${reviewed_sha} <new base>..<head>, and list in changed_files every file whose patch differs between the two ranges. only_conflicting is true when changed_files is a subset of the conflicting files and, in each of them, the difference only reconciles the PR's change with what main added there. Each finding names a file and what changed beyond that reconciliation. Do not edit the PR or post comments.`, { label: `rebase:${ticket}`, phase: 'Rebase', schema: REBASE })
  const clean = !!r && r.only_conflicting && r.findings.length === 0
  return { ticket, stage: 'rebase', pr, rebase: r, reviewed_sha: clean ? r.head_sha : null }
}

let pre = null
let build
if (args.fix) {
  build = { pr_number: args.fix.pr, branch: args.fix.branch }
} else {
  phase('Preflight')
  pre = await agent(`${READ}
You are the pre-flight checker. Read the ticket against the current code on origin/main in the repository at the current working directory (read only; do not edit or create anything there). Flag false premises (the ticket assumes code or text that is not there), ambiguities a builder could resolve two ways, and decisions that belong to the owner (not settled by the common context or the ADRs it names). A concept the ticket edits whose frontmatter has verified: human: and which the ticket does not name as a human-verified concept it must edit is an ambiguity. Set proceed=false only if a false premise or an owner decision would make the build wrong.`, { label: `preflight:${ticket}`, phase: 'Preflight', schema: PRE })
  if (!pre || !pre.proceed) return { ticket, stage: 'preflight', pre }

  phase('Build')
  const notes = [...pre.false_premises, ...pre.ambiguities].map(s => `- ${s}`).join('\n') || '- none'
  build = await agent(`${READ}
You are the builder. You are in an isolated git worktree of the repo. ${args.continueBranch
    ? `A previous builder was interrupted. Its partial work is the local WIP commit on branch ${args.continueBranch} (not pushed): git fetch origin; git checkout ${args.continueBranch}. Read the ticket again (it may have changed since that builder started, for example with decisions settled for the builder), review what the WIP did against it, keep what is right, fix what is not, and finish the rest. Before pushing, squash the WIP into your final commit(s) so no "WIP" commit reaches the PR (git reset --soft origin/main, then commit). Implement`
    : `Start a branch from origin/main (git fetch origin; git checkout -b ${bead.replace(/\./g, '-')} origin/main). Implement`} the ticket within its closed file list. Pre-flight notes to take into account:
${notes}
Prove each acceptance criterion by revert → red → restore where it is code, and by the stated check otherwise. ${LINT} Commit, push, and open a DRAFT PR to main with gh (gh auth switch -u jisequilla first) whose title follows Conventional Commits (feat:, fix:, docs:, refactor:, test:, build:, ci:, chore:; ! for a breaking change; DEC-0005) and whose body has: what changed, each criterion with the pasted evidence, a "Left unclear" section listing what the ticket left unclear and the reading you took (also returned in unclear; "none" when nothing was), and "Ticket: ${ticket} (bead ${bead})". If you must stop (a needed file outside the list, a criterion impossible), still push what you have, open the draft PR and explain in stopped_reason; otherwise stopped_reason is "".`, { label: `build:${ticket}`, phase: 'Build', schema: BUILD, isolation: 'worktree' })
  if (!build || !build.pr_number) return { ticket, stage: 'build', pre, build }
}

const LENSES = [
  { key: 'correctness', text: 'Lens: correctness. Does the diff do what the ticket table says, without contradicting the ADRs the ticket or the common context names, and without regressions?' },
  { key: 'tests', text: 'Lens: tests. Is each acceptance criterion really proven (would its test fail if the change were reverted)? Are the build/checks.py steps and script --test cases sound? Read the evidence pasted in the PR body; do NOT run just test in the checkout of the builder (it writes dist/ there); you may run single script --test commands from a fresh checkout of the PR branch in the scratchpad.' },
]
const review = (round) => parallel(LENSES.map(l => () => agent(`${READ}
You are a reviewer with fresh context. Review PR #${build.pr_number} of jisequilla/j3r3-okf-builder (gh pr view ${build.pr_number}; gh pr diff ${build.pr_number}). Do not read any builder report other than the PR itself. Record in head_sha the PR head commit you read (gh pr view ${build.pr_number} --json headRefOid). ${l.text} ${VERIFIED}
Label every finding against the ticket's blocking bar: "blocking" if the bar names it; "fix" for real defects outside the bar; "nit" otherwise. Another agent rules on the bar from your summaries, so write each summary to say what fails and how it shows. Do not edit the PR or post comments.`, { label: `review:${ticket}:${l.key}:r${round}`, phase: 'Review', schema: REVIEW })))

// Principle 7 of the doctrine: the bar decides, not the reviewer's label; the reviewer that wrote a label never grades it.
const classify = async (round, findings) => {
  if (!findings.length) return { blocking: [], classifier_failed: false }
  phase('Classify')
  const list = findings.map((f, i) => `${i}. [labelled ${f.severity}] ${f.file}: ${f.summary} (reviewer's reason: ${f.why_blocking_per_bar})`).join('\n')
  const c = await agent(`${READ}
You rule on review findings against the ticket's blocking bar, with fresh context. Read the bar and the acceptance criteria in the ticket; do not read the PR. For each finding below, decide whether the bar makes it blocking, whatever the reviewer's label says, in either direction: a finding labelled fix or nit that breaks an item of the bar (for example a criterion whose check would not fail on revert, when the bar names an unproven criterion) is blocking; a finding labelled blocking that no item of the bar names is not. Quote in bar_item the item of the bar it breaks, or "none". ${VERIFIED} Return one ruling per finding, by its index.
${list}`, { label: `classify:${ticket}:r${round}`, phase: 'Classify', schema: CLASSIFY })
  const ruled = new Map((c?.rulings ?? []).map(r => [r.index, r]))
  if (!c || findings.some((_, i) => !ruled.has(i))) {
    return { blocking: findings.filter(f => f.severity === 'blocking'), classifier_failed: true }
  }
  return {
    blocking: findings.flatMap((f, i) => ruled.get(i).blocking ? [{ ...f, bar_item: ruled.get(i).bar_item }] : []),
    classifier_failed: false,
  }
}

let round = 0
let reviews = []
let blocking = []
let classifier_failed = false
const history = []
if (args.fix) {
  blocking = args.fix.findings
} else {
  reviews = (await review(round)).filter(Boolean)
  const findings = reviews.flatMap(r => r.findings)
  ;({ blocking, classifier_failed } = await classify(round, findings))
  history.push({ round, findings, blocking, classifier_failed })
}
while (blocking.length && round < 2) {
  round++
  phase('Fix')
  await agent(`${READ}
You fix review findings on PR #${build.pr_number} (branch ${build.branch}). You are in an isolated worktree: git fetch origin; git checkout ${build.branch}. Fix only these blocking findings, within the ticket's file list:
${blocking.map(f => `- ${f.file}: ${f.summary} (${f.bar_item ?? f.why_blocking_per_bar})`).join('\n')}
Re-prove the affected criteria. ${LINT} Push, and append a "Fix round ${round}" section with the evidence to the PR body (gh pr edit --body-file).`, { label: `fix:${ticket}:r${round}`, phase: 'Fix', isolation: 'worktree' })
  reviews = (await review(round)).filter(Boolean)
  const findings = reviews.flatMap(r => r.findings)
  ;({ blocking, classifier_failed } = await classify(round, findings))
  history.push({ round, findings, blocking, classifier_failed })
}
const heads = [...new Set(reviews.map(r => r.head_sha))]
const reviewed_sha = heads.length === 1 ? heads[0] : null
return { ticket, pr: build.pr_number, branch: build.branch, criteria: build.criteria, unclear: build.unclear, stopped_reason: build.stopped_reason, pre, rounds: round, open_blocking: blocking, classifier_failed, reviewed_sha, sha_mismatch: heads.length > 1, history }
