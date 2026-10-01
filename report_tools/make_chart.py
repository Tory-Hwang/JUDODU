#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""주도주·후보 주봉 40주 패널 차트. 사용법: python3 make_chart.py <수집기준일 YYYY-MM-DD> <출력 png>"""
import sys, json, math, datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter

font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc')
plt.rcParams['font.family']='Noto Sans CJK JP'
plt.rcParams['axes.unicode_minus']=False

COLLECT=sys.argv[1]
OUT=sys.argv[2]
d=json.load(open('/home/claude/jododu/state_today.json',encoding='utf-8'))

def pd(s): return datetime.datetime.strptime(s,'%Y%m%d')
def fd(s): return datetime.datetime.strptime(s.replace('-',''),'%Y%m%d') if s else None

leaders=[s for s in d['stocks'].values() if s['status']=='주도주']
cands=[s for s in d['stocks'].values() if s['status']=='후보']
leaders.sort(key=lambda s: s.get('entry_date') or '9999')
cands.sort(key=lambda s: s['metrics'].get('since') or '99999999')
panels=[('L',s) for s in leaders]+[('C',s) for s in cands]

n=len(panels); cols=2; rows=math.ceil(n/cols)
fig,axes=plt.subplots(rows,cols,figsize=(15,3.45*rows+0.9))
axes=axes.flatten() if n>1 else [axes]
fmt=FuncFormatter(lambda x,_: f'{int(x):,}')

for ax,(kind,s) in zip(axes,panels):
    m=s['metrics']
    ser=list(reversed(m.get('series') or []))[-40:]
    xs=[pd(r['d']) for r in ser]
    ax.plot(xs,[r['c'] for r in ser],color='#9A9A9A',lw=1.0,label='종가')
    ax.plot(xs,[r['m4'] for r in ser],color='#E0322B',lw=1.6,label='4주')
    ax.plot(xs,[r['m13'] for r in ser],color='#F39C12',lw=1.5,label='13주')
    ax.plot(xs,[r['m26'] for r in ser],color='#1F6FC5',lw=1.5,label='26주')
    ax.plot(xs,[r['m52'] for r in ser],color='#6B7B8C',lw=1.4,label='52주')
    name=s['name']
    if kind=='L':
        ed=fd(s.get('entry_date'))
        if ed and xs and ed>=xs[0]:
            ax.axvline(ed,color='#1E7A3C',ls='--',lw=1.1)
            ax.text(ed,ax.get_ylim()[0],' 진입',color='#1E7A3C',fontsize=8,va='bottom')
        if m.get('aligned'):
            cw=m.get('cycle_weeks')
            title=f"{name} · 주도주 {cw if cw is not None else 0}주"; col='#1F3864'
        else:
            title=f"{name} · 정배열 이탈(13<26주선)"; col='#C0392B'
    else:
        sd=fd(m.get('since'))
        if sd and xs and sd>=xs[0]:
            ax.axvline(sd,color='#7A4FA3',ls='--',lw=1.1)
            ax.text(sd,ax.get_ylim()[0],' 정배열',color='#7A4FA3',fontsize=8,va='bottom')
        prep=m.get('prep_weeks') or 0
        why='준비기간 미달' if prep<15 else '델타 관문 미통과'
        title=f"{name} · 후보 ({why})"; col='#7A4FA3'
    ax.set_title(title,loc='left',fontsize=11,color=col,fontweight='bold')
    ax.yaxis.set_major_formatter(fmt)
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.tick_params(labelsize=7.5)
    ax.grid(alpha=0.25)
    ax.legend(loc='upper left',fontsize=7,ncol=2,frameon=True)
for ax in axes[n:]: ax.axis('off')

fig.suptitle(f'주도주·후보 주봉 이동평균 (최근 40주, 4·13·26·52주선) — 수집 {COLLECT}',fontsize=13,fontweight='bold',y=0.995)
fig.tight_layout(rect=[0,0,1,0.985])
fig.savefig(OUT,dpi=110,facecolor='white')
print('saved',OUT,'panels:',n)
