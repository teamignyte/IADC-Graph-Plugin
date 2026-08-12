---
name: setup
description: Configure the `iadc` graph MCP connection for this repo — collect the graph URL and API key and write the `iadc` entry into `.mcp.json`, merging rather than overwriting. Use when: the `iadc` MCP entry is missing, placeholder, or — unless this session already wrote it — its tools aren't responding this session (expected until the next session starts, not a reason to reconfigure); another IADC setup skill (`iadc-advisor:setup`, `iadc-tester:setup`) hands off here; the user asks directly. Runs a git-safety sequence before any write. Skips itself when a working, protected entry already exists. Works with neither other IADC plugin installed. Run once per repo.
---

# Setup

`iadc-advisor` and `iadc-tester` both reach the graph over one MCP server, `iadc`, configured in the
client repo's `.mcp.json` (repo root) — a URL plus an `appian-api-key` header. Writing that entry
means writing a **credential**, which is why it lives here instead of in either product: `iadc-graph`
is the one plugin both already depend on, so this is the one place in the family the sequence below
needs to exist. Nothing here reads anything `iadc-advisor` or `iadc-tester` write, and nothing here
assumes either is installed — this works whether either, both, or neither is present.

This is prompt-driven, not a script: explore, show the user what you found, get their word before
any git change or credential write, then write. **Never print a credential value back into the
transcript.** Report `.mcp.json`'s *shape* — server names, key names, `••••` where a secret sits —
from the first time you read the file through the last time you show it, in every step below.

**Every gate below tests what git actually did, not what the user said or what a looser check
implies.** `git check-ignore` alone, for instance, goes green the instant an untracking is merely
*staged* — before it's committed — because it already accounts for the index, not for whether HEAD
still carries the file. Where that distinction matters, the steps below say which command settles it
and why the other one doesn't.

## Process

### 1. Check whether this repo already needs anything from you

