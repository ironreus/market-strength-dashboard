#!/usr/bin/env python3
import csv,io,json,os
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.parse import urlencode
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
H={'User-Agent':'market-strength-dashboard/1.0'}
def getj(u):
 r=urlopen(Request(u,headers=H),timeout=20); return json.loads(r.read().decode())
def gettext(u):
 r=urlopen(Request(u,headers=H),timeout=20); return r.read().decode('utf-8','replace')
def fred(s):
 rows=list(csv.reader(io.StringIO(gettext(f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}')))); a=[]
 for row in rows[1:]:
  if len(row)>1 and row[1] not in ('','.'): 
   try:a.append((row[0],float(row[1])))
   except:pass
 if not a: raise RuntimeError(s)
 return {'date':a[-1][0],'value':a[-1][1],'prev':a[-2][1] if len(a)>1 else None,'source':f'FRED:{s}'}
def tga():
 u='https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance?'+urlencode({'fields':'record_date,account_type,open_today_bal','filter':'account_type:eq:Treasury General Account Closing Balance','sort':'-record_date','page[size]':'5'})
 x=getj(u)['data'][0]; raw=float(str(x['open_today_bal']).replace('$','').replace(',','')); return {'date':x['record_date'],'value':raw/1e9,'source':'U.S. Treasury Fiscal Data:DTS'}
def rrp():
 j=getj('https://markets.newyorkfed.org/api/rp/reverserepo/all/results/last/10.json'); found=[]
 def walk(x):
  if isinstance(x,list):
   for y in x:walk(y)
  elif isinstance(x,dict):
   if ('operationDate' in x or 'operation_date' in x) and any(k in x for k in ('totalAmtAccepted','total_amt_accepted','amountAccepted')):found.append(x)
   for y in x.values():walk(y)
 walk(j)
 if not found:raise RuntimeError('RRP format changed')
 x=found[0];raw=x.get('totalAmtAccepted',x.get('total_amt_accepted',x.get('amountAccepted')));return {'date':x.get('operationDate',x.get('operation_date')),'value':float(raw)/1e9,'source':'NY Fed Markets API'}
def btc():
 b=getj('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=krw&include_24hr_change=true')['bitcoin'];return {'date':datetime.now(timezone.utc).date().isoformat(),'value':float(b['krw']),'chg24h':float(b.get('krw_24h_change',0)),'source':'CoinGecko API'}
def score(k,v):
 if k in ('M1','M2','RES'):
  if v.get('prev') is None:return None
  p=(v['value']/v['prev']-1)*100; lim=.3 if k!='RES' else .5; return 2 if p>lim else 1 if p>0 else -2 if p<-lim else -1
 if k=='RRP':x=v['value'];return 2 if x<50 else 1 if x<200 else 0 if x<500 else -1 if x<1000 else -2
 if k=='TGA':x=v['value'];return 2 if x<700 else 1 if x<850 else 0 if x<1000 else -1 if x<1150 else -2
 if k=='Y10':x=v['value'];return 2 if x<3.8 else 1 if x<4.4 else 0 if x<4.8 else -1 if x<5.2 else -2
 if k=='DXY':x=v['value'];return 2 if x<98 else 1 if x<101 else 0 if x<104 else -1 if x<107 else -2
 if k=='BTC':x=v.get('chg24h',0);return 2 if x>3 else 1 if x>0 else 0 if x>-3 else -1 if x>-7 else -2
 return None
def main():
 jobs={'M1':lambda:fred('M1SL'),'M2':lambda:fred('M2SL'),'RES':lambda:fred('WRESBAL'),'Y10':lambda:fred('DGS10'),'DXY':lambda:fred('DTWEXBGS'),'TGA':tga,'RRP':rrp,'BTC':btc}
 out={};errors={}
 for k,f in jobs.items():
  try:
   v=f();v['score']=score(k,v);out[k]=v
  except Exception as e:errors[k]=str(e)
 manual=json.loads((DATA/'manual_overrides.json').read_text()) if (DATA/'manual_overrides.json').exists() else {}
 for k in ('EARN','AI','KOSPI','SENT'):out[k]=manual.get(k,{'score':0,'status':'manual_required'})
 total=sum(int(v.get('score',0) or 0) for v in out.values());now=datetime.now(timezone.utc).isoformat();day=now[:10]
 latest={'generated_at':now,'total':total,'items':out,'errors':errors};(DATA/'latest.json').write_text(json.dumps(latest,ensure_ascii=False,indent=2))
 hp=DATA/'history.json';h=json.loads(hp.read_text()) if hp.exists() else {'history':[]};a=[x for x in h.get('history',[]) if x.get('date')!=day];a.append({'date':day,'total':total,'items':out,'errors':errors});h['history']=sorted(a,key=lambda x:x['date'])[-730:];hp.write_text(json.dumps(h,ensure_ascii=False,indent=2))
 print(f'{day} total={total} errors={list(errors)}')
if __name__=='__main__':main()
