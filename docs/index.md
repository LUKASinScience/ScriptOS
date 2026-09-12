# ScriptOS

Turn a Python or R command-line script into a validated, reproducible desktop app — **no terminal required.**

![ScriptOS running on macOS](assets/macbook-mockup.png)

## Appearance

**View → Appearance → Dark / Light** in the menu bar. Takes effect after a restart
(ScriptOS offers to restart immediately) — icons and colors are baked in at
startup, so a live switch isn't worth the complexity for a rarely-toggled setting.

## Starting the app

=== "macOS (installed)"

    Double-click **ScriptOS** in Applications, or Spotlight-search for "ScriptOS".

=== "macOS (build it yourself)"

    ```bash
    ./build.sh
    open dist/ScriptOS.app
    # optional: copy it to Applications so it behaves like any other Mac app
    cp -R dist/ScriptOS.app /Applications/
    ```

=== "Developer mode"

    Only needed if you're changing ScriptOS's own code — end users never do this.

    ```bash
    python3 -m venv .venv
    .venv/bin/pip install PySide6 cryptography pytest
    .venv/bin/python -m app.main
    ```

Whichever way you start it, use the **house icon** (top left) any time to get back to
your loaded script — it works from anywhere, including the Environments page.

## Try everything: a full walkthrough

Every path below is a real file already in the ScriptOS project — clone/open the
project folder and follow along exactly. Nothing here needs the internet except
the one-time environment/package installs.

### 1. Run a plain script (no dependencies, no environment needed)

1. Launch ScriptOS, drag `tests/fixtures/analyze.py` onto the window.
2. The analysis card shows: 5 parameters detected, no dependencies (stdlib only).
3. In the **Input** field, drag in `tests/fixtures/samples.csv` (or click its folder icon to browse).
4. Watch the **command preview** update live as you type.
5. Click **Run**. The Logs tab streams output; when it finishes, open the **Report**
   tab — that's your reproducibility record (exact command, parameters, duration).

### 2. Create an environment and install real dependencies

1. Click **Environments** (top right) → **Environments** tab → **+ New environment**,
   name it `demo`.
2. Go back (arrow-left) to your script, load `tests/fixtures/plot_histogram.py` instead
   (drag it on, or use **File → Recent Scripts** if you loaded it before).
3. Its analysis card shows `pandas` and `matplotlib` as **✗ not installed** — that's
   checked against whatever's currently selected in the **Environment** dropdown.
4. Set the **Environment** dropdown to `demo`. The dependency list re-checks against
   that environment — still missing there too.
5. Click **Install missing dependencies into this environment**. Watch pip run live;
   when it's done, both packages show ✓.
6. Fill **Input** with `tests/fixtures/samples.csv`, leave **Output Dir** as `.`, click **Run**.
7. Open the **Files** tab — `histogram.png` is listed; double-click to open it.
8. Reload the same script later (or reopen ScriptOS) — the `demo` environment is
   still selected automatically. Check **Environments → Environments tab → demo** and
   you'll see "Activated for: plot_histogram.py" and its on-disk location.

### 3. Store a secret in the wallet and use it in a run

1. **Environments → Secrets Wallet tab → + New set**, name it `Demo Credentials`,
   enter a key like `API_TOKEN` and any test value.
2. Back on a loaded script, set the **Secrets** dropdown to `Demo Credentials`.
3. Look at the **command preview** — the secret is *not* there. It's injected only
   into the script's environment variables at run time, never as a visible argument.
   (To prove it to yourself: temporarily add `import os; print(os.environ.get("API_TOKEN"))`
   to a test script and run it — you'll see the value in the Logs tab, and only there.)
4. The wallet's key file and encrypted store live in `~/.scriptos/` — check
   `cat ~/.scriptos/credentials.enc.json` yourself; it's ciphertext, not your value.

### 4. Run an R script

1. Install R once if you haven't: `brew install r`
2. Install the one R package ScriptOS's discovery relies on:
   `Rscript -e 'install.packages("optparse", repos="https://cloud.r-project.org")'`
3. Load `tests/fixtures/runnable_r_tool.R` — no extra dependencies, safe to run immediately.
4. Set **Input** to `tests/fixtures/samples.csv`, click **Run** — same workflow as Python,
   just a different interpreter under the hood.

### 5. Chain two scripts as a workflow

Workflows are a simple linear chain — not a full pipeline engine. Each step's
declared output feeds the next step's first file/directory input, automatically.

1. Click **Workflows** (top right) → **+ New workflow**, name it `demo chain`.
2. **+ Add step** twice: pick `tests/fixtures/workflow_step_a.py`, then
   `tests/fixtures/workflow_step_b.py`.
3. Click **Run workflow**. Step 1 writes a result file; step 2 automatically
   receives step 1's output location and reads it back — no path typed by hand.

### 6. Use the command line (for people who already live in a terminal)

ScriptOS ships a small `scriptos` CLI that shares the same environments and
manifests as the GUI:

```bash
scriptos list                       # environments + which scripts use them
scriptos new my-env                 # create one
scriptos activate my-env            # opens a subshell with it on PATH
scriptos run tests/fixtures/analyze.py --env my-env -- --input tests/fixtures/samples.csv
```

Or skip the CLI entirely: on the Environments page, each environment shows a
copyable `source .../bin/activate` line — that's a plain Python venv, so any
tool that understands venvs (including your own shell) works with it directly.

### 7. Power Terminal: jump straight into a directory + environment

For working from a plain terminal without keeping a tab open just to stay
oriented. Two independent wallets you mix and match:

```bash
scriptos dir new my-project ~/Desktop/my-project     # save a directory once
scriptos activate my-env --dir my-project            # cd + activate in one step
```

Or in the app: **Environments → Power Terminal tab** — pick an environment and
a saved directory from the two dropdowns, get a copyable `cd ... && source
.../bin/activate` line, or click **Open Terminal here** to launch a new
Terminal.app window already sitting in that directory with that environment active.

### 8. See what a script without CLI flags looks like

Load `tests/fixtures/interactive_script.py` — it calls `input()` and has zero
argparse flags. The analysis card warns about both: no configurable parameters, and
a script that would otherwise hang forever waiting for typed input (ScriptOS makes
it fail fast with a clear error instead).

## Installing R

ScriptOS detects whether `Rscript` is on your system and tells you how to fix it if not:

```bash
brew install r
Rscript -e 'install.packages("optparse", repos="https://cloud.r-project.org")'
```

`optparse` is what ScriptOS's R parameter discovery looks for (`make_option()` calls).

## What ScriptOS is not

- Not a workflow engine — one script, one run
- Not a replacement for the command line for people who already use it
- Never installs anything without you clicking a button first
- Never touches your OS keychain — the secrets wallet is entirely local to `~/.scriptos`
