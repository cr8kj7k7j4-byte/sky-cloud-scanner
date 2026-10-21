import time
import requests

UA = "Mozilla/5.0 (compatible; SkyCloudScanner/0.3; +GitHubActions)"

def session():
    s=requests.Session()
    s.headers.update({"User-Agent":UA,"Accept":"application/json,text/plain,*/*"})
    return s

def get_json(url, *, params=None, timeout=20, retries=3, headers=None):
    s=session()
    if headers: s.headers.update(headers)
    last=None
    for i in range(retries):
        try:
            r=s.get(url,params=params,timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last=e
            if i+1<retries: time.sleep(1.2*(i+1))
    raise last
