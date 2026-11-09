export const meta = {
  name: 'okf-layer-ticket',
  description: 'Build one okf-builder ticket: pre-flight, builder PR in a worktree, two-lens review, up to two fix rounds',
  phases: [
    { title: 'Preflight', detail: 'check the ticket against the code' },
    { title: 'Build', detail: 'builder in a worktree opens a draft PR' },
    { title: 'Review', detail: 'correctness and tests lenses, fresh context' },
    { title: 'Fix', detail: 'at most two rounds on blocking findings' },
  ],
}
// Carries out the runbook knowledge/base/runbooks/build-in-layers.md (step 5) and the doctrine knowledge/base/doctrine/building-with-agents.md.

const { ticket, ticketPath, commonPath, bead } = args
const READ = `Read ${commonPath} (context for every ticket) and ${ticketPath} (ticket ${ticket}, stored in bead ${bead}).`

const PRE = { type: 'object', properties: {
  proceed: { type: 'boolean' },
  false_premises: { type: 'array', items: { type: 'string' } },
  ambiguities: { type: 'array', items: { type: 'string' } },
  owner_decisions: { type: 'array', items: { type: 'string' } },
}, required: ['proceed', 'false_premises', 'ambiguities', 'owner_decisions'] }

const BUILD = { type: 'object', properties: {
  pr_number: { type: 'integer' }, branch: { type: 'string' },
  criteria: { type: 'array', items: { type: 'object', properties: { criterion: { type: 'string' }, proven: { type: 'boolean' }, evidence: { type: 'string' } }, required: ['criterion', 'proven', 'evidence'] } },
  stopped_reason: { type: 'string' },
}, required: ['pr_number', 'branch', 'criteria', 'stopped_reason'] }

const REVIEW = { type: 'object', properties: {
  findings: { type: 'array', items: { type: 'object', properties: {
    severity: { type: 'string', enum: ['blocking', 'fix', 'nit'] }, file: { type: 'string' }, summary: { type: 'string' }, why_blocking_per_bar: { type: 'string' },
  }, required: ['severity', 'file', 'summary', 'why_blocking_per_bar'] } },
}, required: ['findings'] }

phase('Preflight')
const pre = await agent(`${READ}
You are the pre-flight checker. Read the ticket against the current code on origin/main in the repository at the current working directory (read only; do not edit or create anything there). Flag false premises (the ticket assumes code or text that is not there), ambiguities a builder could resolve two ways, and decisions that belong to the owner (not settled by the common context or the ADRs it names). Set proceed=false only if a false premise or an owner decision would make the build wrong.`, { label: `preflight:${ticket}`, phase: 'Preflight', schema: PRE })
if (!pre || !pre.proceed) return { ticket, stage: 'preflight', pre }

phase('Build')
const notes = [...pre.false_premises, ...pre.ambiguities].map(s => `- ${s}`).join('\n') || '- none'
const build = await agent(`${READ}
You are the builder. You are in an isolated git worktree of the repo. ${args.continueBranch
  ? `A previous builder was interrupted. Its partial work is the local WIP commit on branch ${args.continueBranch} (not pushed): git fetch origin; git checkout ${args.continueBranch}. Read the ticket again (it may have changed since that builder started, for example with decisions settled for the builder), review what the WIP did against it, keep what is right, fix what is not, and finish the rest. Before pushing, squash the WIP into your final commit(s) so no "WIP" commit reaches the PR (git reset --soft origin/main, then commit). Implement`
  : `Start a branch from origin/main (git fetch origin; git checkout -b ${bead.replace(/\./g, '-')} origin/main). Implement`} the ticket within its closed file list. Pre-flight notes to take into account:
${notes}
Prove each acceptance criterion by revert → red → restore where it is code, and by the stated check otherwise. Run just test and just lint. Commit, push, and open a DRAFT PR to main with gh (gh auth switch -u jisequilla first) whose body has: what changed, each criterion with the pasted evidence, and "Ticket: ${ticket} (bead ${bead})". If you must stop (a needed file outside the list, a criterion impossible), still push what you have, open the draft PR and explain in stopped_reason; otherwise stopped_reason is "".`, { label: `build:${ticket}`, phase: 'Build', schema: BUILD, isolation: 'worktree' })
if (!build || !build.pr_number) return { ticket, stage: 'build', pre, build }

const LENSES = [
  { key: 'correctness', text: 'Lens: correctness. Does the diff do what the ticket table says, without contradicting the ADRs the ticket or the common context names, and without regressions?' },
  { key: 'tests', text: 'Lens: tests. Is each acceptance criterion really proven (would its test fail if the change were reverted)? Are the build/checks.py steps and script --test cases sound? Read the evidence pasted in the PR body; do NOT run just test in the builder's checkout (it writes dist/ there); you may run single script --test commands from a fresh checkout of the PR branch in the scratchpad.' },
]
const review = (round) => parallel(LENSES.map(l => () => agent(`${READ}
You are a reviewer with fresh context. Review PR #${build.pr_number} of jisequilla/j3r3-okf-builder (gh pr view ${build.pr_number}; gh pr diff ${build.pr_number}). Do not read any builder report other than the PR itself. ${l.text}
Classify every finding against the ticket's blocking bar: "blocking" only if the bar names it; "fix" for real defects outside the bar; "nit" otherwise. Do not edit the PR or post comments.`, { label: `review:${ticket}:${l.key}:r${round}`, phase: 'Review', schema: REVIEW })))

let round = 0
let reviews = (await review(round)).filter(Boolean)
let blocking = reviews.flatMap(r => r.findings).filter(f => f.severity === 'blocking')
const history = [{ round, findings: reviews.flatMap(r => r.findings) }]
while (blocking.length && round < 2) {
  round++
  phase('Fix')
  await agent(`${READ}
You fix review findings on PR #${build.pr_number} (branch ${build.branch}). You are in an isolated worktree: git fetch origin; git checkout ${build.branch}. Fix only these blocking findings, within the ticket's file list:
${blocking.map(f => `- ${f.file}: ${f.summary} (${f.why_blocking_per_bar})`).join('\n')}
Re-prove the affected criteria, run just test and just lint, push, and append a "Fix round ${round}" section with the evidence to the PR body (gh pr edit --body-file).`, { label: `fix:${ticket}:r${round}`, phase: 'Fix', isolation: 'worktree' })
  reviews = (await review(round)).filter(Boolean)
  blocking = reviews.flatMap(r => r.findings).filter(f => f.severity === 'blocking')
  history.push({ round, findings: reviews.flatMap(r => r.findings) })
}
return { ticket, pr: build.pr_number, branch: build.branch, criteria: build.criteria, stopped_reason: build.stopped_reason, pre, rounds: round, open_blocking: blocking, history }
