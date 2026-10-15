# PROOF

Evidence that the gates in this repository actually work. Every claim below has a way to reproduce it, and anything not yet proven is listed at the end instead of being implied.

Repository: https://github.com/alvaroolazabal88-hub/gated-delivery

## What is being proven

A change can only reach `main` through a pull request, and only if the `test` check passes. A test that fails blocks the merge.

## 1. The tests pass, and they fail when something is wrong

`test_app.py` starts the real server on a free port, calls it over HTTP, and asserts on the status code and body.

```
$ python3 -m unittest -v
test_health_returns_ok ... ok
test_unknown_route_returns_404 ... ok

Ran 2 tests in 0.5s
OK
```

To check that a failing test really fails (and is not decoration), I changed `200` to `201` in a throwaway copy and ran it again:

```
AssertionError: 200 != 201
FAILED (failures=1)
```

The process exits with a non-zero code. That exit code is what the pipeline reads, so it is what turns a check red.

## 2. CI runs on every pull request and on every push to `main`

| When | Event | Result | Run |
|---|---|---|---|
| 2026-10-13 | `pull_request` (PR #1) | success | 38433280109 |
| 2026-10-13 | `push` to `main` after the merge | success | 38433701247 |

The check appears on the pull request as `ci/test (pull_request)`. The job installs Python 3.12 on a clean Ubuntu runner and runs `python -m unittest -v`.

Reproduce: `gh run list --limit 5`

## 3. Direct pushes to `main` are rejected

With the ruleset active, I tried to push a commit straight to `main`. GitHub refused it (2026-10-14):

```
remote: error: GH013: Repository rule violations found for refs/heads/main.
remote: - Changes must be made through a pull request.
remote: - Required status check "test" is expected.
 ! [remote rejected] main -> main (push declined due to repository rule violations)
```

Both rules are the ones configured below. The bypass list is empty, so the rule also applies to the repository owner.

Reproduce:

```bash
git switch main
git commit --allow-empty -m "Test direct push"
git push          # rejected
git reset --hard origin/main
```

## 4. The ruleset (`protect-main`, active)

Read back from the GitHub API, not from memory:

| Setting | Value |
|---|---|
| Target | default branch (`main`) |
| Enforcement | active |
| Bypass list | empty |
| Restrict deletions | on |
| Block force pushes (`non_fast_forward`) | on |
| Restrict creation | on |
| Pull request required | on, 0 required approvals |
| Required status check | `test` |
| Strict (branch must be up to date) | off |

Reproduce: `gh api repos/alvaroolazabal88-hub/gated-delivery/rulesets`

Why 0 approvals: this is a single-person repository and GitHub does not let an author approve their own pull request. Requiring one approval would lock the owner out. In a team this would be at least 1.

## 5. A failing test blocks the merge

To prove that the check is a real gate and not decoration, I opened a pull request that breaks `test_health_returns_ok` on purpose (`200` changed to `201`). It is PR #3, branch `test/break-on-purpose`, 2026-10-14.

**Locally**, the test fails and the process exits with code 1:

```
AssertionError: 200 != 201
FAILED (failures=1)
$ echo $?
1
```

**In CI**, the same failure shows up on the runner (run 38596566737, job time 6 s), and `gh pr checks` reports it as failing:

```
Some checks were not successful
0 cancelled, 1 failing, 0 successful, 0 skipped, and 0 pending checks
X  ci/test (pull_request)    6s
```

**On the pull request**, read back from the GitHub API:

| Field | Value |
|---|---|
| `statusCheckRollup` | `test`: FAILURE |
| `mergeable` | MERGEABLE (no code conflicts) |
| `mergeStateStatus` | **BLOCKED** |

The distinction matters: git could have merged the change cleanly, but the repository rule stopped it because the required check failed.

The pull request was then closed **without merging** (closed 2026-10-14, `mergedAt: null`), so the broken test never reached `main`. `main` still has `200` on that line.

Reproduce:

```bash
git switch -c test/break-on-purpose
# change 200 to 201 in test_app.py, commit, push
gh pr create --base main --title "Break test on purpose (do not merge)" --body "Proof."
gh pr checks
gh pr view --json mergeStateStatus
```

## What this does not prove (yet)

Listed so the limits are clear:

- No container image is built, so there is no Dockerfile or Compose proof yet.
- No security scanning (dependencies, image or secrets) runs in the pipeline.
- There is no manual approval step and nothing is deployed.
- Actions are referenced by version tag (`@v7`), not pinned to a commit SHA.
- Only one check is required, and the branch does not have to be up to date before merging.
- It is a one-person repository, so there is no real code review.

These are the next phases of the project.
