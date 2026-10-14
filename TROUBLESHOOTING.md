# TROUBLESHOOTING

Problems hit while building this project, what caused them, and how each was fixed. Each entry follows the same shape: symptom, cause, fix, and what to check first next time.

## 1. `docker: command not found` after installing Docker Desktop

**Symptom:** `docker run --rm hello-world` returned `zsh: command not found: docker`, even though the app was installed and running.

**Cause:** the `docker` binary lives inside the app bundle, and the link into `/usr/local/bin` was not created.

**Fix:**

```bash
sudo ln -sf /Applications/Docker.app/Contents/Resources/bin/docker /usr/local/bin/docker
```

**Check first next time:** `ls /Applications/Docker.app/Contents/Resources/bin` to see the binaries exist, then `echo $PATH`.

## 2. `error getting credentials ... docker-credential-desktop not found`

**Symptom:** after fixing the first problem, pulling an image failed with `exec: "docker-credential-desktop": executable file not found in $PATH`.

**Cause:** Docker reads the credential helper named in its config, and that helper had no link in the PATH either. Part of the confusion was a typo: I had run `docker run hello`, an image that does not exist, instead of `hello-world`.

**Fix:** link the helpers.

```bash
sudo ln -sf /Applications/Docker.app/Contents/Resources/bin/docker-credential-desktop /usr/local/bin/docker-credential-desktop
sudo ln -sf /Applications/Docker.app/Contents/Resources/bin/docker-credential-osxkeychain /usr/local/bin/docker-credential-osxkeychain
```

**Lesson:** when two errors appear in a row, read the real one. The first message ("Unable to find image 'hello:latest'") was a red herring.

## 3. `Permission denied (publickey)` on `gh repo create --push`

**Symptom:** the repository was created on GitHub, but the push failed with `git@github.com: Permission denied (publickey)`.

**Cause:** `gh` was configured to use SSH (`Git operations protocol: ssh`), so it added the remote as `git@github.com:...`. No SSH key was registered with GitHub for this machine.

**Fix:** switch the remote to HTTPS, which authenticates through `gh`:

```bash
git remote set-url origin https://github.com/alvaroolazabal88-hub/gated-delivery.git
git push -u origin main
```

**Permanent options:** `gh config set git_protocol https`, or register a dedicated SSH key for GitHub.

## 4. The terminal "froze" when running the app

**Symptom:** `python3 app.py` printed nothing and never returned to the prompt.

**Cause:** not a freeze. `serve_forever()` keeps the process running to answer requests, so the terminal is occupied on purpose.

**Fix:** leave it running, open a second terminal and call it with `curl -i localhost:8000/health`. Stop it with `Ctrl+C` in the first one.

## 5. `ResourceWarning: Implicitly cleaning up <HTTPError 404>`

**Symptom:** the 404 test passed but printed a `ResourceWarning`.

**Cause:** `urllib` raises `HTTPError` for a 404, and that exception holds an open response that nobody closed.

**Fix:** close it before asserting.

```python
ctx.exception.close()
self.assertEqual(ctx.exception.code, 404)
```

**How I checked:** `python3 -W error::ResourceWarning -m unittest` turns the warning into a failure, so it cannot come back silently.

**Known weakness:** the tests call `urlopen` without a `timeout`. If the server ever hangs, a CI job would wait instead of failing. Adding `timeout=5` is on the list.

## 6. `nothing to commit, working tree clean` when testing the gate

**Symptom:** `git commit -m "Test direct push"` did nothing.

**Cause:** a commit needs changes to record, and there were none.

**Fix:** `git commit --allow-empty -m "Test direct push"` creates a commit with no file changes, which is enough to test whether a push is allowed.

## 7. Workflow YAML that parses but does not do what it says

**Symptom:** a first draft of `ci.yml` looked fine to the eye.

**Cause, found by parsing it** (PyYAML was not installed, so I used Ruby: `ruby -ryaml -e 'p YAML.load_file(".github/workflows/ci.yml")'`):

- `contents:read` with no space after the colon is read as the string `"contents:read"`, not as a key and a value, so `permissions` was invalid.
- A step with only `name:` and no `uses:` or `run:` does nothing.

**Fix:** a space after every colon, and every step gets either `uses` or `run`. Inside a step, `uses` and `with` line up with `name`, not with the dash.

**Lesson:** parse a workflow before pushing it. A linter such as `actionlint` is the next improvement.

## 8. Action versions I suggested were out of date

**Symptom:** the draft used `actions/checkout@v4` and `actions/setup-python@v5`.

**Cause:** those versions came from memory. Checking the releases and the `action.yml` of each tag showed the current ones are `v7`, and that older versions run on older Node runtimes:

| Action version | Runtime |
|---|---|
| `checkout` v3 | node16 |
| `checkout` v4 | node20 |
| `checkout` v5 to v7 | node24 |

**Fix:** use the current major version, and plan to pin to a commit SHA, because a tag can be moved.

```bash
gh api repos/actions/checkout/releases --jq '.[0:3] | .[].tag_name'
```

**Lesson:** do not trust a version number from memory. Look it up.

## 9. Push rejected: `without workflow scope`

**Symptom:**

```
remote rejected ... refusing to allow an OAuth App to create or update workflow `.github/workflows/ci.yml` without `workflow` scope
```

**Cause:** the `gh` token did not have the `workflow` scope. GitHub treats editing a pipeline as a privileged action, because a workflow runs with the repository's secrets and permissions.

**Fix:**

```bash
gh auth refresh -h github.com -s workflow
gh auth status        # `workflow` now listed under Token scopes
git push -u origin ci/add-test-workflow
```

The commit did not need to be redone, only the push.

## 10. `no upstream branch` on the first push of a new branch

**Symptom:** a plain `git push` from a new branch fails.

**Cause:** the local branch has no remote counterpart yet, and git does not guess the name. `main` worked because it was linked on the first push.

**Fix:** `git push -u origin <branch>`. `-u` records the link, so later `git push` works without arguments.

## 11. The workflow did not run after pushing the branch

**Symptom:** the branch was on GitHub but no run appeared.

**Cause:** the workflow triggers on `pull_request` and on pushes to `main`, not on pushes to other branches.

**Fix:** open a pull request. Verify with `gh pr checks` and `gh run list`.

## 12. Command typos

`gh pt create`, `git tatus`, `git --push`. Both tools print the likely command (`Did you mean this? pr`). Reading that suggestion is faster than debugging.

## 13. Python version differs between the laptop and CI

The laptop runs Python 3.14 and the pipeline pins 3.12. The tests pass on both, which is useful evidence that the code does not depend on a specific version. A version matrix is a future step.
