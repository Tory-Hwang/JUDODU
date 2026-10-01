#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""daily_report.html 배포 전 자동 검증. 실패 시 exit 1."""
import sys, re, asyncio, datetime, glob, os
from playwright.async_api import async_playwright

P='/home/claude/jododu/daily_report.html'
errs=[]
h=open(P,encoding='utf-8').read()

# 1) 치환 안 된 플레이스홀더
for ph in re.findall(r'\[\[[A-Z_]+\]\]', h):
    errs.append(f'치환 안 된 플레이스홀더: {ph}')

# 2) data URI 접두어 중복
if 'base64,data:' in h:
    errs.append('data URI 접두어 중복 (base64,data:)')

# 3) 금칙어 (푸터 내부 명칭 노출)
for w in ('JUDODU','jododu','state.json','state_today'):
    if w in h:
        errs.append(f'금칙어 노출: {w}')

# 4) 날짜 정합성 — 리포트 제목 날짜가 오늘(KST)인지
kst=datetime.datetime.utcnow()+datetime.timedelta(hours=9)
today=kst.strftime('%Y-%m-%d')
if today not in h and kst.strftime('%Y.%m.%d') not in h and kst.strftime('%-m월 %-d일') not in h:
    errs.append(f'본문에 오늘 날짜({today}) 표기가 없음 — 날짜 확인 필요')

# 5) 브라우저 렌더 검증
async def render():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        pg=await b.new_page(viewport={'width':1000,'height':1400})
        await pg.goto('file://'+P)
        imgs=await pg.query_selector_all('img')
        if not imgs: errs.append('img 태그가 하나도 없음')
        for i,el in enumerate(imgs):
            nw=await el.evaluate('e=>e.naturalWidth')
            if not nw: errs.append(f'이미지 #{i+1} 로딩 실패 (naturalWidth=0)')
        over=await pg.evaluate("""() => {
          const bad=[];
          document.querySelectorAll('td.dt, th').forEach(e=>{
            const t=(e.innerText||'').trim();
            if(!t) return;
            if(e.innerHTML.includes('<br')) return;
            const r=document.createRange(); r.selectNodeContents(e);
            const rects=Array.from(r.getClientRects()).filter(x=>x.height>1&&x.width>1);
            if(rects.length<2) return;
            const tops=new Set(rects.map(x=>Math.round(x.top)));
            if(tops.size>1) bad.push(t);
          });
          return bad.slice(0,8);
        }""")
        for t in over: errs.append(f'날짜/숫자 셀 줄바꿈 발생: "{t}"')
        await pg.screenshot(path='/home/claude/jododu/_verify.png', full_page=False)
        await b.close()
asyncio.run(render())

# ── 6~11) 본문 파일 기준 검사 (면책 블록은 어미 계수에서 제외)
BODY=f'/home/claude/jododu/report_body_{kst.strftime("%Y%m%d")}.html'
if os.path.exists(BODY):
    b=open(BODY,encoding='utf-8').read()
    nodisc=re.sub(r'<div class="disclaimer">.*?</div>','',b,flags=re.S)
    txt=re.sub(r'<[^>]+>','',nodisc)

    # 6) 줄표는 제목(h3/굵은 라벨) 한정에만
    if txt.count('—') != len(re.findall(r'(?:<h3>|<b>)[^<]*—', b)):
        errs.append('줄표(—)가 제목 한정 외의 위치에 사용됨')

    # 7) 대화 잔재·구어 어미
    for w in ('짧게','나머지','적어 둔','기억해 둘','밝혀 둔','함께 적','이어서 살펴','간밤'):
        if w in txt: errs.append(f'금지 표현: "{w}"')
    for w in ('됐','했다','했고','했으나','합니다','습니다'):
        if w in txt: errs.append(f'구어 어미: "{w}"')

    # 8) 운영·점검성 내용 (리포트 비게재 항목)
    for w in ('젯슨','수집 로그','수집 불일치','배포 지연','주 전환 효과의 포트폴리오'):
        if w in txt: errs.append(f'운영성 내용은 리포트에 넣지 않음: "{w}"')

    # 9) 해설 박스는 굵은 도입구 목록 형식 (<br> 나열 금지)
    for m in re.finditer(r'<div class="(card|warnbox|notice)">(.*?)</div>', b, re.S):
        inner=m.group(2)
        if '<ul>' not in inner and inner.count('<br>')>=2:
            errs.append(f'{m.group(1)} 박스가 <br> 나열임 — <ul><li>+굵은 도입구로 작성')

    # 10) 미국 증시 표의 최근 거래일 열이 전부 미확인인지
    us=re.search(r'<h2>미국 증시.*?</table>', b, re.S)
    if us:
        rows=re.findall(r'<tr><td class="dt">.*?</tr>', us.group(0))
        recent=[r.split('</td>')[2] for r in rows if r.count('</td>')>=3]
        if recent and all('미확인' in c for c in recent):
            errs.append('미국 증시 최근 거래일 열이 전부 미확인 — AP 확정표 완전일치 재검색과 미러 순회를 먼저 수행')

    # 11) 직전 리포트와 구조 대조 (참고 출력)
    prev=sorted(glob.glob('/home/claude/jododu/report_body_*.html'))
    prev=[f for f in prev if f<BODY]
    if prev:
        pb=open(prev[-1],encoding='utf-8').read()
        cur_h2=re.findall(r'<h2>([^<]+)</h2>', b)
        pre_h2=re.findall(r'<h2>([^<]+)</h2>', pb)
        if cur_h2!=pre_h2:
            print('ℹ️ 직전 리포트와 섹션 구성이 다름 (의도한 변경인지 확인)')
            print('   직전:', ' / '.join(pre_h2))
            print('   오늘:', ' / '.join(cur_h2))

if errs:
    print('❌ 검증 실패')
    for e in errs: print('  -', e)
    sys.exit(1)
print('✅ 검증 통과 — 이미지 로딩·플레이스홀더·날짜·표 레이아웃 이상 없음')
