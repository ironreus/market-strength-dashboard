import json,csv,io,os,datetime,urllib.request

ROOT=os.path.dirname(os.path.dirname(__file__)); DATA=os.path.join(ROOT,"data"); os.makedirs(DATA,exist_ok=True)
UA={"User-Agent":"market-strength-dashboard/2.0"}; TODAY=datetime.datetime.now(datetime.timezone.utc).astimezone().date().isoformat()
def get(u):
    r=urllib.request.Request(u,headers=UA)
    with urllib.request.urlopen(r,timeout=20) as x:return x.read().decode()
def fred(s):
    rows=list(csv.DictReader(io.StringIO(get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}"))))
    rows=[r for r in rows if r.get(s) not in ("",".")]; r=rows[-1]; return float(r[s]),r["DATE"]
def prev(k):
    try:
        h=json.load(open(os.path.join(DATA,"history.json"),encoding="utf8"))
        a=[r["metrics"][k]["numeric"] for r in h["records"] if k in r["metrics"] and isinstance(r["metrics"][k].get("numeric"),(int,float))]
        return a[-1] if a else None
    except:return None
def mk(name,value,score,trend,reason,obs,num=None):
    d={"name":name,"value":value,"score":max(-2,min(2,int(score))),"trend":trend,"reason":reason,"obs_date":obs}
    if num is not None:d["numeric"]=num
    return d
def sc(v,o,down=False):
    if o is None:return 0
    z=(v-o)/max(abs(o),1e-9)
    if down:z=-z
    return 2 if z>.05 else 1 if z>.01 else -2 if z<-.05 else -1 if z<-.01 else 0

out={}; errors=[]
for k,s,n,down in [("M1","M1SL","M1",False),("M2","M2SL","M2",False),("RES","WRESBAL","Reserve Balances",False),("Y10","DGS10","미국 10년물 금리",True),("DXY","DTWEXBGS","달러지수(DXY 대용)",False)]:
    try:
        v,o=fred(s); p=prev(k); out[k]=mk(n,f"{v:,.3f}",sc(v,p,down),"상승" if not p or v>p else "하락","직전 저장값 대비 변화",o,v)
    except Exception as e: errors.append(k+":"+str(e))
try:
    d=json.loads(get("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance?sort=-record_date&page%5Bsize%5D=1"))
    r=d["data"][0]; v=float(r.get("close_today_bal") or r.get("accounting_period_amount")); o=r["record_date"]; p=prev("TGA"); out["TGA"]=mk("TGA",f"{v:,.0f}백만달러",sc(v,p,True),"하락" if p and v<p else "상승","TGA 감소를 유동성에 우호적으로 해석",o,v)
except Exception as e: errors.append("TGA:"+str(e))
try:
    d=json.loads(get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=krw&include_24hr_change=true")); v=float(d["bitcoin"]["krw"]); c=float(d["bitcoin"]["krw_24h_change"]); out["BTC"]=mk("비트코인 사이클",f"{v:,.0f}원",2 if c>3 else 1 if c>.5 else -2 if c<-3 else -1 if c<-.5 else 0,"24시간 "+("상승" if c>0 else "하락"),"24시간 가격 변화 보조점수",TODAY,v)
except Exception as e: errors.append("BTC:"+str(e))
try:
    d=json.loads(get("https://markets.newyorkfed.org/api/rp/reverserepo/propositions/search.json?startDate=2000-01-01&endDate="+TODAY)); a=d.get("refRateData",d.get("data",[])); r=a[-1]; v=float(r.get("totalAmtOutstanding",r.get("total_amount",0))); o=r.get("effectiveDate",TODAY); p=prev("RRP"); out["RRP"]=mk("RRP",f"{v:,.0f}",sc(v,p,True),"하락" if p and v<p else "상승","RRP 감소를 유동성에 우호적으로 해석",o,v)
except Exception as e: errors.append("RRP:"+str(e))
try:
    d=json.loads(get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata")); x=d.get("fear_and_greed",{}); v=x.get("score"); 
    if v is None: raise ValueError("CNN score 없음")
    sent=[float(v)]
except Exception as e: errors.append("CNN:"+str(e)); sent=[]
try:
    d=json.loads(get("https://api.coinmarketcap.com/data-api/v3/fear-greed/latest")); v=d.get("data",{}).get("value")
    if v is not None: sent.append(float(v))
except Exception as e: errors.append("CMC:"+str(e))
if sent:
    v=sum(sent)/len(sent); out["SENT"]=mk("시장심리",f"{v:.1f}/100",2 if v>=75 else 1 if v>=55 else -2 if v<25 else -1 if v<45 else 0,"탐욕" if v>=55 else "공포" if v<45 else "중립","CNN·CoinMarketCap 공포탐욕지수 평균",TODAY,v)
try:
    man=json.load(open(os.path.join(DATA,"manual_overrides.json"),encoding="utf8"))
    for k,n in [("EARN","기업실적"),("AI","AI 투자 사이클"),("KOSPI","외국인 코스피 순매수")]:
        x=man.get(k,{}); out[k]=mk(n,x.get("value","수동 입력"),x.get("score",0),"수동",x.get("reason","수동 입력"),x.get("obs_date",TODAY))
except Exception as e: errors.append("MANUAL:"+str(e))
try: old=json.load(open(os.path.join(DATA,"latest.json"),encoding="utf8"))["record"]["metrics"]
except: old={}
for k,n in [("M1","M1"),("M2","M2"),("RRP","RRP"),("TGA","TGA"),("RES","Reserve Balances"),("EARN","기업실적"),("AI","AI 투자 사이클"),("BTC","비트코인 사이클"),("Y10","미국 10년물 금리"),("DXY","달러지수(DXY 대용)"),("KOSPI","외국인 코스피 순매수"),("SENT","시장심리")]:
    if k not in out: out[k]=old.get(k,mk(n,"수집 실패",0,"-","데이터 수집 실패","-"))
total=sum(x.get("score",0) for x in out.values()); rec={"date":TODAY,"total":total,"metrics":out,"errors":errors}
json.dump({"generated_at":datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds"),"record":rec},open(os.path.join(DATA,"latest.json"),"w",encoding="utf8"),ensure_ascii=False,indent=2)
try:h=json.load(open(os.path.join(DATA,"history.json"),encoding="utf8"))
except:h={"records":[]}
h["records"]=[r for r in h["records"] if r["date"]!=TODAY]+[rec]; h["records"]=h["records"][-370:]
json.dump(h,open(os.path.join(DATA,"history.json"),"w",encoding="utf8"),ensure_ascii=False,indent=2)
print("score",total,"errors",len(errors))
