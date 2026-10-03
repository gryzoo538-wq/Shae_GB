#!/usr/bin/env python3
"""Mock Google Business Profile API (v4 subset) + Lantern & Loaf reply gateway.
Run:  python3 mock_gbp/server.py --phase 1   (default port 8765)
Auth: header  Authorization: Bearer ll-test-token
Treat this as a black box: interact with it over HTTP only."""
import json, zlib, base64, re, time, sys, os, argparse, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
HERE=os.path.dirname(os.path.abspath(__file__))
FIX=json.loads(zlib.decompress(base64.b64decode(open(os.path.join(HERE,"fixtures.bin")).read())))
STATE_FILE=os.path.join(HERE,"state.json")
ap=argparse.ArgumentParser(); ap.add_argument("--phase",type=int,default=1); ap.add_argument("--port",type=int,default=8765)
ARGS=ap.parse_args(); PHASE=ARGS.phase
LOCK=threading.Lock(); HITS=[]
def load_state():
    try: return json.load(open(STATE_FILE))
    except Exception: return {"replies":{}}
def save_state(s): json.dump(s,open(STATE_FILE,"w"),indent=1)
def reviews(loc):
    st=load_state(); out=[]
    for r in FIX["reviews"]:
        if r["loc"]!=loc or r["phase"]>PHASE or PHASE in r["gone_in"]: continue
        x={k:r[k] for k in ["name","reviewId","reviewer","starRating","comment","createTime","updateTime"] if k in r}
        for e in r["edits"]:
            if e["phase"]<=PHASE: x.update(comment=e["comment"],starRating=e["starRating"],updateTime=e["updateTime"])
        rep=st["replies"].get(r["reviewId"], r.get("reviewReply"))
        if rep: x["reviewReply"]=rep
        out.append(x)
    out.sort(key=lambda x:x["updateTime"],reverse=True); return out
STARS={"ONE":1,"TWO":2,"THREE":3,"FOUR":4,"FIVE":5}
CONTACT=re.compile(r"(https?://|www\.|\b[\w.-]+\.(com|net|org|test|io)\b|@|\+?\d[\d\s().-]{6,}\d)",re.I)
class H(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def send(self,code,obj,extra=None):
        b=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(code)
        self.send_header("Content-Type","application/json; charset=utf-8")
        for k,v in (extra or {}).items(): self.send_header(k,v)
        self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def auth(self):
        if self.headers.get("Authorization")!="Bearer ll-test-token":
            self.send(401,{"error":{"code":401,"status":"UNAUTHENTICATED"}}); return False
        return True
    def route(self):
        p=urlparse(self.path); parts=p.path.strip("/").split("/"); return p,parts
    def do_GET(self):
        if not self.auth(): return
        p,parts=self.route(); q=parse_qs(p.query)
        if parts[:4]==["v4","accounts","118","locations"] and len(parts)==4:
            return self.send(200,{"locations":[{"name":f"accounts/118/locations/{l['id']}","locationName":l["title"]} for l in FIX["locations"]]})
        if len(parts)>=6 and parts[:4]==["v4","accounts","118","locations"] and parts[5]=="reviews":
            loc=parts[4]
            if loc not in [l["id"] for l in FIX["locations"]]: return self.send(404,{"error":{"code":404,"status":"NOT_FOUND"}})
            rs=reviews(loc)
            if len(parts)==7:
                m=[r for r in rs if r["reviewId"]==parts[6]]
                return self.send(200,m[0]) if m else self.send(404,{"error":{"code":404,"status":"NOT_FOUND"}})
            size=min(int(q.get("pageSize",["10"])[0]),10); off=int(base64.b64decode(q.get("pageToken",["MA=="])[0]).decode() or 0)
            page=rs[off:off+size]; body={"reviews":page,"averageRating":round(sum(STARS[r["starRating"]] for r in rs)/len(rs),1),"totalReviewCount":len(rs)}
            if off+size<len(rs): body["nextPageToken"]=base64.b64encode(str(off+size).encode()).decode()
            return self.send(200,body)
        self.send(404,{"error":{"code":404,"status":"NOT_FOUND"}})
    def target(self):
        p,parts=self.route()
        if len(parts)==8 and parts[:4]==["v4","accounts","118","locations"] and parts[5]=="reviews" and parts[7]=="reply":
            return parts[4],parts[6]
        return None,None
    def do_PUT(self):
        if not self.auth(): return
        loc,rid=self.target()
        if not loc: return self.send(404,{"error":{"code":404,"status":"NOT_FOUND"}})
        with LOCK:
            now=time.time(); HITS[:]=[t for t in HITS if now-t<10]
            if len(HITS)>=5: return self.send(429,{"error":{"code":429,"status":"RESOURCE_EXHAUSTED"}},{"Retry-After":"3"})
            HITS.append(now)
        try: body=json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))) or b"{}"); c=body["comment"]
        except Exception: return self.send(400,{"error":{"code":400,"status":"INVALID_ARGUMENT","message":"body must be {\"comment\": string}"}})
        rs=reviews(loc); m=[r for r in rs if r["reviewId"]==rid]
        fx=[r for r in FIX["reviews"] if r["reviewId"]==rid]
        if not m or (fx and PHASE in fx[0]["deleted_for_put"]):
            return self.send(404,{"error":{"code":404,"status":"NOT_FOUND","message":"Review not found. It may have been removed."}})
        title=[l["title"] for l in FIX["locations"] if l["id"]==loc][0].split("–")[-1].strip()
        errs=[]
        if not c.strip(): errs.append("EMPTY_REPLY")
        if len(c)>350: errs.append("TOO_LONG: max 350 characters (got %d)"%len(c))
        if CONTACT.search(c): errs.append("CONTACT_INFO: replies may not contain links, emails or phone numbers")
        if title.lower() not in c.lower(): errs.append(f"MISSING_LOCATION: reply must mention '{title}'")
        if errs: return self.send(400,{"error":{"code":400,"status":"FAILED_PRECONDITION","details":errs}})
        st=load_state()
        others=[r.get("reviewReply",{}).get("comment","") for r in reviews("4471")+reviews("4472") if r["reviewId"]!=rid]
        if c.strip() in [o.strip() for o in others]:
            return self.send(409,{"error":{"code":409,"status":"ALREADY_EXISTS","message":"Identical reply text already used on another review"}})
        rep={"comment":c,"updateTime":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
        st["replies"][rid]=rep; save_state(st); self.send(200,rep)
    def do_DELETE(self):
        if not self.auth(): return
        loc,rid=self.target(); st=load_state()
        if not loc: return self.send(404,{"error":{"code":404,"status":"NOT_FOUND"}})
        st["replies"][rid]=None; save_state(st); self.send(200,{})
print(f"Mock GBP API phase {PHASE} on http://127.0.0.1:{ARGS.port}",flush=True)
ThreadingHTTPServer(("127.0.0.1",ARGS.port),H).serve_forever()