Read `.mcp.json` at the repo root if it exists (redacted, per the rule above; if it exists but
doesn't parse, treat that the same as "nothing confirmed yet" here — step 4 handles a malformed file
explicitly when it's actually time to write). Look at the `iadc` entry, if there is one:

- **No file, no `iadc` key, or its `url` / `headers.appian-api-key` are still `<placeholder>` text**
  — nothing usable yet. Continue to step 2.
- **Both values look literal** — check whether tools named `mcp__iadc__*` (e.g. `mcp__iadc__seed`)
  are available to you in this session — directly listed, or discoverable if your environment defers
  tool schemas. Claude Code connects the servers named in `.mcp.json` when a session starts, so their
  presence means this entry was already live at the start of *this* session:
  - **Absent** → on record, but not confirmed from here, and that is genuinely ambiguous rather than
    a "no": the entry could be wrong, or it could just be a value nothing has loaded yet, because a
    `.mcp.json` edit only takes effect on the *next* session — a value written five minutes ago in
    this same session would look identical to a wrong one from this vantage point. **If this same
    session already wrote this entry (step 4's write ran and its read-back confirmed the `iadc`
    block), that already is the explanation — say so and stop, rather than presenting it as
    ambiguous:** the entry is configured and will go live next session. **A prior run this session
    that reached this branch without writing doesn't qualify — a decline, a gate failure, or
    choosing to leave the entry standing all leave the ambiguity exactly as genuine as a first
    visit, and that run's values-still-needed report still stands.** Otherwise, say both readings
    plainly and ask: enter fresh values now (treat as unconfigured — continue to step 2), or leave
    it standing and check again after restarting? On "leave it," stop without writing anything.
  - **Present** → before calling this "working," check `git ls-files --error-unmatch .mcp.json`
    (repo root) — a connection succeeding is not the same question as a credential being safe:
    - **Untracked** → not being in the index only means nothing has staged it — it says nothing about
      whether the next broad `git add -A` would leave it alone. Settle it with the same three checks
      step 4 runs right before it writes anything — a credential already sitting in the file deserves
      the same durable protection as one about to be written, and none alone is sufficient:
      - `git check-ignore .mcp.json` **fails** → nothing in `.gitignore` reaches this file yet. Say
        the entry works, but say just as plainly that this repo does not protect it, and name the fix
        outright:
        ```
        # iadc-graph credential — the iadc MCP entry in .mcp.json, never committed
        .mcp.json
        ```
        added to `.gitignore` and committed. **Report this and stop — don't add the line yourself and
        don't ask whether to.** This branch exists so a working entry is never re-interrogated;
        offering to fix it here would reopen exactly that.
      - `git check-ignore .mcp.json` succeeds but step 4's second gate — the same four-part check,
        run here early — does not: `git check-ignore -- .mcp.json 2>/dev/null && git check-ignore -v
        -- .mcp.json 2>/dev/null | grep -q '^\.gitignore:' && git cat-file -e HEAD:.gitignore
        2>/dev/null && git diff --quiet HEAD -- .gitignore 2>/dev/null && git ls-files -v .gitignore
        2>/dev/null | grep -q '^H '`. Something is ignoring it right now, but not durably, and this
        check can't tell you which of four reasons without looking: the match may not trace to the
        tracked `.gitignore` at all — `.git/info/exclude` and `core.excludesFile` can make plain
        `check-ignore` succeed too, and neither one travels with a clone or a coworker; a rule that
        traces to `.gitignore` may be a later line negating it back out (`-v` alone still reports
        that line as a source and exits 0, which is why the plain, non-`-v` exit code has to agree
        first); it may trace to a real, non-negated `.gitignore` rule but not yet the copy at HEAD;
        or `.gitignore` itself may be flagged `--skip-worktree` or `--assume-unchanged`, which stops
        git from comparing it to the working tree at all — whether the committed rule is real,
        current, and non-negated is exactly what that flag makes unknowable, not something this
        check can assume in its favor: the working copy could carry a rule the committed one lacks
        (or lack one the committed copy carries) and the diff check just above would never see either
        divergence (`git ls-files -v .gitignore` reporting anything other than `H` is what catches
        that). Either way this repo does not yet durably protect it.
        Say the entry works, and that it needs a committed, non-negated `.gitignore` rule, actually
        compared against the working tree, before it's durable. **Report this and stop, same as
        above** — no commit, no asking.
      - `git check-ignore .mcp.json` succeeds and the durability check above exits 0, but
        `git cat-file -e HEAD:.mcp.json` also succeeds → the ignore rule is real and durable, but HEAD
        still carries a committed blob at this path — the state a prior run of this same skill that got
        interrupted between untracking and committing leaves behind (step 4's third gate below exists
        for exactly this). The key is still readable from this repo's history, and a plain `git reset`
        would put the file straight back in the index with nothing in `.gitignore` reaching it. Say the
        entry works, but say just as plainly that this repo does not protect it, and name the fix
        outright: the removal from the index is already staged — it only needs one more commit to
        become durable, the same commit step 4's own third gate also requires.
        **Report this and stop, same as above** — no commit, no asking.
      - **All three gates pass** → genuinely working **and** protected. Say so — name the `url`,
        redact the key — and stop. Nothing else in this skill needs to run.
    - **Tracked** → **don't report this as working.** The key is committed into this repo's git
      history, and untracking the file later doesn't erase that — anyone with the repo's history can
      still read the old commit. Say so, then continue to step 2 exactly as the unconfigured case
      would: step 3's tracked-file handling is what gets *this* file untracked, and step 4 is where
      you'll ask whether to keep the value that's already there (it does work) or replace it outright
      — worth raising given the history point above. Don't skip ahead on the assumption nothing needs
      asking.

This tool-presence check is the only evidence this skill gathers for "working" — but it settles the
one question that actually matters here: whether this specific credential is accepted by the graph
service, not whether every later operation will succeed. Every read tool needs a `session_id`, which
only exists after `seed()`, so this skill never calls one just to check a connection — and it never
collects an application to call one against anyway (see the standalone note above). Tool presence is
enough on its own, though: the graph service gates its entire MCP endpoint behind this exact key
before any MCP handshake completes, and does so fail-closed — a missing or wrong key can't match by
accident. So `mcp__iadc__*` tools being present doesn't just mean the transport connected; it means
this credential specifically was checked and accepted. What it doesn't prove: that a later `seed()`
or graph operation will succeed — those depend on things this check never touches (an application to
point at, whether Appian/LCP itself is reachable) — only that this credential is the right one.

### 2. Establish the ignore rule — before anything is written

Check whether `.gitignore` itself — not `.git/info/exclude`, not `core.excludesFile` — already
carries a rule that actually covers this path. Those other two can make `check-ignore` report
"ignored" exactly the way a `.gitignore` rule does, but neither one ever leaves this machine, so
neither protects a clone or a coworker; a rule that lives only there is, for this purpose, exactly as
absent as no rule at all. `git check-ignore --no-index -- .mcp.json 2>/dev/null && git check-ignore
-v --no-index -- .mcp.json 2>/dev/null`, piped through a check that the reported source starts with
`.gitignore:`. Both halves matter: `-v` alone exits 0 and reports a source even for a rule a *later*
line in the same file negates back out (`*.json` then `!.mcp.json` is genuinely not ignored, but
`-v` still prints `.gitignore:2:!.mcp.json`), so the plain, non-`-v` exit code is what confirms the
path is actually ignored before the source-pin asks by what. `--no-index` on both halves, not plain
`check-ignore` — plain `check-ignore` reports "not ignored" for a path that's currently tracked (or
merely staged) even when a rule that covers it is sitting right there in `.gitignore` (`.mcp.json`
may still be tracked here; step 3 is what untracks it); leaving `--no-index` off either half
reintroduces that same blind spot for that half.

