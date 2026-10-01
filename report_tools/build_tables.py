#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""주도주·후보·관찰군 표 생성. 사용법: python3 build_tables.py <obs_reports.json> <out.json>
state_today.json(오늘)과 state_prev.json(전일)을 /home/claude/jododu 에서 읽는다.
obs_reports.json 예: {"005930":"268,500 <span class=\\"neg\\">-1.47%</span>", "000660":"미확인", "_extra_obs":["003230"], "_extra_label":{"003230":" (9/28 후보 해제)"}, "_close_override":{"005935":[207000,"보도"]}}
"""
import json, sys
D='/home/claude/jododu/'
n=json.load(open(D+'state_today.json',encoding='utf-8'))
import os
_pp=D+'state_prev.json'
PJ=json.load(open(_pp,encoding='utf-8')) if os.path.exists(_pp) else {}
P=PJ.get('stocks',{})
print('PREV_COLLECT', PJ.get('last_collect','없음(전일 대비 미확인)'), 'TODAY_COLLECT', json.load(open(D+'state_today.json',encoding='utf-8')).get('last_collect'), file=sys.stderr)
R=json.load(open(sys.argv[1],encoding='utf-8')) if len(sys.argv)>1 else {}
S=n['stocks']
def g(a,b): return (a/b-1)*100
def pct(v,d=2):
    if v is None: return '미확인'
    if round(v,d)==0: return f'{0:.{d}f}%'
    cls='pos' if v>0 else 'neg'
    return f'<span class="{cls}">{v:+.{d}f}%</span>'
def dt(s): return f'{s[:4]}-{s[4:6]}-{s[6:]}' if s else '-'
def prevc(k):
    ov=R.get('_prev_override',{}).get(k)
    if ov: return ov
    return P.get(k,{}).get('metrics',{}).get('close')
def delta_txt(s):
    d=s.get('delta')
    if not d: return '미확인'
    v=d['verdict']; t=f"{v} ({d['delta_pp']:+.1f}%p)"
    if v=='강한 가속': return f'<span class="pos">{t}</span>'
    if v=='위험': return f'<span class="neg">{t}</span>'
    return t
PREF=['055550','161890','105560','475150','086790','010950','006340','066570','005935','001820','222800','009150']
leaders=[k for k in PREF if k in S and S[k]['status']=='주도주']
leaders+=sorted([k for k,s in S.items() if s['status']=='주도주' and k not in leaders],key=lambda k:(S[k].get('entry_date') or '',k))
rows=[]
for k in leaders:
    s=S[k]; m=s['metrics']; ser=m['series']
    w=[]
    if (m.get('cycle_weeks') or 0)>=52: w.append('52주벽')
    if not m['aligned'] and not m['dc_4_13']: w.append('정배열 이탈')
    if m['dc_4_13']: w.append('4-13DC')
    if m['vol_dc_13_26']: w.append('거래량DC')
    if s.get('delta') and s['delta']['verdict']=='위험': w.append('델타')
    if (m.get('off_peak_pct') or 0)<=-20: w.append('MDD')
    cw=m.get('cycle_weeks'); cw='-' if cw is None else f'{cw}주'
    co=R.get('_close_override',{}).get(k)
    if co:
        close=f'{co[0]:,}'; chg=pct(g(co[0],prevc(k))); off='미확인'; gap='미확인'
    else:
        close=f"{m['close']:,}"; pc=prevc(k); chg=pct(g(m['close'],pc)) if pc else '미확인'
        op=m.get('off_peak_pct'); off=pct(op,1) if op else '0.0%'
        gap=f"<b>{g(ser[0]['m4'],ser[0]['m26']):+.2f}%</b>"
    rows.append(f'<tr><td>{s["name"]}</td><td class="dt">{dt(s.get("entry_date"))}</td><td class="dt">{dt(s.get("judged_date"))}</td><td class="dt">{cw}</td><td class="dt">{close}</td><td class="dt">{chg}</td><td class="dt">{off}</td><td class="dt">{gap}</td><td class="dt">{delta_txt(s)}</td><td class="dt">{"·".join(w) or "없음"}</td></tr>')
lead=f'<h2>주도주 현황 ({len(leaders)}종목)</h2>\n<table>\n<tr><th>종목</th><th>진입일<br>(정배열 형성)</th><th>판정일</th><th>경과</th><th>종가(주봉)</th><th>전일 대비</th><th>공세 고점<br>대비</th><th>4-26주 간격<br>(음수=탈락)</th><th>실적 델타</th><th>경고</th></tr>\n'+'\n'.join(rows)+'\n</table>'
cands=sorted([k for k,s in S.items() if s['status']=='후보'],key=lambda k:(S[k]['metrics'].get('since') or '',S[k].get('judged_date') or '',k))
cr=[]
for k in cands:
    s=S[k]; m=s['metrics']; ser=m['series']; prep=m.get('prep_weeks') or 0
    d=s.get('delta') or {}
    if prep<15:
        why=f'준비기간 {prep}주로 15주 미달'
        wn=(s.get('watch_note') or '')
        if '수급 발작' in wn: why+='. 수급 발작 의심'
        if d.get('verdict')=='강한 가속': why+=f". 실적 델타는 {d['delta_pp']:+.1f}%p [강한 가속]"
    else:
        why='실적 미가속. '+(d.get('desc','미확인').replace(' vs ',' 대 ').replace(' → ',', '))
    op=m.get('off_peak_pct') or 0
    if op<=-20: why+=f'. 공세 고점 대비 {op:.1f}%로 MDD 경고선 하회'
    pc=prevc(k)
    cr.append(f'<tr><td>{s["name"]}</td><td class="dt">{dt(m.get("since"))}</td><td class="dt">{dt(s.get("judged_date"))}</td><td class="dt">{m["close"]:,}</td><td class="dt">{pct(g(m["close"],pc)) if pc else "미확인"}</td><td class="dt">{g(ser[0]["m4"],ser[0]["m26"]):+.2f}%</td><td class="dt">{prep}주</td><td>{why}</td></tr>')
cand=f'<h2>주도주 후보 ({len(cands)}종목)</h2>\n<table>\n<tr><th>종목</th><th>정배열 형성일</th><th>판정일</th><th>종가</th><th>전일 대비</th><th>4-26주 간격</th><th>준비기간</th><th>미충족 사유</th></tr>\n'+'\n'.join(cr)+'\n</table>'
obs_codes=['005930','000660','278470']+R.get('_extra_obs',[])
o=[]
for k in obs_codes:
    s=S[k]; m=s['metrics']; pc=prevc(k)
    a=g(m['ma4'],m['ma26']); b=g(m['ma4'],m['ma13']); op=m.get('off_peak_pct')
    nm=s['name']+R.get('_extra_label',{}).get(k,'')
    o.append(f'<tr><td>{nm}</td><td class="dt">{m["close"]:,}</td><td class="dt">{pct(g(m["close"],pc)) if pc else "미확인"}</td><td class="dt">{R.get(k,"미확인")}</td><td class="dt">{pct(a)}</td><td class="dt">{pct(b)}</td><td class="dt">{pct(op,1) if op else "0.0%"}</td></tr>')
obs='<h2>관찰군</h2>\n<table>\n<tr><th>종목</th><th>종가(수집)</th><th>전일 대비(수집)</th><th>마감 보도</th><th>4-26주 간격</th><th>4-13주 간격</th><th>공세 고점 대비</th></tr>\n'+'\n'.join(o)+'\n</table>'
out=sys.argv[2] if len(sys.argv)>2 else D+'tables.json'
json.dump({'lead':lead,'cand':cand,'obs':obs},open(out,'w',encoding='utf-8'),ensure_ascii=False)
print(lead);print(cand);print(obs)
