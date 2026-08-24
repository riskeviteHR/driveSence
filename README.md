# DriveSense

*Analyze • Optimize • Recover — Smarter Storage. Safer Cleanup.*

A local, login-protected dashboard for scanning your C: drive (or any folder),
finding duplicate files, temp/cache junk, old downloads, and large files with
explainable risk scores — and cleaning them up safely. Nothing is ever
permanently deleted: every action goes to the Recycle Bin and is logged.

Everything runs on your own machine. No data leaves your computer, no
internet connection is required to use it, and nothing is shared between
different people's installs — each person who runs this creates their own
local login and scans their own PC.

## Option A: Run from source (needs Python)

1. Install [Python 3.10 or newer](https://www.python.org/downloads/) if you
   don't have it (check "Add Python to PATH" during install).
2. Unzip this folder anywhere.
3. Open a terminal in that folder and install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run the app:
   ```
   python app.py
   ```
   Your browser opens automatically to `http://127.0.0.1:5000`.
5. First run: create a local username/password. This is stored only on your
   PC and just prevents someone else walking up to your computer from
   opening it — it isn't hardened security.

## Option B: Standalone .exe (no Python needed)

Double-click `DriveSense.exe`. A browser tab opens automatically. Same
first-run login step as above.

**If Windows SmartScreen or your antivirus flags it:** this is a common false
positive for apps built with PyInstaller (the packaging tool used here), not
a sign of anything malicious — the source code is right here in this folder
if you want to check it yourself, and Option A runs the exact same code
without needing to trust a packaged binary at all.

Keep the .exe in its own folder — it creates a few small files next to
itself (your login, scan history, exclusions list) to remember your data
between runs.

## Using it

- **Scan Your Folder** — pick a folder or a whole drive (`C:\` gives the
  fullest picture, including temp/cache detection). A full-drive scan takes
  a couple of minutes, plus more time to hash files for duplicate detection.
  You can pause/resume from the progress screen.
- **See Results** — the dashboard: disk usage, storage by folder/type,
  largest files, and one-click "Clear" buttons for known-safe cache/temp
  locations. Download the full file-wise Excel breakdown from here too.
- **Cleanup Center** (top nav) — duplicates (verified by content hash, not
  just name/size), temp/cache files, old downloads, large files, and an
  unknown-file review queue. Every item shows a risk level, a confidence
  score, and why it was flagged.
- **Exclusions** (top nav) — add paths you never want scanned or touched.
- **Audit Logs** (top nav) — full history of every scan and every cleanup
  action, including refused ones.

## Safety model

- Windows, Program Files, ProgramData, AppData, drivers, boot files, and
  known antivirus sandbox folders are excluded from cleanup entirely — they
  never even appear as suggestions.
- Unrecognized file types always require typed confirmation before deletion.
- Duplicate groups always keep at least one copy.
- Every delete goes to the Recycle Bin — restore anything from there the
  normal Windows way.
