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
  return { normalizeSection, findAngle, calculate };
})();