- **Both succeed, and the source is `.gitignore`** — a rule already covers it there, exact line or
  broader pattern alike; nothing to append. Continue below to the durability check.
- **Anything else** — not ignored at all, ignored but negated back out by a later `.gitignore` line,
  or ignored only via a match sourced from `.git/info/exclude` or `core.excludesFile` — `.gitignore`
  itself doesn't actually cover this path, durably or not, no matter what
  `check-ignore` alone just said. Show the user the line and get an explicit yes before adding it:

  ```
  # iadc-graph credential — the iadc MCP entry in .mcp.json, never committed
  .mcp.json
  ```

  Create `.gitignore` if it doesn't exist yet. **On decline, add nothing, and don't ask again this
  run** — remember it: step 4 writes no credential value below. Leave any `<placeholder>` exactly as
  it is, don't add an `iadc` block if there isn't one already, and hand the two values off instead of
  putting them in the file.

**Either way — whether a line was just added or `.gitignore` already covered it — confirm that
coverage is actually committed, not just present in the working tree or the index, and that git can
actually see it there:** `git cat-file -e HEAD:.gitignore 2>/dev/null && git diff --quiet HEAD --
.gitignore 2>/dev/null && git ls-files -v .gitignore 2>/dev/null | grep -q '^H '`. The first part catches a
`.gitignore` that exists only in the working tree — brand new, or just added this run — where the
second part alone would read clean by default: a diff against a HEAD that has no such file to
differ from reports no difference, which is not the same thing as "durable." The second part catches
one that exists at HEAD too but disagrees with the working tree. **Neither part sees a `.gitignore`
flagged `--skip-worktree` or `--assume-unchanged`** — either flag tells git to stop comparing the
working tree to the index for this one file, so the second part reports no difference even when the
working copy carries a rule the committed copy at HEAD lacks; the third part is what catches that,
since `git ls-files -v` is the one place either flag is actually visible (`H` = plain cached entry,
`S` = skip-worktree, lowercase `h` = assume-unchanged — `git diff` has no flag of its own to see past
either one). Any part failing means a `git stash`, `git checkout -- .gitignore`, a flag left set from
an earlier session, or similar, could leave this file not actually covering `.mcp.json`, or covering
it in a way git itself cannot currently verify.

