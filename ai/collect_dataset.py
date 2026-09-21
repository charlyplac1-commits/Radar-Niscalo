import csv, json, os, random, re, time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(os.environ.get("DATASET_DIR","ai_dataset"))
POS = ROOT/"positive"; NEG = ROOT/"negative"
ROOT.mkdir(parents=True, exist_ok=True); POS.mkdir(exist_ok=True); NEG.mkdir(exist_ok=True)
UA="Radar-Niscalo-AI/1.1 (public research project; respectful rate limiting)"

def get_json(url, retries=4):
    for attempt in range(retries):
        req=Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
        try:
            with urlopen(req,timeout=30) as r:
                return json.load(r)
        except HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get("Retry-After","0") or 0) or (3 * (attempt + 1))
                print(f"rate limited: {url[:100]}... waiting {wait}s")
                time.sleep(wait)
                continue
            print("request failed", e)
            return {}
        except (URLError, TimeoutError) as e:
            print("request failed", e)
            time.sleep(2 * (attempt + 1))
    print("giving up on request", url)
    return {}

def get_bytes(url, retries=3):
    for attempt in range(retries):
        req=Request(url,headers={"User-Agent":UA})
        try:
            with urlopen(req,timeout=45) as r:
                return r.read()
        except HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get("Retry-After","0") or 0) or (4 * (attempt + 1))
                print(f"download rate limited: waiting {wait}s")
                time.sleep(wait)
                continue
            raise
        except (URLError, TimeoutError):
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("download retries exhausted")

def safe(s): return re.sub(r"[^a-zA-Z0-9._-]+","_",s)[:100]

def save(url,path):
    try:
        data=get_bytes(url)
        if len(data)<5000: return False
        path.write_bytes(data); return True
    except Exception as e:
        print("download failed",url,e); return False

def inat(limit=450):
    rows=[]; page=1
    while len(rows)<limit and page<=8:
        params={"taxon_name":"Lactarius deliciosus","photo_license":"cc0,cc-by,cc-by-sa","per_page":200,"page":page,"order_by":"observed_on","order":"desc"}
        data=get_json("https://api.inaturalist.org/v1/observations?"+urlencode(params))
        for obs in data.get("results",[]):
            for ph in obs.get("photos",[]):
                lic=(ph.get("license_code") or "").lower()
                if lic not in ("cc0","cc-by","cc-by-sa"): continue
                url=ph.get("url")
                if not url: continue
                name=f"inat_{obs.get('id')}_{ph.get('id')}.jpg"; p=POS/safe(name)
                if not p.exists() and save(url,p):
                    geo=obs.get("geojson",{}).get("coordinates",[None,None])
                    rows.append({"file":str(p),"label":"niscalo","source":"iNaturalist","observation_id":obs.get("id"),"photo_id":ph.get("id"),"author":obs.get("user",{}).get("login"),"license":lic,"source_url":f"https://www.inaturalist.org/observations/{obs.get('id')}","observed_on":obs.get("observed_on"),"lat":geo[1] if len(geo)>1 else None,"lon":geo[0] if len(geo)>0 else None})
                if len(rows)>=limit: break
            if len(rows)>=limit: break
        page+=1
        if not data.get("results"): break
        time.sleep(1.0)
    return rows

def commons_search(search,limit):
    out=[]; cont={}
    while len(out)<limit:
        params={"action":"query","format":"json","generator":"search","gsrsearch":search,"gsrnamespace":6,"gsrlimit":30,"prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":640}
        params.update(cont)
        data=get_json("https://commons.wikimedia.org/w/api.php?"+urlencode(params))
        if not data:
            print("Commons search temporarily unavailable; moving to next negative query.")
            break
        for page in data.get("query",{}).get("pages",{}).values():
            ii=(page.get("imageinfo") or [{}])[0]; meta=ii.get("extmetadata",{})
            lic=(meta.get("LicenseShortName",{}).get("value") or "").lower()
            if not any(x in lic for x in ("cc0","cc by","cc-by")): continue
            url=ii.get("thumburl") or ii.get("url")
            if not url: continue
            p=NEG/safe("commons_"+str(page.get("pageid"))+".jpg")
            if not p.exists() and save(url,p):
                out.append({"file":str(p),"label":"no_niscalo","source":"Wikimedia Commons","page_id":page.get("pageid"),"author":meta.get("Artist",{}).get("value"),"license":lic,"source_url":"https://commons.wikimedia.org/wiki/"+page.get("title","").replace(" ","_")})
            if len(out)>=limit: break
        if len(out)>=limit or "continue" not in data: break
        cont=data["continue"]; time.sleep(1.5)
    return out

if __name__=="__main__":
    pos=inat(int(os.environ.get("POSITIVE_LIMIT","450")))
    neg=[]
    target=int(os.environ.get("NEGATIVE_LIMIT","450"))
    for q in ("pine forest -mushroom","forest floor pine needles -mushroom","pine woodland -mushroom"):
        neg += commons_search(q,max(0,target-len(neg)))
        if len(neg)>=target: break
    rows=pos+neg; random.Random(42).shuffle(rows)
    fields=sorted({k for r in rows for k in r})
    with open(ROOT/"manifest.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    (ROOT/"stats.json").write_text(json.dumps({"positive":len(pos),"negative":len(neg),"total":len(rows)},ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"positive":len(pos),"negative":len(neg),"total":len(rows)}))
