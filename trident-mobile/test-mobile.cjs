"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const html = fs.readFileSync("trident-mobile/index.html","utf8");
const script = html.match(/<script>([\s\S]*?)<\/script>/);
assert(script, "inline script exists");
const nodes = new Map();
const node = (id) => {
  if(!nodes.has(id)) nodes.set(id, {value:"",textContent:"",innerHTML:"",className:"",files:[], dataset:{}, classList:{toggle() {}}});
  return nodes.get(id);
};
const storage = new Map();
const localStorage = {getItem:k=>storage.get(k)??null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)};
const document = {getElementById:node,querySelectorAll:()=>[]};
const context = vm.createContext({document,localStorage,Date,Number,String,Math,JSON,RegExp,Array,Object,
  setInterval:()=>0,scrollTo:()=>{},alert:()=>{},confirm:()=>false});
vm.runInContext(script[1],context,{filename:"trident-inline.js"});
const evalJS = (code)=>vm.runInContext(code,context);
function inputs({side="LONG",entry=50,stop=49,target=53,shares=1000,fees=".45"}={}) {
  Object.entries({side,entry,stop,target,shares,fees}).forEach(([k,v])=>node(k).value=String(v));
}
inputs();
let r=evalJS("calc()");
assert(r.loss>0 && r.gain>0 && r.rr>0);
assert(r.loss<=5000);
assert.equal(r.allowed, Math.floor(5000/(Math.abs(r.entry-r.stop)+r.entry*r.fee)));
inputs({side:"SHORT",entry:50,stop:51,target:47});
r=evalJS("calc()");
assert(r.loss>0 && r.gain>0);
inputs({side:"SHORT",entry:50,stop:49,target:47});
assert.throws(()=>evalJS("calc()"),/不合法/);
inputs({shares:0});
assert.throws(()=>evalJS("calc()"),/不合法/);
inputs({side:"INVALID",entry:50,stop:49,target:53,shares:1000});
assert.throws(()=>evalJS("calc()"),/方向不合法/);
inputs({side:"LONG",entry:1e308,stop:1e307,target:1.7e308,shares:1000,fees:".45"});
assert.throws(()=>evalJS("calc()"),/安全數值範圍/);
node("symbol").value="2330";
evalJS("recordTrade()");
assert.equal(evalJS("positions.length"),0,"overflow must never create a trade plan");
inputs({entry:50,stop:49,target:53,shares:1000});
assert.equal(evalJS("validFeed({as_of:'2026-11-07T09:05:00+08:00',source:'test',signals:[{symbol:'2330',side:'WATCH'}]})"),true);
assert.equal(evalJS("validFeed({as_of:'invalid',source:'test',signals:[]})"),false);
assert.equal(evalJS("validFeed({as_of:'2026-11-07T09:05:00+08:00',source:'test',signals:[{symbol:'2330',side:'AUTO_BUY'}]})"),false);
assert.equal(node("decision").textContent,"");
assert.equal(html.includes('id="decision">NO TRADE'),true);
assert.equal(html.includes("沒有自動下單功能"),true);
// A user-imported source and claimed coverage are never server-authenticated.
assert.equal(html.includes('el("feedBadge").className="tag warn";'),true,
  "Imported feed must not display a green/verified status");
assert.equal(html.includes('未驗證（匯入宣稱：'),true,
  "Claimed market coverage must be visibly marked unverified");
assert.equal(html.includes('id="tradeBadge">交易訊號停用'),true,
  "Real trading signals remain disabled");
assert.equal(html.includes('id="decision">NO TRADE'),true,
  "Unvalidated model output must fail closed");
console.log("TRIDENT behavioral smoke tests passed");
