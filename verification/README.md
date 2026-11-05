# Browser verification

The scripts start an HTTP server on a disposable local port and use isolated browser storage. They never open a personal profile or load private student backups. Generated reports and screenshots are ignored by Git under `verification/publication/`.

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
python3 verification/verifier_bilan_seance.py
python3 verification/verifier_interface_epuree.py
```

- Mobile: six touch viewports, consent, navigation, lessons, vocabulary, progression, exercises, full expressions, sense button and modal. Checks actual element bounds.
- Visitor session: explicit persistence, temporary storage, refresh/browser restart, original data protection, JSON export and storage failures.
- Vocabulary: whole phrasal verbs, contextual suggestions, all senses, isolated saved words, keyboard controls, mobile modal and export.
- Session summary: five completed exercises, scores 0/10, 9/10 and 10/10, compact corrections, meaningful curriculum estimates, preserved answers/history, JSON export and browser restart.

WebKit availability is reported by the mobile script. Chromium touch emulation does not prove Safari compatibility. Optionally install WebKit with `python3 -m playwright install webkit`.

The public application at `https://eliasbellouti.com/demos/toeic/TOEIC_Lab.html` was also checked over HTTPS on November 4, 2026: 66 mobile states, 10 visitor-session checks, 57 complete expressions, JSON export and a full browser close/reopen. Those application checks reported no JavaScript errors; the seven served application files matched the tested repository. Portfolio navigation is verified separately, since its navigation and prefetch behavior belongs to the hosting project.

- Simplified interface: avatar menu, local name/photo, storage consent, concise corrections, on-demand translation, pause/resume, full close/reopen and real JSON export/import. The profile suite also accepts `TOEIC_TEST_URL` and `TOEIC_TEST_OUT` for a disposable-profile HTTPS run.
