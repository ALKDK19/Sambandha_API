# How to stop Git from tracking sensitive files and folders

If your `.gitignore` is not being respected (files are already tracked), use the following steps to remove those files from the Git index while keeping them on disk.

Important: make a backup of any sensitive files before changing tracking (copy them outside the repo or to a secure location).

1) Add the files/folders to `.gitignore`

Add lines like the following to your repository's `.gitignore` (or ensure equivalent rules exist):

```
# sensitive credentials
firebase-credentials.json
.env

# runtime / logs / venv
logs/
.venv/

# generated or local scripts/state
scripts/
```

2) Remove the files from the index (stop tracking) but keep them locally

Run these commands from the repository root. Note: the correct flag is `--cached` (not `--cache`). Use `-r` when removing directories.

```
# single files
git rm --cached firebase-credentials.json
git rm --cached .env

# directories (recursive)
git rm -r --cached logs
git rm -r --cached .venv
git rm -r --cached scripts
```

3) Commit the changes

```
git add .gitignore
git commit -m "Stop tracking sensitive files (firebase credentials, env, logs, venv, scripts)"
```

4) Push to remote

```
git push origin <branch>
```

Replace `<branch>` with your current branch name (for example `main` or `develop`).

5) Verify that files are no longer tracked

```
# show files staged/changed
git status

# show tracked files that match ignore rules (should be none)
git ls-files --ignored --exclude-standard

# check a single file
git check-ignore -v firebase-credentials.json
```

Notes and safety considerations

- These commands only remove files from the index (stop tracking). The files remain on your local disk.
- If the sensitive files were already pushed to a remote, they will still exist in the repository history. To remove them from history you must rewrite history using tools such as `git filter-repo` or the BFG Repo-Cleaner — both are destructive operations and require care. Example references:
  - git filter-repo: https://github.com/newren/git-filter-repo
  - BFG: https://rtyley.github.io/bfg-repo-cleaner/

- After rewriting history you will need to force-push and coordinate with anyone who has cloned the repo.

- If you accidentally removed a file from the index and want to re-track it, re-add and commit:

```
# re-track a file
git add firebase-credentials.json
git commit -m "Re-add firebase credentials"
```

Quick checklist

- [ ] Backup sensitive files
- [ ] Add patterns to `.gitignore`
- [ ] git rm --cached ... (or git rm -r --cached for directories)
- [ ] Commit and push
- [ ] Verify with `git status` / `git check-ignore`

If you'd like, I can also:
- Prepare a safe `.gitignore` snippet tailored to this repo
- Show exact git commands to remove a file from history (and explain the risks)

