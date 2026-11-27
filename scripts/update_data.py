import json, csv, io, os, datetime, time, urllib.request, urllib.error

ROOT=os.path.dirname(os.path.dirname(__file__))
DATA=os.path.join(ROOT,"data")
os.makedirs(DATA,exist_ok=True)

UA={"User-Agent":"Mozilla/5.0 (market-strength-dashboard; +https://github.com/ironreus/market-strength-dashboard)"}
TODAY=datetime.datetime.now(datetime.timezone.utc).astimezone().date().isoformat()

def get(url, timeout=60, tries=3):
    last=None
    for i in range(tries):
        try:
            req=urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8")
        except Exception as e:
            last=e
            if i < tries-1:
                time.sleep(2*(i+1))
    raise last

def fred(series):
    url=f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd=2000-01-01"
    rows=list(csv.DictReader(io.StringIO(get(url))))
    rows=[r for r in rows if r.get(series) not in ("",".",None)]
    if not rows: raise ValueError(f"FRED {series} empty")
    r=rows[-1]
    return float(r[series]), r["DATE"]

def load_json(path, default):
    try:
        with open(path,encoding="utf-8") as f:return json.load(f)
    except:return default

def prev(k):
    h=load_json(os.path.join(DATA,"history.json"),{"records":[]})
    a=[r["metrics"][k]["numeric"] for r in h["records"]
       if k in r.get("metrics",{}) and isinstance(r["metrics"][k].get("numeric"),(int,float))]
    return a[-1] if a else None

def mk(name,value,score,trend,reason,obs,num=None):
    d={"name":name,"value":value,"score":max(-2,min(2,int(score))),
       "trend":trend,"reason":reason,"obs_date":obs}
    if num is not None:d["numeric"]=num
    return d

def sc(v,o,down=False):
    if o is None:return 0
    z=(v-o)/max(abs(o),1e-9)
    if down:z=-z
    return 2 if z>.05 else 1 if z>.01 else -2 if z<-.05 else -1 if z<-.01 else 0

out={}; errors=[]

for k,s,n,down in [
    ("M1","M1SL","M1",False),("M2","M2SL","M2",False),
    ("RES","WRESBAL","Reserve Balances",False),
    ("Y10","DGS10","미국 10년물 금리",True),
    ("DXY","DTWEXBGS","달러지수(DXY 대용)",False)
]:
    try:
        v,o=fred(s); p=prev(k)
        out[k]=mk(n,f"{v:,.3f}",sc(v,p,down),"상승" if not p or v>p else "하락",
                  "직전 저장값 대비 변화",o,v)
    except Exception as e: errors.append(k+":"+str(e))

# TGA: the API's close_today_bal is intentionally null in current DTS structure.
# Use the row named "Treasury General Account (TGA) Closing Balance"
# and its open_today_bal field instead.
try:
    u=("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/"
       "accounting/dts/operating_cash_balance?sort=-record_date&page%5Bsize%5D=100")
    d=json.loads(get(u))
    rows=d.get("data",[])
    rows=[r for r in rows if "Treasury General Account (TGA) Closing Balance" in str(r.get("account_type",""))
          and r.get("open_today_bal") not in (None,"null","")]
    if not rows: raise ValueError("TGA closing-balance row not found")
    r=rows[0]; v=float(str(r["open_today_bal"]).replace(",","").replace("$",""))
    o=r["record_date"]; p=prev("TGA")
    out["TGA"]=mk("TGA",f"{v:,.0f}백만달러",sc(v,p,True),
                  "하락" if p and v<p else "상승","TGA 감소를 유동성에 우호적으로 해석",o,v)
except Exception as e: errors.append("TGA:"+str(e))

