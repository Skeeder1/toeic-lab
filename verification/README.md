# Browser verification

The three scripts start an HTTP server on a disposable local port and use isolated browser storage. They never open a personal profile or load private student backups. Generated reports and screenshots are ignored by Git under `verification/publication/`.

Install Python 3 and Playwright:

```sh
python3 -m pip install playwright
python3 -m playwright install chromium
```

Scripts automatically use Brave or a system Chromium when found; otherwise they use Playwright Chromium. To select an installed browser explicitly:

```sh
export CHROMIUM_EXECUTABLE=/absolute/path/to/chromium
```

From the repository root:

```sh
python3 verification/verifier_mobile_publication.py
python3 verification/verifier_session_visiteur.py
python3 verification/verifier_aide_vocabulaire.py
```

- Mobile: six touch viewports, consent, navigation, lessons, vocabulary, progression, exercises, full expressions, sense button and modal. Checks actual element bounds.
- Visitor session: explicit persistence, temporary storage, refresh/browser restart, original data protection, JSON export and storage failures.
- Vocabulary: whole phrasal verbs, contextual suggestions, all senses, isolated saved words, keyboard controls, mobile modal and export.

WebKit availability is reported by the mobile script. Chromium touch emulation does not prove Safari compatibility. Optionally install WebKit with `python3 -m playwright install webkit`.
