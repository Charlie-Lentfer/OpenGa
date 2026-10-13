# Deploy OpenGa to Streamlit Community Cloud

The repository root is this folder. Streamlit Cloud runs the app from the root,
reads the theme from `.streamlit/config.toml` at the root, and installs
`requirements.txt` from the root.

```text
.streamlit/config.toml     # theme (UNSW navy); must stay at the repo root
.gitignore
requirements.txt           # pinned: Streamlit 1.63.0, pandas 3.0.2, Altair 6.2.2
app/streamlit_app.py       # main file
app/views/                 # one file per page
app/state.py  app/ui.py  app/pfd.py  app/charts.py  app/lcop.py
app/assets/                # UNSW logo and favicon
openga_v1/                 # the model (includes stream_metadata.json)
openga_flowsheet/          # used by tests/test_streams.py only
tests/  selftest.py  run.sh
```

## 1. Create the repository

1. On github.com, click **+ → New repository**. Name it (for example `OpenGa`),
   choose Public or Private, and leave "Add a README" **unticked** so the repository
   starts empty. Click **Create repository**.
2. On the next page, click **uploading an existing file**.
3. In Finder, open this folder and press **Cmd + Shift + .** so the hidden
   `.streamlit` folder and `.gitignore` show.
4. Select **everything inside** the folder (Cmd + A), not the folder itself, and drag
   it into the GitHub upload box. Check that `.streamlit` is in the list.
5. Click **Commit changes**.

The repository's top level should then show `.streamlit`, `app`, `openga_v1`,
`openga_flowsheet`, `tests`, `requirements.txt` and the Markdown files. If `app` sits
inside another folder, the folder was dragged instead of its contents: delete and
upload again.

## 2. Deploy

1. Go to share.streamlit.io and click **Create app**, then choose the option for an
   app you already have on GitHub.
2. Repository: the new repository. Branch: `main`.
   Main file path: **`app/streamlit_app.py`**.
3. App URL: choose a subdomain, for example `openga`. If the old app already uses
   the name you want, delete the old app (or change its subdomain) first.
4. **Advanced settings → Python version:** 3.12 (the default) or newer. The pinned
   pandas needs Python 3.11 or newer.
5. Click **Deploy**. The first build installs the requirements and takes a few
   minutes.

## 3. Check it

Open the app, press **Run model**, then:

- Results summary shows A$837/kg and 9.9 kg CO₂e/kg at the defaults.
- Step 2 shows the process flow diagram. Hover over stream 1: total 71,943 kg per kg Ga.
- Buttons are UNSW navy. Red buttons mean `.streamlit/config.toml` is missing from
  the repository's top level.

## Updating later

Edit or upload files at the same paths in the repository and commit. Streamlit
Cloud picks up commits on its own. After adding new Python files, reboot the app
from its menu in your Streamlit workspace so it loads them fresh.

## Run locally

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python selftest.py
python -m streamlit run app/streamlit_app.py
```
