/* Offline browser calculator equivalent to engine.py for the educational
   single rolled angle / one-leg / one-longitudinal bolt-row assumption.
   Keep this in parity with engine.py and its reference tests.
*/
window.SteelCalculator = (() => {
  "use strict";
  const gammaM0 = 1.10;
  const gammaM1 = 1.25;
  function normalizeSection(value) {
    const text = String(value || "").trim().toUpperCase()
      .replaceAll("×", "X").replaceAll("∠", "").replace(/\s+/g, "").replace(/^(ISA|L)/, "");
    if (!/^\d+(?:\.0+)?X\d+(?:\.0+)?X\d+(?:\.0+)?$/.test(text)) return "";
    return text.split("X").map(n => String(parseInt(n, 10))).join("X");
  }
  function findAngle(input, catalog) {
    const key = normalizeSection(input);
    const angle = catalog.find(row => normalizeSection(row.section) === key);
    if (!angle) throw new Error("please select correct section");
    return angle;
  }
  function numeric(value, label) {
    const n = Number(value);
    if (!Number.isFinite(n) || n <= 0) throw new Error(label + " must be a positive finite number.");
    return n;
  }
  function calculate(raw, catalog) {
    if (raw.member_type !== "Tensile member") {
      throw new Error("Compression needs separate IS 800 Section 7 buckling checks. No tension PASS/FAIL is available for compression.");
    }
    const angle = findAngle(raw.section, catalog);
    const force = numeric(raw.force_kn, "Factored force (kN)");
    const fy = numeric(raw.fy_mpa, "Yield stress fy (MPa)");
    const fu = numeric(raw.fu_mpa, "Ultimate stress fu (MPa)");
    const n = numeric(raw.bolts_in_line, "Bolts in line");
    const d = numeric(raw.hole_diameter_mm, "Hole diameter (mm)");
    const p = numeric(raw.pitch_mm, "Pitch (mm)");
    const e = numeric(raw.end_distance_mm, "End distance (mm)");
    const g = numeric(raw.gauge_mm, "Gauge (mm)");
    const a = numeric(angle.a_mm, "Connected leg (mm)");
    const b = numeric(angle.b_mm, "Outstanding leg (mm)");
    const t = numeric(angle.t_mm, "Angle thickness (mm)");
    const Ag = numeric(angle.gross_area_mm2, "Gross area (mm²)");
    if (fu <= fy) throw new Error("Ultimate stress fu must exceed yield stress fy.");
    if (!Number.isInteger(n) || n < 2 || n > 30) throw new Error("Use 2 to 30 whole bolts in the single longitudinal line.");
    if (t >= Math.min(a, b)) throw new Error("Angle thickness must be smaller than the leg widths.");
    if (d >= a - t / 2) throw new Error("The hole is too large for the connected leg net section.");
    if (!(d / 2 < g && g < a - d / 2)) throw new Error("Bolt hole must fit entirely inside the connected leg (gauge from heel).");
    if (p < d) throw new Error("Pitch must be at least the hole diameter to avoid overlapping holes.");
    if (e <= d / 2) throw new Error("End distance must exceed half the hole diameter.");

    const tdg = Ag * fy / gammaM0 / 1000;
    const Anc = (a - t / 2 - d) * t;
    const Ago = (b - t / 2) * t;
    const w = b;
    const bs = w + g - t;
    const Lc = (n - 1) * p;
    const betaRaw = 1.4 - 0.076 * (w / t) * (fy / fu) * (bs / Lc);
    const betaMax = 0.9 * fu * gammaM0 / (fy * gammaM1);
    const beta = Math.min(Math.max(betaRaw, 0.7), betaMax);
    const tdn = (0.9 * Anc * fu / gammaM1 + beta * Ago * fy / gammaM0) / 1000;
    const Ls = e + Lc;
    const Avg = Ls * t;
    const Avn = (Ls - (n - 0.5) * d) * t;
    const Atg = (a - g) * t;
    const Atn = (a - g - d / 2) * t;
    if (Math.min(Anc, Ago, Avg, Avn, Atg, Atn) <= 0) throw new Error("Net ligament/tear-out area is not positive; revise hole layout.");
    const tdb1 = (Avg * fy / (Math.sqrt(3) * gammaM0) + 0.9 * Atn * fu / gammaM1) / 1000;
    const tdb2 = (0.9 * Avn * fu / (Math.sqrt(3) * gammaM1) + Atg * fy / gammaM0) / 1000;
    const tdb = Math.min(tdb1, tdb2);
    const strength = Math.min(tdg, tdn, tdb);
    const checks = {
      "Yielding": { capacity_kn: tdg, status: force <= tdg + 1e-9 ? "Satisfies" : "Not Satisfy" },
      "Rupture": { capacity_kn: tdn, status: force <= tdn + 1e-9 ? "Satisfies" : "Not Satisfy" },
      "Block shear": { capacity_kn: tdb, status: force <= tdb + 1e-9 ? "Satisfies" : "Not Satisfy" },
    };
    const governing = tdg <= tdn && tdg <= tdb ? "Gross-section yielding"
      : tdn <= tdb ? "Net-section rupture" : "Block shear";
    return {
      section: angle.section, angle, inputs: {force_kn:force, fy_mpa:fy, fu_mpa:fu, bolts_in_line:n, hole_diameter_mm:d,
        pitch_mm:p, end_distance_mm:e, gauge_mm:g},
      gross_yield_kn:tdg, net_rupture_kn:tdn, block_shear_kn:tdb,
      block_case_1_kn:tdb1, block_case_2_kn:tdb2, design_strength_kn:strength,
      utilization:force/strength, governing_mode:governing, overall_pass:force <= strength + 1e-9,
      gross_area_mm2:Ag, connected_net_area_mm2:Anc, outstanding_gross_area_mm2:Ago,
      beta_raw:betaRaw, beta_max:betaMax, beta_used:beta, w_mm:w, bs_mm:bs, lc_mm:Lc,
      avg_mm2:Avg, avn_mm2:Avn, atg_mm2:Atg, atn_mm2:Atn, gamma_m0:gammaM0, gamma_m1:gammaM1, checks,
    };
  }
  // Cl. 6.3.4 (double angle) uses the Cl. 6.3.3 shear-lag model.
  // Only equal, mirrored angles on opposite gusset faces with one shared
  // through-bolt row and equal demand are supported. Joint checks excluded.
  function calculateDouble(raw, catalog) {
    const force = numeric(raw.force_kn, "Factored force (kN)");
    const half = calculate({...raw, force_kn: force / 2}, catalog);
    const summed = ["gross_yield_kn", "net_rupture_kn", "block_shear_kn",
      "block_case_1_kn", "block_case_2_kn", "design_strength_kn",
      "gross_area_mm2", "connected_net_area_mm2", "outstanding_gross_area_mm2",
      "avg_mm2", "avn_mm2", "atg_mm2", "atn_mm2"];
    const combined = {...half, inputs: {...half.inputs, force_kn: force},
      angle_count: 2, angle_design: "Double Angle",
      arrangement: "Two identical mirrored angles on opposite faces of a common gusset, one shared straight through-bolt line, equal load"};
    for (const name of summed) combined[name] = 2 * half[name];
    combined.utilization = force / combined.design_strength_kn;
    combined.overall_pass = force <= combined.design_strength_kn + 1e-9;
    combined.checks = {
      "Yielding": { capacity_kn: combined.gross_yield_kn, status: force <= combined.gross_yield_kn + 1e-9 ? "Satisfies" : "Not Satisfy" },
      "Rupture": { capacity_kn: combined.net_rupture_kn, status: force <= combined.net_rupture_kn + 1e-9 ? "Satisfies" : "Not Satisfy" },
      "Block shear": { capacity_kn: combined.block_shear_kn, status: force <= combined.block_shear_kn + 1e-9 ? "Satisfies" : "Not Satisfy" },
    };
    return combined;
  }
  // Preliminary bearing-type bolt + small catalog section shortlist.
  // Restricted one-row single/mirrored-opposite-gusset twin-angle only.
  function recommend(raw, catalog, option) {
    const d=Number(option.bolt_d_mm), fub=Number(option.bolt_fub_mpa),
      tg=Number(option.gusset_t_mm), fug=Number(option.gusset_fu_mpa),
      area=Number(option.required_area_mm2), holes={12:13,16:18,20:22,24:26};
    if(!Object.hasOwn(holes,d)||![400,800].includes(fub)) throw new Error("Unsupported bearing bolt specification.");
    if(!Number.isFinite(area)||area<0) throw new Error("Required gross area must be nonnegative.");
    numeric(tg,"Gusset thickness"); numeric(fug,"Gusset ultimate strength");
    if(Math.abs(Number(raw.hole_diameter_mm)-holes[d])>1e-6)
      throw new Error(`M${d} needs hole diameter ${holes[d]} mm. Update Step 4.`);
    if(raw.pitch_mm < 2.5*d) throw new Error("Pitch must be at least 2.5 times bolt diameter.");
    if(raw.end_distance_mm < 1.5*holes[d]) throw new Error("End distance must be at least 1.5 times hole diameter for assumed machined edge.");
    const double=raw.angle_design==="Double Angle", factor=double?2:1;
    const force=numeric(raw.force_kn,"Factored force"), fy=numeric(raw.fy_mpa,"fy");
    const minYieldArea=force*1000*1.1/fy, minArea=Math.max(area,minYieldArea);
    const boltCheck=(section,n)=>{
      const grip=tg+factor*section.t_mm;
      if(grip>5*d) throw new Error("Grip over 5d is outside preliminary suggestion scope.");
      const anb=.78*Math.PI*d*d/4, lj=(n-1)*raw.pitch_mm;
      const betaLj=(n<=2||lj<=15*d)?1:Math.max(.75,Math.min(1,1.075-lj/(200*d)));
      const shear=fub/(Math.sqrt(3)*1.25)*factor*anb/1000*betaLj;
      const kb=(fu)=>Math.min(raw.end_distance_mm/(3*raw.hole_diameter_mm),
        raw.pitch_mm/(3*raw.hole_diameter_mm)-.25,fub/fu,1);
      const kbAngle=kb(raw.fu_mpa),kbGusset=kb(fug);
      const angleBearing=2.5*kbAngle*d*section.t_mm*raw.fu_mpa/1.25/1000*factor;
      const gussetBearing=2.5*kbGusset*d*tg*fug/1.25/1000;
      const boltCap=Math.min(shear,angleBearing,gussetBearing);
      return {count:n,net_thread_area_mm2:anb,shear_planes:factor,long_joint_factor:betaLj,
        kb_angle:kbAngle,kb_gusset:kbGusset,shear_per_bolt_kn:shear,
        bearing_angles_per_bolt_kn:angleBearing,bearing_gusset_per_bolt_kn:gussetBearing,
        capacity_per_bolt_kn:boltCap,group_capacity_kn:n*boltCap,
        status:n*boltCap+1e-9>=force?"Satisfies":"Not Satisfy"};
    };
    const selectedBolt=boltCheck(findAngle(raw.section,catalog),Number(raw.bolts_in_line));
    const rows=[];
    for(const a of [...catalog].sort((x,y)=>x.gross_area_mm2-y.gross_area_mm2)){
      const totalArea=factor*a.gross_area_mm2;
      if(totalArea+1e-9<minArea) continue;
      for(let n=2;n<=30;n++){
        const input={...raw,section:a.section,bolts_in_line:n};
        try {
          const mem=double?calculateDouble(input,catalog):calculate(input,catalog),bolt=boltCheck(a,n);
          const cap=Math.min(mem.design_strength_kn,bolt.group_capacity_kn);
          if(cap+1e-9>=force) {
            rows.push({section:a.section,number_of_angles:factor,total_area_mm2:totalArea,
              bolts:n,gross_yield_kn:mem.gross_yield_kn,net_rupture_kn:mem.net_rupture_kn,
              block_shear_kn:mem.block_shear_kn,member_capacity_kn:mem.design_strength_kn,
              bolt_group_capacity_kn:bolt.group_capacity_kn,governing_capacity_kn:cap,
              utilization:force/cap,status:"Preliminary Satisfies"});
            break;
          }
        }catch(e){ /* invalid candidate geometry: skip */ }
      }
    }
    rows.sort((x,y)=>x.total_area_mm2-y.total_area_mm2||x.bolts-y.bolts||x.section.localeCompare(y.section));
    return {minimum_yield_area_mm2:minYieldArea,selected_bolt:selectedBolt,rows:rows.slice(0,8),
      assumptions:"Bearing-type bolts; standard holes; threaded shear planes; machined edges; no packing; grip <=5d; member and basic bolt checks only."};
  }

  return { normalizeSection, findAngle, calculate, calculateDouble, recommend };
})();
