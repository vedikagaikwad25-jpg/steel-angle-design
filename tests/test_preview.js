// Run with: node tests/test_preview.js
// Verifies the self-contained preview is consistent with independent reference cases.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname,'..','preview.html'),'utf8');
const engineCode = html.match(/<script id="engine-script">([\s\S]*?)<\/script>/)?.[1];
const catalogCode = html.match(/<script>const CATALOG = ([\s\S]*?);<\/script>/)?.[1];
assert(engineCode, 'Expected embedded calculation engine');
assert(catalogCode, 'Expected embedded catalog');
const catalog = JSON.parse(catalogCode);
const scope = {window:{}};
vm.runInNewContext(engineCode,scope);
const calc = data=>scope.window.SteelCalculator.calculate({member_type:'Tensile member', fy_mpa:250,fu_mpa:410, ...data},catalog);
function close(actual,expected){assert(Math.abs(actual-expected)<0.000005,`${actual} vs ${expected}`)}
const examples=[
  {section:'75x75x6',force_kn:160,bolts_in_line:4,pitch_mm:100,end_distance_mm:70,gauge_mm:35,hole_diameter_mm:18,tdg:198.86363636,tdn:213.38315920,tdb1:346.20665400,tdb2:368.48451316,mode:'Gross-section yielding',pass:true},
  {section:'50x50x5',force_kn:105,bolts_in_line:3,pitch_mm:60,end_distance_mm:40,gauge_mm:35,hole_diameter_mm:18,tdg:109.77272727,tdn:102.43427642,tdb1:113.82877622,tdb2:115.04488924,mode:'Net-section rupture',pass:false},
  {section:'75x75x6',force_kn:180,bolts_in_line:3,pitch_mm:60,end_distance_mm:40,gauge_mm:35,hole_diameter_mm:18,tdg:198.86363636,tdn:183.80887982,tdb1:180.87453146,tdb2:172.14477618,mode:'Block shear',pass:false},
];
for(const e of examples){
  const r=calc(e);
  close(r.gross_yield_kn,e.tdg);close(r.net_rupture_kn,e.tdn);
  close(r.block_case_1_kn,e.tdb1);close(r.block_case_2_kn,e.tdb2);
  assert.equal(r.governing_mode,e.mode);assert.equal(r.overall_pass,e.pass);
}
const base={section:'ISA 75x75x6',force_kn:120,bolts_in_line:3,pitch_mm:60,end_distance_mm:40,gauge_mm:35,hole_diameter_mm:18};
assert.equal(calc(base).overall_pass,true);
assert.equal(calc({...base,force_kn:180}).overall_pass,false);
assert.throws(()=>calc({...base,section:'ISA 79x79x7'}),/please select correct section/);
assert.throws(()=>calc({...base,gauge_mm:73}),/fit entirely/);
assert.throws(()=>calc({...base,fu_mpa:200}),/must exceed yield/);
assert.throws(()=>calc({...base,force_kn:0}),/positive finite/);
assert.throws(()=>calc({...base,member_type:'Compressive member'}),/Compression needs/);
console.log('PASS: 3 independent cases + 7 browser-engine validation / change checks');
