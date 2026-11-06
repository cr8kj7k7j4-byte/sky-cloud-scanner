"use strict";
const fs=require("node:fs");
const vm=require("node:vm");
const assert=require("node:assert/strict");
const html=fs.readFileSync("trident-mobile/index.html","utf8");
const match=html.match(/<script>([\\s\\S]*?)<\\/script>/);
assert(match,"inline JavaScript must exist");
const elements=new Map();
const get=id=>{if(!elements.has(id))elements.set(id,{value:"",textContent:"",innerHTML:"",className:"",files:[]});return elements.get(id)};
const storage=new Map();
const context={console,Date,JSON,Math,Number,String,Array,Object,RegExp,Error,parseFloat,parseInt,
document:{getElementById:get,querySelectorAll:()=>[]},
localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},
setInterval:()=>{},alert:()=>{},confirm:()=>true,scrollTo:()=>{}};
vm.createContext(context);
vm.runInContext(match[1],context,{timeout:2000});
const test=(code)=>vm.runInContext(code,context,{timeout:2000});
const sample={as_of:"2026-11-09T09:05:00+08:00",source:"licensed-data",signals:[{symbol:"2330",side:"WATCH",entry:0,stop:0,target:0}]};
assert.equal(context.validFeed(sample),true,"valid snapshot");
assert.equal(context.validFeed({...sample,as_of:"2026-11-09T09:05:00"}),false,"reject timezone-less timestamps");
assert.equal(context.validFeed({...sample,source:""}),false,"reject missing source");
assert.equal(context.validFeed({...sample,signals:[{symbol:"<script>",side:"WATCH"}]}),false,"reject invalid ticker");
assert.equal(context.validFeed({...sample,signals:[{symbol:"2330",side:"BUY"}]}),false,"reject unrecognized side");
const set=(side,entry,stop,target,shares,fees)=>{get("side").value=side;get("entry").value=String(entry);get("stop").value=String(stop);get("target").value=String(target);get("shares").value=String(shares);get("fees").value=String(fees)};
set("LONG",50,49,53,1000,0.45);
let x=context.calc();assert(Math.abs(x.loss-1225)<0.001);assert(Math.abs(x.gain-2775)<0.001);assert(x.rr>2);assert.equal(x.allowed,4081);
set("SHORT",50,51,47,1000,0.45);
x=context.calc();assert(Math.abs(x.loss-1225)<0.001);assert(Math.abs(x.gain-2775)<0.001);
set("LONG",50,51,53,1000,0.45);assert.throws(()=>context.calc(),/不合法/);
set("SHORT",50,49,47,1000,0.45);assert.throws(()=>context.calc(),/不合法/);
set("LONG",50,49,53,10000,0.45);context.calculate();assert.match(get("riskResult").textContent,/未通過/);
assert.match(context.safe("<img src=x onerror=alert(1)>"),/&lt;img/);
assert(!/\bfetch\s*\(|\bXMLHttpRequest\b|\bWebSocket\b/.test(match[1]),"v1 must remain offline-only");
console.log("TRIDENT smoke checks passed: JSON, escaping, LONG/SHORT PnL, risk limits and safe defaults.");
