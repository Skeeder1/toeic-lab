"""Cross-session question rotation checks, disposable profiles exclusively.

TOEIC_APP_DIR selects an installed or sanitised public edition. TOEIC_TEST_URL
can target HTTPS. --audit records all failing cases without a failing exit code.
"""
import functools
import hashlib
import http.server
import json
import os
import re
import shutil
import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
APP = Path(os.environ.get("TOEIC_APP_DIR", ROOT.parent))
OUT = Path(os.environ.get("TOEIC_TEST_OUT", ROOT / "publication" / "variete"))
EXPOSURE = "toeiclab.questions.exposure.v1"
FILES = ["TOEIC_Lab.html"] + sorted(set(re.findall(
    r'<(?:script|link)\b[^>]*(?:src|href)="([^":]+\.(?:js|css))"',
    (APP / "TOEIC_Lab.html").read_text())))
RESET_RNG = """(seed)=>{let n=Number.isInteger(seed)?seed:7;Math.random=()=>{n=(1664525*n+1013904223)>>>0;return n/4294967296}}"""
POOL = """V6_ALL.filter(q=>q.source==='toeic'&&(Number(q.tier)||3)>=3&&/^(syntax|relative|tense):/.test(q.group))"""
START = """(size)=>{v7State.section='toeic';v7Cfg().length=String(size);v7Cfg().feedback='exam';v7Cfg().mode='auto';v6Start();return [...v6Session.items,...v6Session.v14Queue].map(q=>({key:q.key,text:q.text,group:q.group}))}"""


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"checks": [], "failures": [], "javascript_errors": [], "runs": []}
    server = None
    with tempfile.TemporaryDirectory(prefix="toeic-rotation-") as temp, sync_playwright() as playwright:
        temp = Path(temp)
        url = os.environ.get("TOEIC_TEST_URL")
        if not url:
            # Freeze a copy: another agent may finish a source edit during this run.
            frozen = temp / "application"
            frozen.mkdir()
            for name in FILES:
                shutil.copy2(APP / name, frozen / name)
            report["source_sha256"] = hashlib.sha256((frozen / "TOEIC_Lab.html").read_bytes()).hexdigest()
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(frozen)))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = f"http://127.0.0.1:{server.server_port}/TOEIC_Lab.html"
        report["url"] = url
        browser = playwright.chromium.launch(executable_path=os.environ.get("CHROMIUM_EXECUTABLE", "/usr/bin/brave-browser"), headless=True)

        def fresh():
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            page.set_default_timeout(7000)
            page.on("pageerror", lambda error: report["javascript_errors"].append(str(error)))
            page.goto(url)
            page.locator("[data-tv-accept]").click()
            page.evaluate(RESET_RNG)
            return context, page

        def check(name, function):
            try:
                function()
                report["checks"].append(name)
                print("PASS", name, flush=True)
            except Exception as error:
                report["failures"].append({"check": name, "error": str(error)})
                print("FAIL", name, str(error)[:300], flush=True)

        def preview_pure():
            context, page = fresh()
            try:
                before = page.evaluate("JSON.stringify(Object.entries(localStorage).sort())")
                for _ in range(3):
                    assert len(page.evaluate("__toeicV18.selectPreview('toeic',20)")) == 20
                assert page.evaluate("JSON.stringify(Object.entries(localStorage).sort())") == before
            finally:
                context.close()
        check("Un aperçu ne modifie aucun stockage, réponse ou historique", preview_pure)

        def structural_variants():
            context, page = fresh()
            try:
                result = page.evaluate("""()=>{
                    const first=V6_BYKEY.get('v14_original_0252'),near=V6_BYKEY.get('v14_original_0257'),other=V6_BYKEY.get('v18:original:048');
                    if(!first||!near||!other)throw Error('Known branch director/safety officer fixtures missing');
                    const snapshot=JSON.stringify(Object.entries(localStorage).sort()),start=performance.now();
                    const rotation=__toeicRotation.context();rotation.selected(first);
                    const prioritized=rotation.prioritize([near,other]).map(q=>q.key),onlyVariant=rotation.prioritize([near]).map(q=>q.key);
                    const coldMs=performance.now()-start,warmStart=performance.now();
                    for(let i=0;i<10;i++){const next=__toeicRotation.context();next.selected(first);next.prioritize([near,other]);}
                    return {prioritized,onlyVariant,coldMs,warmMeanMs:(performance.now()-warmStart)/10,storageUnchanged:snapshot===JSON.stringify(Object.entries(localStorage).sort())};
                }""")
                report["variation_timings"] = result
                assert result["prioritized"] == ["v18:original:048"], result
                assert result["onlyVariant"] == ["v14_original_0257"], result
                assert result["storageUnchanged"], result
            finally:
                context.close()
        check("Variantes branch director/safety officer espacées, mais toujours utilisables si elles seules restent", structural_variants)

        def twenty_series(size, correct):
            context, page = fresh()
            try:
                result = page.evaluate("""({size,correct})=>{
                    const norm=s=>s.toLowerCase().normalize('NFD').replace(/[^a-z0-9]+/g,' ').trim();
                    const keys=new Set(),texts=new Set(),runs=[];
                    for(let index=0;index<20;index++){
                        v7State.section='toeic';v7Cfg().length=String(size);v7Cfg().feedback='exam';v7Cfg().mode='auto';v6Start();
                        const selected=[...v6Session.items,...v6Session.v14Queue];
                        const repeat=selected.filter(q=>keys.has(q.key)||texts.has(norm(q.text)));
                        runs.push({number:index+1,count:selected.length,repeated:repeat.map(q=>q.key),keys:selected.map(q=>q.key)});
                        for(const q of selected){keys.add(q.key);texts.add(norm(q.text))}
                        while(v6Session){const q=v6Session.items[v6Session.index];v6Answer(correct?q.correct:(q.correct+1)%4);v6Advance()}
                    }
                    return {size,correct,runs,unique:keys.size,events:v6Events.length,history:v5History.length};
                }""", {"size": size, "correct": correct})
                report["runs"].append(result)
                assert result["events"] == size * 20
                assert all(row["count"] == size for row in result["runs"])
                assert not any(row["repeated"] for row in result["runs"]), [row for row in result["runs"] if row["repeated"]]
            finally:
                context.close()
        for size, correct in [(10, True), (10, False), (20, True), (20, False)]:
            check(f"20 séries réelles de {size}, réponses {'justes' if correct else 'fausses'} : aucun énoncé répété", lambda size=size, correct=correct: twenty_series(size, correct))

        def priority_before_quotas():
            context, page = fresh()
            try:
                wanted = page.evaluate("""()=>{
                    const pool=""" + POOL + """,g=pool.find(q=>pool.filter(z=>z.group===q.group).length>=12).group;
                    const fresh=pool.filter(q=>q.group===g).slice(0,10),ids=new Set(fresh.map(q=>q.key));
                    const events=pool.filter(q=>!ids.has(q.key)).map((q,i)=>({id:q.key,group:q.group,correct:true,date:new Date(Date.now()-1000000+i).toISOString(),session:'old-'+Math.floor(i/20)}));
                    localStorage.setItem('toeiclab.v6.answers',JSON.stringify(events));return fresh.map(q=>q.key);
                }""")
                page.reload()
                chosen = page.evaluate("__toeicV18.selectPreview('toeic',10).map(q=>q.key)")
                assert set(chosen) == set(wanted), {"wanted": wanted, "chosen": chosen}
            finally:
                context.close()
        check("Les dix derniers inédits passent avant les quotas de familles et de notions", priority_before_quotas)

        def legacy_aliases(seed, already_reencoded=False):
            context, page = fresh()
            try:
                page.evaluate(RESET_RNG, seed)
                original = page.evaluate("""()=>{const qs=__toeicV18.selectPreview('toeic',20);localStorage.setItem('toeiclab.history.v5',JSON.stringify([{id:'legacy-session',date:new Date().toISOString(),level:'TOEIC',questions:qs.map(q=>({id:q.id,group:q.group,chosen:0,expected:0}))}]));return qs.map(q=>q.key)}""")
                if already_reencoded:
                    page.evaluate("""()=>{
                        const key='toeiclab.v10.imported-questions',bank=JSON.parse(localStorage.getItem(key)||'[]');
                        for(const q of bank)q.id=q.key.replace(/[^A-Za-z0-9_]/g,'_');
                        localStorage.setItem(key,JSON.stringify(bank));
                    }""")
                page.reload()
                before_history = page.evaluate("JSON.stringify(v5History)")
                before_events = page.evaluate("JSON.stringify(v6Events)")
                page.evaluate(RESET_RNG, seed)
                chosen = page.evaluate("__toeicV18.selectPreview('toeic',20).map(q=>q.key)")
                assert not set(chosen) & set(original), {"aliases_repeated": list(set(chosen) & set(original))}
                assert page.evaluate("JSON.stringify(v5History)") == before_history, "Preview changed legacy history"
                assert page.evaluate("JSON.stringify(v6Events)") == before_events, "Preview changed answer events"
            finally:
                context.close()
        for seed in [0, 7]:
            check(f"Anciens identifiants q.id reconnus sans réinitialiser historique ni réponses, seed {seed}", lambda seed=seed: legacy_aliases(seed))
        check("Profil déjà réencodé par l'ancienne version : les anciens alias restent reconnus", lambda: legacy_aliases(0, True))

        def paused_reservation():
            context, page = fresh()
            try:
                first = page.evaluate(START, 20)
                page.locator("#v18Pause").click()
                assert page.evaluate("__toeicV18.paused()") == 1
                page.evaluate(RESET_RNG)
                second = page.evaluate(START, 20)
                assert not {q["key"] for q in first} & {q["key"] for q in second}
            finally:
                context.close()
        check("Une séance en pause réserve ses questions et sa file sans les rejouer dans la suivante", paused_reservation)

        def displayed_and_idempotent():
            context, page = fresh()
            try:
                first = page.evaluate(START, 10)
                assert first
                ledger = page.evaluate("key=>localStorage.getItem(key)", EXPOSURE)
                assert ledger is not None
                page.evaluate("v6Render();v6Render()")
                assert page.evaluate("key=>localStorage.getItem(key)", EXPOSURE) == ledger
                draft = page.evaluate("JSON.parse(JSON.stringify(v6Session))")
                page.reload()
                assert page.evaluate("key=>localStorage.getItem(key)", EXPOSURE) == ledger
                assert page.evaluate("v6Session.items.map(q=>q.key)") == [q["key"] for q in draft["items"]]
                assert page.evaluate("v6Session.v14Queue.map(q=>q.key)") == [q["key"] for q in draft["v14Queue"]]
                page.evaluate("v6Finish()")
                page.evaluate(RESET_RNG)
                second = page.evaluate(START, 10)
                assert first[0]["key"] not in {q["key"] for q in second}
            finally:
                context.close()
        check("Énoncé affiché sans réponse conservé ; rendu et rechargement idempotents ; brouillon intact", displayed_and_idempotent)

        def exhausted_pool():
            context, page = fresh()
            try:
                recent = page.evaluate("""()=>{
                    const pool=""" + POOL + """,events=pool.map((q,i)=>({id:q.key,group:q.group,correct:true,date:new Date(Date.now()-(pool.length-i)*60000).toISOString(),session:'old-'+Math.floor(i/20)}));
                    localStorage.setItem('toeiclab.v6.answers',JSON.stringify(events));return pool.slice(-40).map(q=>q.key);
                }""")
                page.reload()
                selected = page.evaluate("__toeicV18.selectPreview('toeic',20).map(q=>q.key)")
                assert len(selected) == 20 and len(set(selected)) == 20
                assert not set(selected) & set(recent), {"recent_repeated": list(set(selected) & set(recent))}
            finally:
                context.close()
        check("Après épuisement des inédits, les dernières séries restent évitées si des anciennes sont disponibles", exhausted_pool)

        def export_import_exposure():
            context, page = fresh()
            receiver = None
            try:
                first = page.evaluate(START, 10)
                page.evaluate("v6Answer(v6Session.items[0].correct);v6Advance()")
                ledger = page.evaluate("key=>JSON.parse(localStorage.getItem(key))", EXPOSURE)
                assert ledger is not None
                events = page.evaluate("JSON.parse(JSON.stringify(v6Events))")
                with page.expect_download() as download:
                    page.evaluate("__toeicV18.exportBackup()")
                target = temp / "rotation-backup.json"
                download.value.save_as(target)
                payload = json.loads(target.read_text())
                assert payload.get("v26Exposure") == ledger
                receiver, imported = fresh()
                imported.on("dialog", lambda dialog: dialog.accept())
                with imported.expect_navigation(wait_until="load"):
                    imported.evaluate("payload=>{void __toeicV18.importBackup(new File([JSON.stringify(payload)],'rotation.json',{type:'application/json'}))}", payload)
                imported.wait_for_selector("#tvSettings")
                assert imported.evaluate("key=>JSON.parse(localStorage.getItem(key))", EXPOSURE) == ledger
                assert imported.evaluate("JSON.parse(JSON.stringify(v6Events))") == events
                assert imported.evaluate("v6Session.items[0].key") == first[0]["key"]
                assert imported.evaluate("v6Session.index") == 1
            finally:
                if receiver:
                    receiver.close()
                context.close()
        check("Export et véritable import conservent expositions, réponses, séance et ordre de reprise", export_import_exposure)

        browser.close()
    if server:
        server.shutdown()
    report["status"] = "passed" if not report["failures"] and not report["javascript_errors"] else "failed"
    (OUT / "resultats-variete.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "checks": len(report["checks"]), "failures": report["failures"], "javascript_errors": report["javascript_errors"]}, ensure_ascii=False, indent=2))
    if report["status"] != "passed" and "--audit" not in sys.argv:
        raise SystemExit(1)


if __name__ == "__main__":
    run()
