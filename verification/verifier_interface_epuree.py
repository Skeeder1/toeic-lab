"""Exercise/profile integration checks using disposable browser profiles only.

TOEIC_TEST_URL optionally points to the public deployment; otherwise a temporary
HTTP origin serves the installed edition, without using the personal origin.
"""
import functools
import http.server
import json
import os
import struct
import tempfile
import threading
import zlib
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent
APP = Path(os.environ.get("TOEIC_APP_DIR", ROOT.parent))
OUT = Path(os.environ.get("TOEIC_TEST_OUT", ROOT / "publication" / "epure"))
PROFILE = "toeiclab.ui.profile.v1"
SIZES = [(320, 640), (390, 844), (844, 390), (1440, 1050)]


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        # The production portfolio supplies its favicon; this disposable origin
        # does not. An empty icon response avoids an unrelated test-server 404.
        if self.path.split("?")[0] == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        super().do_GET()


def avatar_png():
    """Small synthetic 192×192 raster image; no personal photograph is read."""
    def chunk(kind, content):
        return struct.pack(">I", len(content)) + kind + content + struct.pack(">I", zlib.crc32(kind + content))
    pixels = b"".join(b"\x00" + bytes((38, 80 + y // 3, 150, 255)) * 192 for y in range(192))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 192, 192, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    server = None
    url = os.environ.get("TOEIC_TEST_URL")
    if not url:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(APP)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_port}/TOEIC_Lab.html"
    report = {"url": url, "checks": [], "javascript_errors": [], "console_errors": [], "overflow": []}

    def checked(message):
        report["checks"].append(message)
        print(message, flush=True)

    try:
        with tempfile.TemporaryDirectory(prefix="toeic-clean-ui-") as tmp, sync_playwright() as p:
            photo_file = Path(tmp) / "avatar-192.png"
            photo_file.write_bytes(avatar_png())

            def launch(name="persistent", width=1440, height=1050):
                context = p.chromium.launch_persistent_context(
                    str(Path(tmp) / name), executable_path="/usr/bin/brave-browser", headless=True,
                    viewport={"width": width, "height": height}, accept_downloads=True,
                )
                context.add_init_script("window.__testNativeStorage=window.localStorage")
                page = context.pages[0]
                page.set_default_timeout(7000)
                page.on("pageerror", lambda e: report["javascript_errors"].append(str(e)))
                page.on("console", lambda e: report["console_errors"].append(e.text) if e.type == "error" else None)
                page.goto(url)
                page.wait_for_selector("#tvSettings")
                return context, page

            def menu_action(page, action):
                page.locator("#tvSettings").click()
                page.locator("#tvProfileMenu").wait_for(state="visible")
                page.locator(f'[data-tv-profile-action="{action}"]').click()

            def fit(page, name):
                page.wait_for_timeout(100)
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2"), name
                over = page.evaluate("""() => [...document.querySelectorAll('#tvSettings,#tvProfileMenu,#tvProfileEditor,#tvPanel')].filter(e=>{
                    const r=e.getBoundingClientRect(),s=getComputedStyle(e);
                    return r.width>0&&r.height>0&&s.visibility!=='hidden'&&(r.left< -2||r.right>innerWidth+2||r.top< -2||r.bottom>innerHeight+2)
                }).map(e=>({id:e.id,rect:e.getBoundingClientRect().toJSON()}))""")
                report["overflow"].extend({"state": name, **e} for e in over)
                assert not over, (name, over)

            context, page = launch()
            assert page.locator("#tvPanel").is_visible()
            assert page.evaluate("Object.keys(__testNativeStorage).filter(k=>k.startsWith('toeiclab.')).length") == 0
            page.locator("[data-tv-accept]").click()
            assert page.evaluate("ToeicVisitor.mode") == "persistent"
            assert page.locator(".v7-header #tvSettings").count() == 1
            assert page.locator('.v20-nav [data-v20-nav="progress"]').count() == 0
            assert "Données sur cet appareil" not in page.locator(".v7-header").inner_text()
            checked("Avatar unique dans l’en-tête ; progression et données retirées de la navigation principale ; aucune nouvelle écriture permanente avant accord")

            for width, height in SIZES:
                page.set_viewport_size({"width": width, "height": height})
                page.locator("#tvSettings").click()
                assert page.locator("#tvSettings").get_attribute("aria-expanded") == "true"
                for action in ["progress", "edit", "data", "words"]:
                    assert page.locator(f'[data-tv-profile-action="{action}"]').is_visible()
                fit(page, f"menu-{width}x{height}")
                page.screenshot(path=str(OUT / f"profil-menu-{width}x{height}.png"))
                page.keyboard.press("Escape")
                assert not page.locator("#tvProfileMenu").is_visible()
                assert page.locator("#tvSettings").evaluate("e=>e===document.activeElement")
                page.locator("#tvSettings").click()
                page.mouse.click(2, 2)
                assert not page.locator("#tvProfileMenu").is_visible()
            checked("Menu à 320/390/844 paysage/1440 px : aucune sortie d’écran, actions accessibles, Échap et clic extérieur ferment le menu")

            for width, height in SIZES:
                page.set_viewport_size({"width": width, "height": height})
                menu_action(page, "edit")
                fit(page, f"editor-{width}x{height}")
                page.keyboard.press("Escape")
                assert not page.locator("#tvProfileEditor").is_visible()
                menu_action(page, "data")
                fit(page, f"data-{width}x{height}")
                for selector in ["[data-tv-temporary]", "[data-tv-export]"]:
                    rect=page.locator(selector).bounding_box()
                    assert rect and rect["y"] >= 0 and rect["y"]+rect["height"] <= height+2, (selector,width,height,rect)
                page.keyboard.press("Escape")
                assert not page.locator("#tvPanel").is_visible()
            checked("Éditeur et données à quatre formats : cadres et deux choix de mémorisation restent dans l’écran")

            page.set_viewport_size({"width": 390, "height": 844})
            menu_action(page, "edit")
            editor = page.locator("#tvProfileEditor")
            assert editor.is_visible()
            # Delay the real browser decoder, close its dialog, then reopen.
            # A stale asynchronous request must not keep the save button disabled.
            page.evaluate("""() => {
                window.__originalBitmap=createImageBitmap;
                window.createImageBitmap=file=>new Promise((resolve,reject)=>{
                    window.__releaseBitmap=()=>window.__originalBitmap(file).then(resolve,reject);
                });
            }""")
            page.locator("[data-tv-photo]").set_input_files(str(photo_file))
            assert page.locator("[data-tv-save-profile]").is_disabled()
            page.keyboard.press("Escape")
            menu_action(page, "edit")
            assert page.locator("[data-tv-save-profile]").is_enabled()
            page.evaluate("""() => {window.__releaseBitmap();window.createImageBitmap=window.__originalBitmap;}""")
            page.wait_for_timeout(100)
            assert page.locator("[data-tv-save-profile]").is_enabled()
            page.locator("[data-tv-name]").fill("Camille")
            page.locator("[data-tv-photo]").set_input_files(str(photo_file))
            page.wait_for_function("document.querySelector('[data-tv-preview] img')?.naturalWidth === 192 && !document.querySelector('[data-tv-save-profile]').disabled")
            avatar = page.locator("[data-tv-avatar]").last
            avatar.click()
            fit(page, "editor-390")
            page.screenshot(path=str(OUT / "profil-edition-390.png"))
            page.locator("[data-tv-save-profile]").click()
            assert not editor.is_visible()
            profile = page.evaluate("key=>localStorage.getItem(key)", PROFILE)
            assert "Camille" in profile
            photo = json.loads(profile)["photo"]
            assert photo.startswith("data:image/webp;base64,") and len(photo) <= 180000
            sanitizer = page.evaluate("""() => {
                const bad=['data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=', 'data:text/html;base64,PGgxPng8L2gxPg==', 'https://example.com/photo.png'];
                return bad.map(photo=>ToeicVisitor.sanitizeProfile({version:1,name:'  Camille  ',avatar:'unknown',photo}));
            }""")
            assert all(row["photo"] == "" and row["name"] == "Camille" and row["avatar"] == "indigo" for row in sanitizer)
            checked("Photo raster locale 192×192 importée et réduite en WebP ; fermeture pendant décodage puis réouverture sans bouton bloqué ; SVG/data texte/URL distante refusés par le sanitizer")
            page.reload()
            page.wait_for_selector("#tvSettings")
            assert page.evaluate("key=>localStorage.getItem(key)", PROFILE) == profile
            menu_action(page, "edit")
            assert page.locator("[data-tv-name]").input_value() == "Camille"
            assert page.locator("[data-tv-preview] img").get_attribute("src") == photo
            assert page.locator("[data-tv-preview] img").evaluate("e=>e.naturalWidth===192&&e.naturalHeight===192")
            page.keyboard.press("Escape")
            assert not editor.is_visible()
            checked("Nom et avatar modifiés puis conservés après rechargement ; éditeur accessible et fermé au clavier")

            menu_action(page, "progress")
            assert page.locator(".v7-progress-page").is_visible()
            page.locator('[data-v20-nav="home"]').first.click()
            page.locator('[data-v20-section="toeic"]').first.click()
            page.locator("#v7Start").click()
            # Use an existing bank question in a legitimately started session;
            # keep the session's initialized section/configuration unchanged.
            fixture = page.evaluate("""() => {
                const q=V6_BYKEY.get('toeic:v5_023');
                if(!q||!q.options.includes('Meanwhile'))throw Error('Existing Meanwhile question missing');
                v6Session.items[0]=JSON.parse(JSON.stringify(q));v6Session.index=0;
                v6Session.answers={};v6Session.feedback='learn';v7Save();v6Render();
                return {key:q.key,correct:q.correct,fr:q.fr,options:q.options};
            }""")
            report["fixture"] = {"key": fixture["key"], "options": fixture["options"]}
            body = page.locator(".v7-question-paper").inner_text()
            for redundant in ["Traduire les choix", "Vocabulaire de la question", "Survole", "Un doute sur une règle"]:
                assert redundant not in body, redundant
            assert page.locator("#v7Translate").is_visible()
            word = page.locator('.v7-answer-text [data-tl-term="Meanwhile"]')
            before_answers = page.evaluate("JSON.stringify(v6Session.answers)")
            word.click()
            assert page.locator("[data-tl-save]").is_visible()
            assert page.evaluate("JSON.stringify(v6Session.answers)") == before_answers
            page.locator("[data-tl-save]").click()
            page.locator("[data-tl-close]").click()
            assert page.evaluate("window.__toeicVocabBridge.list().some(x=>x.term.toLowerCase()==='meanwhile')")
            checked("Exercice débarrassé des aides/boutons redondants ; cliquer un mot des choix permet de l’ajouter sans répondre")

            wrong = (fixture["correct"] + 1) % 4
            page.locator(f'[data-v7-answer="{wrong}"] .v7-letter').click()
            assert page.locator(".v7-correction").is_visible()
            correction = page.locator(".v7-correction").inner_text()
            assert fixture["fr"] not in correction
            assert fixture["options"][fixture["correct"]] in correction
            assert not page.locator(".v7-correction .v14-trap").count()
            for width, height in SIZES:
                page.set_viewport_size({"width": width, "height": height})
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
                page.locator(".v7-correction").scroll_into_view_if_needed()
                page.screenshot(path=str(OUT / f"correction-{width}x{height}.png"))
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator("#v7Translate").click()
            assert fixture["fr"] in page.locator(".v8-full-translation").inner_text()
            page.locator("#v7Translate").click()
            assert not page.locator(".v8-full-translation").count()
            answered_snapshot = page.evaluate("JSON.stringify(v6Session.answers)")
            word.click()
            assert page.locator("[data-tl-save]").is_visible()
            page.locator("[data-tl-close]").click()
            assert page.evaluate("JSON.stringify(v6Session.answers)") == answered_snapshot
            checked("Correction erronée simplifiée sans traduction automatique ; traduction sur demande toujours disponible ; mots cliquables après correction")

            draft = page.evaluate("JSON.parse(JSON.stringify(v6Session))")
            event_snapshot = page.evaluate("JSON.stringify(v6Events)")
            menu_action(page, "progress")
            assert page.locator(".v7-progress-page").is_visible()
            assert page.evaluate("JSON.stringify(v6Events)") == event_snapshot
            with page.expect_download() as download:
                page.evaluate("window.__toeicV18.exportBackup()")
            dest = Path(tmp) / "backup.json"
            download.value.save_as(dest)
            payload = json.loads(dest.read_text())
            assert any(x["term"].lower() == "meanwhile" for x in payload["v10Vocabulary"])
            assert payload.get("v24UiProfile") == json.loads(profile)
            candidates = [payload.get("v6Session")] + (payload.get("v18Paused") or [])
            assert any(s and s["answers"] == draft["answers"] and s["items"] == draft["items"] for s in candidates)
            menu_action(page, "data")
            assert page.locator("#tvPanel").is_visible()
            fit(page, "data-390")
            page.keyboard.press("Escape")
            assert not page.locator("#tvPanel").is_visible()
            checked("Progression et préférences accessibles par l’avatar ; navigation préserve les réponses/événements ; export inclut profil, vocabulaire et séance")

            context.close()
            context, page = launch()
            assert page.evaluate("key=>localStorage.getItem(key)", PROFILE) == profile
            assert page.evaluate("window.__toeicVocabBridge.list().some(x=>x.term.toLowerCase()==='meanwhile')")
            current = page.evaluate("v6Session")
            if current is None:
                resume = page.locator("[data-v20-resume]").first
                if not resume.count():
                    page.locator('[data-v20-section="toeic"]').first.click()
                    resume = page.locator("[data-v18-resume]").first
                resume.click()
                page.wait_for_selector(".v7-question")
                current = page.evaluate("v6Session")
            for field in ["items", "answers", "index"]:
                assert current[field] == draft[field], field
            assert page.evaluate("JSON.stringify(v6Events)") == event_snapshot
            checked("Fermeture complète/réouverture : profil, mot enregistré et réponses/ordre de la séance conservés")
            context.close()

            context, page = launch("imported", 390, 844)
            page.locator("[data-tv-accept]").click()
            imported_dialogs = []
            def accept_import_dialog(dialog):
                imported_dialogs.append({"type": dialog.type, "message": dialog.message})
                dialog.accept()
            page.on("dialog", accept_import_dialog)
            with page.expect_navigation(wait_until="domcontentloaded"):
                page.evaluate("""payload=>{window.__toeicV18.importBackup(new File([JSON.stringify(payload)],'backup.json',{type:'application/json'}));}""", payload)
            page.wait_for_selector("#tvSettings")
            assert any(d["type"] == "confirm" for d in imported_dialogs)
            assert any(d["type"] == "alert" and "Import terminé" in d["message"] for d in imported_dialogs)
            assert page.evaluate("key=>localStorage.getItem(key)", PROFILE) == profile
            menu_action(page, "edit")
            assert page.locator("[data-tv-name]").input_value() == "Camille"
            imported_photo = page.locator("[data-tv-preview] img")
            assert imported_photo.get_attribute("src") == photo
            assert imported_photo.evaluate("e=>e.complete&&e.naturalWidth===192&&e.naturalHeight===192")
            page.keyboard.press("Escape")
            assert page.evaluate("window.__toeicVocabBridge.list().some(x=>x.term.toLowerCase()==='meanwhile')")
            imported_session = page.evaluate("v6Session")
            if imported_session is None:
                resume = page.locator("[data-v20-resume]").first
                if not resume.count():
                    page.locator('[data-v20-section="toeic"]').first.click()
                    resume = page.locator("[data-v18-resume]").first
                resume.click()
                page.wait_for_selector(".v7-question")
                imported_session = page.evaluate("v6Session")
            for field in ["items", "answers", "index"]:
                assert imported_session[field] == draft[field], ("import", field)
            assert page.evaluate("JSON.stringify(v6Events)") == event_snapshot
            checked("Vrai import du JSON exporté dans un profil neuf via importBackup : confirmation et rechargement effectifs, nom/photo/vocabulaire/réponses/ordre/événements retrouvés")
            context.close()

            context, page = launch("temporary", 320, 640)
            page.locator("[data-tv-temporary]").click()
            menu_action(page, "edit")
            page.locator("[data-tv-name]").fill("Temporaire")
            page.locator("[data-tv-save-profile]").click()
            assert page.evaluate("key=>localStorage.getItem(key)", PROFILE)
            assert page.evaluate("key=>__testNativeStorage.getItem(key)", PROFILE) is None
            page.reload()
            assert page.evaluate("key=>localStorage.getItem(key)", PROFILE) is None
            checked("Mode temporaire : édition du profil utilisable mais aucune écriture du profil sur disque, puis oubli au rechargement")
            context.close()
        assert not report["javascript_errors"], report["javascript_errors"]
        assert not report["console_errors"], report["console_errors"]
        assert not report["overflow"]
        report["status"] = "passed"
    except Exception as error:
        report["status"] = "failed"
        report["failure"] = repr(error)
        raise
    finally:
        (OUT / "resultats-interface-epuree.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        if server:
            server.shutdown()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
