"""Fixed Part 5 bank and exam checks in disposable profiles, locally or over HTTPS."""
import functools
import http.server
import json
import os
import tempfile
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
APP = Path(os.environ.get('TOEIC_APP_DIR', ROOT.parent))
OUT = Path(os.environ.get('TOEIC_TEST_OUT', ROOT / 'publication' / 'blancs'))
OUT.mkdir(parents=True, exist_ok=True)


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.split('?')[0] == '/TOEIC_Lab.html':
            html = (APP/'TOEIC_Lab.html').read_text()
            payload = html.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif self.path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
        else:
            super().do_GET()


def run():
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(APP)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    report = {'checks': [], 'errors': [], 'overflow': []}
    url = os.environ.get('TOEIC_TEST_URL') or f'http://127.0.0.1:{server.server_port}/TOEIC_Lab.html'
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE','/usr/bin/brave-browser'), headless=True)

        def fresh():
            context = browser.new_context(viewport={'width':390, 'height':844}, accept_downloads=True)
            page = context.new_page()
            page.set_default_timeout(6000)
            page.on('pageerror', lambda error: report['errors'].append(str(error)))
            page.goto(url)
            page.locator('[data-tv-accept]').click()
            page.wait_for_selector('[data-tm-library]')
            return context, page

        def fit(page, state):
            overflow = page.evaluate("""() => [...document.querySelectorAll('main *,#tmSubmit')].filter(e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none'&&(r.left< -2||r.right>innerWidth+2)}).map(e=>({tag:e.tagName,cls:e.className})).slice(0,10)""")
            assert not overflow, (state, overflow)
            report['overflow'].extend(overflow)

        context, page = fresh()
        bank = page.evaluate('ToeicMockBank')
        assert bank['version'] == 1 and bank['part'] == 5 and len(bank['tests']) == 10
        questions = [q for t in bank['tests'] for q in t['questions']]
        assert len(questions) == 300 and len({q['key'] for q in questions}) == 300
        assert len({q['text'].lower() for q in questions}) == 300
        counts = {key: sum(q['category'] == key for q in questions) for key in 'LWVPCDR'}
        assert counts == dict(L=102,W=65,V=43,P=30,C=29,D=23,R=8), counts
        for test in bank['tests']:
            assert len(test['questions']) == 30
            assert [q['number'] for q in test['questions']] == list(range(101,131))
            for q in test['questions']:
                assert q['text'].count('____') == 1 and len(set(q['options'])) == 4
                assert 0 <= q['correct'] < 4 and q['why'] and q['fr']
        separate = page.evaluate("""()=>{const sig=s=>s.toLowerCase().replace(/[^a-z0-9]+/g,' ').trim(),keys=new Set(V6_ALL.map(q=>q.key)),texts=new Set(V6_ALL.map(q=>sig(q.text)));return ToeicMockBank.tests.every(t=>t.questions.every(q=>!keys.has(q.key)&&!texts.has(sig(q.text))));}""")
        assert separate, 'Mock questions overlap the training bank'
        report['bank'] = {'tests':10,'questions':300,'categories':counts}
        report['checks'].append('Ten real fixed Part 5 tests, 300 distinct questions, observed corpus proportions and a separate targeted bank')
        before = page.evaluate('({events:JSON.stringify(v6Events),obs:JSON.stringify(__toeicV18.getProfile().observations),bank:V6_ALL.length})')
        assert page.locator('.tm-toeic-paths > [data-v20-section="toeic"]').count() == 1
        assert page.locator('.tm-toeic-paths > [data-tm-library]').count() == 1
        assert page.locator('.v20-paths > [data-v20-section]').count() == 5
        assert page.locator('.v20-paths [data-v20-section="toeic"]').count() == 0
        for width,height in [(320,640),(390,844),(844,390),(1440,1050)]:
            page.set_viewport_size({'width':width,'height':height})
            fit(page, 'home')
            columns=page.locator('.tm-toeic-paths').evaluate('e=>getComputedStyle(e).gridTemplateColumns.split(" ").length')
            assert columns == (1 if width <= 560 else 2), (width,columns)
            page.screenshot(path=str(OUT/f'module-home-{width}.png'), full_page=True)
        page.locator('.tm-toeic-paths > [data-v20-section="toeic"]').click()
        assert page.locator('.v18-setup').is_visible()
        page.locator('[data-v20-nav="home"]').first.click()
        report['checks'].append('Targeted and mock Part 5 cards grouped above the other five subjects, two desktop columns/one mobile column, original targeted click handler preserved')
        page.locator('[data-tm-library]').click()
        assert page.locator('.tm-test-card').count() == 10
        for width,height in [(320,640),(390,844),(844,390),(1440,1050)]:
            page.set_viewport_size({'width':width,'height':height})
            fit(page, 'library')
            page.screenshot(path=str(OUT/f'module-library-{width}.png'))
        report['checks'].append('Ten fixed test cards; library within 320/390/844/1440 px; mock questions kept outside V6_ALL')
        page.locator('[data-tm-start="part5-01"]').click()
        assert page.locator('.tm-exam').is_visible()
        assert page.locator('[data-tl-term],#v7Translate,.v25-correction').count() == 0
        page.locator('[data-tm-answer="0"]').click()
        page.locator('[data-tm-answer="1"]').click()
        assert page.evaluate('v6Session.answers[v6Session.items[0].key]') == 1
        page.locator('[data-tm-next]').click()
        page.locator('[data-tm-next]').click()
        assert page.evaluate('v6Session.index') == 2
        page.locator('.tm-question-map summary').click()
        page.locator('[data-tm-question="0"]').click()
        assert page.locator('[data-tm-answer="1"]').get_attribute('aria-pressed') == 'true'
        state = page.evaluate('JSON.stringify(v6Session)')
        page.reload()
        page.wait_for_selector('.tm-exam')
        restored = page.evaluate('JSON.parse(JSON.stringify(v6Session))')
        old = json.loads(state)
        assert restored['answers'] == old['answers'] and restored['items'] == old['items'] and restored['index'] == old['index']
        assert page.evaluate('JSON.stringify(v6Events)') == before['events']
        assert page.evaluate('JSON.stringify(__toeicV18.getProfile().observations)') == before['obs']
        assert page.evaluate('V6_ALL.length') == before['bank']
        report['checks'].append('Tentative answer can change, questions can be skipped, reload preserves answers/order, no answer events or observations before submission')
        page.locator('#v18Pause').click()
        assert page.locator('.tm-library').is_visible()
        assert 'En pause' in page.locator('.tm-test-card').first.inner_text()
        page.locator('[data-tm-start="part5-01"]').click()
        assert page.locator('.tm-exam').is_visible()
        assert page.evaluate('v6Session.answers[v6Session.items[0].key]') == 1
        page.locator('[data-tm-finish]').click()
        assert page.locator('#tmSubmit').is_visible()
        page.locator('[data-tm-continue]').click()
        assert page.evaluate('JSON.stringify(v6Events)') == before['events']
        report['checks'].append('Pause/resume keeps tentative choices; cancelling submission leaves events/observations unchanged')
        for width,height in [(320,640),(390,844),(844,390),(1440,1050)]:
            page.set_viewport_size({'width':width,'height':height})
            fit(page, 'question')
            page.screenshot(path=str(OUT/f'module-question-{width}.png'))
        page.evaluate('''()=>{for(let i=0;i<30;i++){v6Session.index=i;v6Answer(v6Session.items[i].correct)}v6Session.index=29;v6Render();v6Finish()}''')
        assert page.evaluate('JSON.stringify(v6Events)') == before['events']
        page.locator('[data-tm-submit]').click()
        assert page.locator('.v24-results').is_visible()
        result = page.evaluate('JSON.parse(JSON.stringify(v6ResultCache.r))')
        assert result['correct'] == 30 and result['total'] == 30 and result['mockTestId'] == 'part5-01'
        assert page.evaluate('v6Events.length') == 30
        assert page.evaluate('__toeicV18.getProfile().observations.length') == 30
        page.evaluate('v6Finish();v6Finish()')
        assert page.evaluate('v6Events.length') == 30
        page.screenshot(path=str(OUT/'module-results-perfect.png'))
        page.locator('[data-v7-again]').click()
        assert '30 / 30' in page.locator('.tm-test-card').first.inner_text()
        report['checks'].append('Confirmed perfect test creates exactly 30 events/observations, 30/30 result and Completed card; double finish does not regrade')
        context.close()
        context,page = fresh()
        page.evaluate("ToeicMocks.start('part5-02');v6Finish()")
        page.locator('[data-tm-submit]').click()
        result=page.evaluate('JSON.parse(JSON.stringify(v6ResultCache.r))')
        assert result['correct']==0 and result['total']==30 and result['answered']==0
        assert all(item['chosen'] is None for item in result['questions'])
        assert 'Sans réponse' in page.locator('.v24-review-body').first.inner_text()
        assert page.evaluate('v6Events.length')==30
        page.screenshot(path=str(OUT/'module-results-blank.png'))
        report['checks'].append('Fully unanswered confirmed test gives 0/30, history chosen:null and explicit Sans réponse, once')
        with page.expect_download() as download:
            page.evaluate('__toeicV18.exportBackup()')
        target=OUT/'module-synthetic-backup.json';download.value.save_as(target)
        payload=json.loads(target.read_text());assert payload['history'][-1 if payload['history'][-1].get('mockTestId')=='part5-02' else 0]['mockTestId']=='part5-02'
        report['checks'].append('Standard JSON backup contains mock test result metadata and full question history')
        context.close()

        # All ten tests use the real tentative-answer and final-marking chain.
        context,page = fresh()
        score_reports=[]
        for index,test in enumerate(bank['tests']):
            expected_score=index*3
            previous=page.evaluate('({events:JSON.stringify(v6Events),obs:JSON.stringify(__toeicV18.getProfile().observations),history:JSON.stringify(v5History)})')
            page.evaluate('(id)=>ToeicMocks.start(id)',test['id'])
            assert page.locator('.tm-exam').is_visible()
            original_items=page.evaluate('JSON.parse(JSON.stringify(v6Session.items))')
            assert [q['key'] for q in original_items]==[q['key'] for q in test['questions']]
            assert all(q['options']==original['options'] for q,original in zip(original_items,test['questions']))
            page.evaluate('''(wanted)=>{
              for(let i=0;i<30;i++){
                v6Session.index=i;const q=v6Session.items[i];
                v6Answer(i<wanted?q.correct:(q.correct+1)%4);
              }
              v6Session.index=29;v6Render();
            }''',expected_score)
            assert page.evaluate('JSON.stringify(v6Events)')==previous['events']
            assert page.evaluate('JSON.stringify(__toeicV18.getProfile().observations)')==previous['obs']
            assert page.evaluate('JSON.stringify(v5History)')==previous['history']
            page.locator('[data-tm-finish]').click()
            assert page.locator('#tmSubmit').is_visible()
            assert page.evaluate('JSON.stringify(v6Events)')==previous['events']
            assert page.evaluate('JSON.stringify(__toeicV18.getProfile().observations)')==previous['obs']
            page.locator('[data-tm-submit]').click()
            page.locator('.v24-results').wait_for()
            marked=page.evaluate('JSON.parse(JSON.stringify(v6ResultCache.r))')
            assert marked['mockTestId']==test['id'] and marked['mockPart']==5
            assert marked['correct']==expected_score and marked['total']==30 and marked['answered']==30
            assert marked['mockQuestionCount']==30 and marked['mockTitle']==test['title']
            assert len(marked['questions'])==30
            for position,question in enumerate(marked['questions']):
                expected=original_items[position]
                assert question['id']==expected['key'] and question['expected']==expected['correct']
                assert question['chosen']==(expected['correct'] if position<expected_score else (expected['correct']+1)%4)
            expected_events=(index+1)*30
            assert page.evaluate('v6Events.length')==expected_events
            assert page.evaluate('__toeicV18.getProfile().observations.length')==expected_events
            assert page.evaluate('v5History.length')==index+1
            marked_state=page.evaluate('JSON.stringify({events:v6Events,obs:__toeicV18.getProfile().observations,history:v5History})')
            page.evaluate('v6Finish();v6Finish();v6Render();v6Render()')
            assert page.evaluate('JSON.stringify({events:v6Events,obs:__toeicV18.getProfile().observations,history:v5History})')==marked_state
            score_reports.append({'testId':test['id'],'score':marked['correct'],'total':30,'events':expected_events,'history':index+1})
        totals=page.evaluate('({events:v6Events.length,eventIds:new Set(v6Events.map(e=>e.id)).size,observations:__toeicV18.getProfile().observations.length,observationIds:new Set(__toeicV18.getProfile().observations.map(e=>e.questionId)).size,history:v5History.length,tests:new Set(v5History.map(r=>r.mockTestId)).size})')
        assert totals=={'events':300,'eventIds':300,'observations':300,'observationIds':300,'history':10,'tests':10},totals
        report['all_tests']=score_reports
        report['marking_totals']=totals
        report['checks'].append('All ten real tests marked at 0/3/6/9/12/15/18/21/24/27 out of 30; tentative choices ungraded, exact 300 unique events and observations, ten histories, no double marking')
        context.close()

        # Reopen a real persistent temporary browser profile, rather than just
        # reloading the page or transferring a storage_state approximation.
        session_fields=['section','mode','feedback','start','count','index','items','v14Queue','answers','answerTimes','settings','toeicMock']
        with tempfile.TemporaryDirectory(prefix='toeic-mock-persistent-') as profile_dir:
            def persistent_profile():
                persistent=p.chromium.launch_persistent_context(profile_dir,executable_path=os.environ.get('CHROMIUM_EXECUTABLE','/usr/bin/brave-browser'),headless=True,viewport={'width':390,'height':844},accept_downloads=True)
                current=persistent.pages[0]
                current.set_default_timeout(7000)
                current.on('pageerror',lambda error: report['errors'].append(str(error)))
                current.goto(url)
                current.wait_for_selector('#tvSettings')
                if current.locator('[data-tv-accept]').is_visible():current.locator('[data-tv-accept]').click()
                current.wait_for_function('typeof ToeicMocks!=="undefined"')
                return persistent,current

            persistent,page=persistent_profile()
            page.evaluate("ToeicMocks.start('part5-04')")
            page.locator('[data-tm-answer="0"]').click()
            page.locator('[data-tm-answer="1"]').click()
            page.locator('.tm-question-map summary').click()
            page.locator('[data-tm-question="3"]').click()
            page.locator('[data-tm-answer="2"]').click()
            page.locator('.tm-question-map summary').click()
            page.locator('[data-tm-question="7"]').click()
            page.locator('.tm-question-map summary').click()
            # The native details toggle event persists this UI metadata asynchronously.
            page.wait_for_function('v6Session.toeicMock.mapOpen === document.querySelector(".tm-question-map").open')
            draft=page.evaluate('JSON.parse(JSON.stringify(v6Session))')
            exposure=page.evaluate("localStorage.getItem('toeiclab.questions.exposure.v1')")
            original_events=page.evaluate('JSON.stringify(v6Events)')
            original_observations=page.evaluate('JSON.stringify(__toeicV18.getProfile().observations)')
            original_history=page.evaluate('JSON.stringify(v5History)')
            assert original_events=='[]' and original_observations=='[]' and original_history=='[]'
            assert exposure is not None and draft['index']==7 and len(draft['answers'])==2
            assert draft['toeicMock']['id']=='part5-04'
            persistent.close()
            persistent,page=persistent_profile()
            page.locator('.tm-exam').wait_for()
            reopened=page.evaluate('JSON.parse(JSON.stringify(v6Session))')
            for field in session_fields:assert reopened[field]==draft[field],{'field':field,'expected':draft[field],'actual':reopened[field]}
            assert page.locator('.tm-step strong').inner_text().startswith('Question 108')
            assert page.locator('.tm-question-map').evaluate('e=>e.open')==draft['toeicMock']['mapOpen']
            assert page.evaluate('JSON.stringify(v6Events)')==original_events
            assert page.evaluate('JSON.stringify(__toeicV18.getProfile().observations)')==original_observations
            assert page.evaluate('JSON.stringify(v5History)')==original_history
            assert page.evaluate("localStorage.getItem('toeiclab.questions.exposure.v1')")==exposure
            page.screenshot(path=str(OUT/'module-persistent-reopened.png'))
            report['checks'].append('Complete Brave shutdown/reopen in a temporary persistent profile restores question 108, fixed questions/options, two tentative choices, map metadata and exposure ledger; no marking occurred')

            with page.expect_download() as download:
                page.evaluate('__toeicV18.exportBackup()')
            portable=Path(profile_dir)/'mock-in-progress.json'
            download.value.save_as(portable)
            payload=json.loads(portable.read_text())
            for field in session_fields:assert payload['v6Session'][field]==draft[field],field
            assert payload['v26Exposure']==json.loads(exposure)
            assert payload['v6Events']==[] and payload['v18Profile']['observations']==[]
            persistent.close()

            receiver,imported=fresh()
            imported.on('dialog',lambda dialog:dialog.accept())
            with imported.expect_navigation(wait_until='load'):
                imported.evaluate("payload=>{void __toeicV18.importBackup(new File([JSON.stringify(payload)],'mock-in-progress.json',{type:'application/json'}))}",payload)
            imported.locator('.tm-exam').wait_for()
            restored=imported.evaluate('JSON.parse(JSON.stringify(v6Session))')
            for field in session_fields:assert restored[field]==draft[field],field
            assert imported.evaluate("JSON.parse(localStorage.getItem('toeiclab.questions.exposure.v1'))")==json.loads(exposure)
            assert imported.evaluate('JSON.stringify(v6Events)')==original_events
            assert imported.evaluate('JSON.stringify(__toeicV18.getProfile().observations)')==original_observations
            assert imported.evaluate('JSON.stringify(v5History)')==original_history
            if not imported.locator('[data-tm-question="0"]').is_visible():imported.locator('.tm-question-map summary').click()
            imported.locator('[data-tm-question="0"]').click()
            assert imported.locator('[data-tm-answer="1"]').get_attribute('aria-pressed')=='true'
            imported.locator('.tm-question-map summary').click()
            imported.locator('[data-tm-question="3"]').click()
            assert imported.locator('[data-tm-answer="2"]').get_attribute('aria-pressed')=='true'
            imported.locator('.tm-question-map summary').click()
            imported.locator('[data-tm-question="7"]').click()
            expected_partial_score=sum(draft['answers'].get(q['key'])==q['correct'] for q in draft['items'])
            imported.locator('[data-tm-finish]').click()
            assert imported.locator('#tmSubmit').is_visible()
            assert imported.evaluate('v6Events.length')==0
            imported.locator('[data-tm-submit]').click()
            marked=imported.evaluate('JSON.parse(JSON.stringify(v6ResultCache.r))')
            assert marked['correct']==expected_partial_score and marked['answered']==2 and marked['total']==30
            assert marked['mockTestId']=='part5-04' and marked['mockPart']==5
            assert sum(q['chosen'] is None for q in marked['questions'])==28
            assert imported.evaluate('v6Events.length')==30
            assert imported.evaluate('__toeicV18.getProfile().observations.length')==30
            assert imported.evaluate('v5History.length')==1
            imported.evaluate('v6Finish();v6Finish()')
            assert imported.evaluate('v6Events.length')==30
            assert imported.evaluate('__toeicV18.getProfile().observations.length')==30
            report['portable_mock']={'testId':'part5-04','question':108,'tentative_answers':2,'unanswered':28,'score':expected_partial_score,'total':30,'exposure_preserved':True}
            report['checks'].append('Real JSON export/import with reload restores the in-progress test, options, tentative answers, metadata and v26Exposure; only later confirmation records exactly 30 observations once')
            receiver.close()
        browser.close()
    assert not report['errors'], report['errors']
    report['status']='passed'
    (OUT/'module-resultats.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    server.shutdown()
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    run()