- **All three succeed** — continue to step 3.
- **The first two succeed but the third fails** — `.gitignore` itself is flagged `--skip-worktree`
  or `--assume-unchanged`, and that flag is exactly what makes "is the rule real, committed, and
  current" unanswerable: the first two parts reporting clean here proves nothing, because the flag
  is what stops git from ever reporting anything else for this file. Tell the user plainly that this
  repo does not yet durably protect the credential, and that this check cannot say whether it ever
  did. Offer `git update-index --no-skip-worktree .gitignore` (or `--no-assume-unchanged`, matching
  whichever flag `ls-files -v` reported), run only on an explicit yes, then re-run this check —
  clearing the flag doesn't establish coverage by itself, it only lets the check run truthfully
  again. Either flag exists specifically to hide a personal working-tree edit from git, so clearing
  it may surface an edit the user meant to keep local — say so before running it.
  - **Decline** — write no credential this run either, for the same not-yet-durable reason. Name
    the values still needed.
- **Either of the first two fails** — stage and commit just that file: `git add .gitignore`, then
  `git commit -m "Ignore .mcp.json — iadc-graph:setup" -- .gitignore` (this sequence is safe whether
  `.gitignore` already existed or is brand new, and never touches any other file's staged state,
  since it only ever adds and commits that one path). Show the pending change first, run only on an
  explicit yes.
  - **They'd rather commit it themselves** — write no credential this run either, for the same
    not-yet-durable reason. Name the values still needed.