# BTC
try:
    d=json.loads(get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=krw&include_24hr_change=true"))
    v=float(d["bitcoin"]["krw"]); c=float(d["bitcoin"]["krw_24h_change"])
    out["BTC"]=mk("비트코인 사이클",f"{v:,.0f}원",
                  2 if c>3 else 1 if c>.5 else -2 if c<-3 else -1 if c<-.5 else 0,
                  "24시간 "+("상승" if c>0 else "하락"),"24시간 가격 변화 보조점수",TODAY,v)
except Exception as e: errors.append("BTC:"+str(e))

# NY Fed RRP: try the current markets API shape first, then preserve previous value if unavailable.
try:
    u=("https://markets.newyorkfed.org/api/rp/reverserepo/propositions/search.json"
       f"?startDate=2020-01-01&endDate={TODAY}")
    d=json.loads(get(u))
    rows=d.get("refRateData") or d.get("data") or []
    rows=[r for r in rows if r.get("effectiveDate") or r.get("operationDate")]
    if not rows: raise ValueError("RRP rows not found")
    r=rows[-1]
    raw=r.get("totalAmtOutstanding",r.get("total_amount",r.get("totalAmount")))
    if raw is None: raise ValueError("RRP amount field not found")
    v=float(raw); o=r.get("effectiveDate",r.get("operationDate",TODAY)); p=prev("RRP")
    out["RRP"]=mk("RRP",f"{v:,.0f}",sc(v,p,True),
                  "하락" if p and v<p else "상승","RRP 감소를 유동성에 우호적으로 해석",o,v)
except Exception as e: errors.append("RRP:"+str(e))

# Market sentiment: use CNN if available, otherwise Alternative.me as a stable fallback.
sent=[]
try:
    d=json.loads(get("https://production.dataviz.cnn.io/index/fearandgreed/graphdata"))
    v=d.get("fear_and_greed",{}).get("score")
    if v is not None:sent.append(("CNN",float(v)))
except Exception as e: errors.append("CNN:"+str(e))
try:
    d=json.loads(get("https://api.alternative.me/fng/?limit=1"))
    v=d.get("data",[{}])[0].get("value")
    if v is not None:sent.append(("Alternative.me",float(v)))
except Exception as e: errors.append("FNG:"+str(e))
if sent:
    v=sum(x[1] for x in sent)/len(sent)
    out["SENT"]=mk("시장심리",f"{v:.1f}/100",
                   2 if v>=75 else 1 if v>=55 else -2 if v<25 else -1 if v<45 else 0,
                   "탐욕" if v>=55 else "공포" if v<45 else "중립",
                   "CNN·Alternative.me 공포탐욕지수 평균(가용 데이터 기준)",TODAY,v)

# Manual inputs
try:
    man=load_json(os.path.join(DATA,"manual_overrides.json"),{})
    for k,n in [("EARN","기업실적"),("AI","AI 투자 사이클"),("KOSPI","외국인 코스피 순매수")]:
        x=man.get(k,{})
        out[k]=mk(n,x.get("value","수동 입력"),x.get("score",0),"수동",
                  x.get("reason","수동 입력"),x.get("obs_date",TODAY))
except Exception as e: errors.append("MANUAL:"+str(e))

old=load_json(os.path.join(DATA,"latest.json"),{}).get("record",{}).get("metrics",{})
names=[("M1","M1"),("M2","M2"),("RRP","RRP"),("TGA","TGA"),
       ("RES","Reserve Balances"),("EARN","기업실적"),("AI","AI 투자 사이클"),
       ("BTC","비트코인 사이클"),("Y10","미국 10년물 금리"),
       ("DXY","달러지수(DXY 대용)"),("KOSPI","외국인 코스피 순매수"),("SENT","시장심리")]
for k,n in names:
    if k not in out:
        out[k]=old.get(k,mk(n,"수집 실패",0,"-","데이터 수집 실패","-"))

total=sum(x.get("score",0) for x in out.values())
rec={"date":TODAY,"total":total,"metrics":out,"errors":errors}
now=datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds")

json.dump({"generated_at":now,"record":rec},
          open(os.path.join(DATA,"latest.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)

h=load_json(os.path.join(DATA,"history.json"),{"records":[]})
h["records"]=[r for r in h["records"] if r["date"]!=TODAY]+[rec]
h["records"]=h["records"][-370:]
json.dump(h,open(os.path.join(DATA,"history.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)

print("score",total,"errors",len(errors))
for e in errors: print("WARN",e)