(If these commands fail because this repo has no `.git` yet, say so and stop there. The checks below
have nothing to run against, and writing a credential with no safety net in place is the one thing
this skill won't do.)

### 3. Handle a tracked `.mcp.json`

Before writing anything to the file itself: `git ls-files --error-unmatch .mcp.json` (repo root).

- **Fails** (untracked, or the file doesn't exist yet) — continue to step 4.
- **Succeeds** (something is in the index at this path) — figure out which of two situations this
  is, since they need different explanations: `git cat-file -e HEAD:.mcp.json`.

  - **Succeeds (HEAD carries a committed blob)** — the ordinary case: someone committed this
    deliberately at some point. Say so, propose `git rm --cached .mcp.json`. Make **no** git change
    without an explicit yes.
    - **Decline** → this step ends here. Write **no** credential — leave any `<placeholder>` exactly
      as it is, and don't add an `iadc` block at all if there isn't one already. Tell the user the two
      values this entry still needs (`url`, `appian-api-key`) and that they need to live somewhere
      outside this repo until it's untracked. Stop; there is nothing else for this skill to do this
      run.
    - **Accept** → run it. `git rm --cached` touches only the **index** — HEAD is untouched — so
      re-confirm: `git cat-file -e HEAD:.mcp.json` (still succeeds; expected, and exactly the gap that
      matters). This is **not yet durable**: `git reset`, `git restore --staged .mcp.json`, or `git
      stash` would each put the index straight back in sync with HEAD — tracked again, where no
      `.gitignore` line reaches it and the next broad `git add` would stage the credential about to be
      written. **Don't treat `git check-ignore` succeeding here as clearance** — it goes green the
      moment the index changes, staged or committed, so it cannot tell these two states apart; only
      HEAD moving does. So this has to be **committed before anything is written**. Show `git status`
      so the pending deletion is visible. Before offering to commit, check what else is currently
      staged (`git diff --cached --name-only`):
      - **Nothing else** — offer a plain `git commit -m "Stop tracking .mcp.json —
        iadc-graph:setup"`. Run only on yes.
      - **Something else is staged too** — name it, and ask plainly: commit everything staged
        together now (only on an explicit yes naming what's included), or hold off?
      - **They commit now** → re-confirm `git cat-file -e HEAD:.mcp.json` now fails — verify the
        effect, not the attempt — then continue to step 4.
      - **They'd rather commit it themselves, or decline bundling unrelated staged work** → write
        **no** credential this run. Leave the placeholders standing, name the values still needed, and
        repeat the pending commit in your final report so it isn't the one thing forgotten.

  - **Fails (HEAD does not carry it)** — this path is staged but was **never committed**: there is no
    git history to untangle, but it still needs to come out of the index before anything can be
    safely ignored (a staged-only add is enough on its own to make `check-ignore` report "not
    ignored"). Say so plainly — don't reuse the "someone committed this deliberately" framing above;
    it would be false here. Propose the same `git rm --cached .mcp.json`, explicit yes required.
    - **Decline** → same as the decline branch above: no credential, placeholders left alone, name
      what's needed, stop.
    - **Accept** → run it. Nothing further is needed for this file specifically — there is no pending
      deletion to commit (confirm, don't assume: `git diff --cached --name-only` shows nothing for
      this path, and `git cat-file -e HEAD:.mcp.json` still fails). Continue directly to the gate
      below.

Once `.mcp.json` is confirmed untracked — either branch above, or step 3 was never entered because it
was untracked already — one gate remains: `git check-ignore .mcp.json`.

- **Succeeds** — continue to step 4.
- **Fails** — step 2's rule either isn't there, isn't sourced from `.gitignore`, or isn't committed
  yet. Offer to settle step 2 now (this is the first ask since the file became untracked, not a
  re-nag of an earlier decline): on yes, go run step 2's whole sequence — append if missing, then
  confirm it's committed — and once that succeeds, come back here and treat this gate as passed; the
  destination is step 4, nothing vaguer than that. On a second decline: stop, write no credential,
  say what's still needed.

### 4. Collect the values and write

First, the file itself has to be usable. `.mcp.json` at the repo root:

- **Doesn't exist** — fine, there's nothing to merge into; the other two triage bullets below don't
  apply, so move on to the gates that follow this list — not straight to writing.
- **Exists, parses as JSON, and `mcpServers` is an object, or is simply absent** — usable; continue.
  An absent `mcpServers` isn't a problem to solve, just a key to create holding `iadc` alone.
- **Exists but doesn't parse, or parses to something where `mcpServers` isn't an object** — **stop.
  Write nothing.** Show the user the exact problem — the parse error, or which part of the shape is
  wrong — and let them choose: fix it and re-run this skill, or describe what the file should hold so
  you can rebuild it with their explicit confirmation before anything is written. Guessing a repair
  risks silently discarding whatever they had reason to put there.

**Three gates, all required, right before anything literal goes in — they test different things and
none alone is sufficient:**

- `git check-ignore .mcp.json` succeeds. Bare here, unlike step 2's `--no-index` — by this point
  step 3 has already confirmed `.mcp.json` untracked, so the tracked-file blind spot `--no-index`
  guards against there cannot apply here. Catches a step-2 decline on a repo where step 3 found no
  tracked file to react to (so nothing upstream already stopped this run). If it fails, write no
  credential and point back at the missing rule.
- **All four of the following hold.** Gate 1 only answers "is it ignored right now," which
  `.git/info/exclude` and `core.excludesFile` can satisfy exactly as well as `.gitignore` can, and
  neither of those two ever leaves this machine's `.git` directory or this user's global config; this
  gate answers the question that actually matters before a credential gets written — would a fresh
  clone of this repo ignore it too:
  - `git check-ignore -- .mcp.json 2>/dev/null && git check-ignore -v -- .mcp.json 2>/dev/null |
    grep -q '^\.gitignore:'` — the path is actually ignored, not just matched by a rule a later
    line negates back out (`-v` alone reports a source and exits 0 even then — gate 1 already
    covers the plain half, but this part can't lean on that and stay correct on its own), **and**
    the match traces to the tracked `.gitignore`, not `.git/info/exclude` or `core.excludesFile`.
  - `git cat-file -e HEAD:.gitignore 2>/dev/null` — that file exists at HEAD, not only on disk right
    now. Without this, a brand-new or freshly-created `.gitignore` that's never been `git add`ed
    passes the next check vacuously: a diff against a HEAD that has no such file to differ from
    reports no difference.
  - `git diff --quiet HEAD -- .gitignore 2>/dev/null` — and the copy at HEAD is the one gate 1 just
    read from, not a working-tree or staged edit HEAD doesn't carry yet.
  - `git ls-files -v .gitignore 2>/dev/null | grep -q '^H '` — and git is actually comparing that
    committed copy to the working tree, not skipping the comparison entirely. `git update-index
    --skip-worktree .gitignore` or `--assume-unchanged .gitignore` — the standard idiom for keeping a personal
    ignore line out of a shared file — makes git treat HEAD's copy as authoritative and stop looking
    at the working tree for this one file, so the bullet above reports **no** difference even when
    the working copy carries a `.mcp.json` rule the committed copy at HEAD lacks. `ls-files -v` is
    the one place either flag is actually visible: `H` marks a plain cached entry, `S` marks
    skip-worktree, lowercase `h` marks assume-unchanged — `git diff` has no flag of its own to see
    past either one, which is why the bullet above cannot catch this case by itself. This doesn't
    replace that bullet: an ordinary edited-but-uncommitted `.gitignore` carrying neither flag is
    still caught there, not here.

  This is step 2's own three checks, combined into one here because step 4 can't assume step 2
  already ran in this session — a repo can pass step 2 and lose the protection again before step 4
  runs (a `git stash`, a `git checkout -- .gitignore`, a flag re-applied, another commit landing in
  between), and this four-part check is what actually stands behind "write no credential" rather
  than that sentence alone. If any part fails, don't write — offer to settle it the way step 2 does
  (stage and commit just `.gitignore`, or clear the flag `ls-files -v` names, only on an explicit
  yes), and if that's declined too, stop for this run.
- `git cat-file -e HEAD:.mcp.json` **fails.** This is the one it's tempting to skip, because step 3
  usually already ensures it — but "usually" is the gap: a *prior*
  run of this same skill that got interrupted between untracking and committing leaves the file out
  of the index already, so step 3's own opening check (`ls-files`) sees nothing to react to and falls
  straight through here, while HEAD still carries the file. If this gate fails, don't write — say so,
  show `git status`, and offer to commit the removal now (checking first whether anything else is
  staged, exactly as step 3's commit offer does) before trying again. Skipping this because step 3
  "already handled it" is exactly the mistake this gate exists to catch.

Now ask the user for the graph URL and the API key — unless step 1 already found a literal,
connectable value on file (the tracked-but-working case), in which case say what's already there and
ask whether to keep it or replace it: a value that was ever committed can still be read from this
repo's history even after this run untracks the file, so replacing it is worth raising even though
it isn't required. See [mcp-entry-template.json](./mcp-entry-template.json) for the exact shape to
fill in, including the default port and scheme. Fill in **literal values, not `${VAR}`** — the
Windows Desktop app doesn't reliably expand `${VAR}` in `.mcp.json`. Drop the template's `_comment`
keys; they're notes to you, never configuration, and must not appear in the file you write.

- **`.mcp.json` doesn't exist** — write a new file holding just `{"mcpServers": {"iadc": {...}}}`.
- **`.mcp.json` exists, no `mcpServers` key yet** — add one, holding just `iadc`.
- **`.mcp.json` exists with a `mcpServers` object** — **merge**: add or update only
  `mcpServers.iadc`. Every other key, at the top level and inside `mcpServers`, is untouched — not
  just in content but in formatting and order, so edit the `iadc` block in place (or insert it)
  rather than parsing the whole file and reserializing it, which would restyle everything else along
  with it. Show the user the diff — redacted — before writing.

**After writing, read the file back and confirm it still parses as JSON, with the `iadc` block
holding what you just wrote.** An in-place text edit into hand-formatted JSON is exactly the kind of
change a stray comma slips into unnoticed, and a broken `.mcp.json` fails every server it lists —
`appian`, `context7`, `iadc` alike — not just this one. If it doesn't parse, say so immediately
rather than reporting success, and show what's wrong.

### 5. Report

Say plainly, for this run:

- The `.mcp.json` entry as it now stands — redacted — or that it was deliberately left untouched, and
  exactly which values are still needed and why (declined ignore rule, tracked file, malformed JSON).
- Any `.gitignore` line or `.mcp.json` untracking still only **staged or otherwise uncommitted** —
  repeat this even if an earlier step already said it, so it isn't the one thing missed between
  steps.
- If a fresh value was written this run: it won't show as connected in *this* session — `.mcp.json`
  is read when a session starts, not while one is already running. Start a new session in this repo
  to pick it up; running `/iadc-graph:setup` again at that point reports it as already working
  (step 1) instead of asking again.
