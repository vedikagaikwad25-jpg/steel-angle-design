# Calculation validation and independently established reference values

The following check values were generated **outside the app engine** using a separate
40-digit Python `decimal.Decimal` calculation based on the written formulas.
They are then hard-coded in `tests/test_engine.py` and compared against the application's
floating-point results within **0.000005 kN**. This verifies the arithmetic implementation,
**not** the structural correctness of the assumed failure path or the underlying standard.

All cases: `fy=250 MPa`, `fu=410 MPa`, `gamma_m0=1.10`, `gamma_m1=1.25`,
one bolted leg and one longitudinal row (hole d0 in mm).

| Case | Angle (mm) | Factored load (kN) | n,p,e,g,d0 (mm) | Yield (kN) | Rupture (kN) | Block 1 (kN) | Block 2 (kN) | Governing | Result |
|---|---|---:|---|---:|---:|---:|---:|---|---|
| A | 75×75×6 | 160 | 4,100,70,35,18 | 198.86363636 | 213.38315920 | 346.20665400 | 368.48451316 | Yield | PASS |
| B | 50×50×5 | 105 | 3,60,40,35,18 | 109.77272727 | 102.43427642 | 113.82877622 | 115.04488924 | Rupture | FAIL |
| C | 75×75×6 | 180 | 3,60,40,35,18 | 198.86363636 | 183.80887982 | 180.87453146 | 172.14477618 | Block shear | FAIL |

### Example hand-verifiable intermediate quantities for Case C

- Gross area (`Ag`) = 875 mm² (transcribed source table).
- Connected net leg (`Anc`) = (75 − 6/2 − 18) × 6 = **324 mm²**.
- Outstanding gross leg (`Ago`) = (75 − 6/2) × 6 = **432 mm²**.
- Shear lag distance `bs` = 75 + 35 − 6 = **104 mm**.
- End connection length `Lc` = (3 − 1) × 60 = **120 mm**.
- Raw beta = `1.4 − 0.076 × (75/6) × (250/410) × (104/120)` = **0.8979674797**.
- 2012 amendment upper bound = `0.9 × 410 × 1.10 / (250 × 1.25)` = **1.29888**, hence beta = raw beta.
- `Avg = (40 + 2×60)×6 = 960 mm²`; `Avn = (160 − 2.5×18)×6 = 690 mm²`.
- `Atg = (75−35)×6 = 240 mm²`; `Atn = (75−35−18/2)×6 = 186 mm²`.
- Strength is min(198.86363636, 183.80887982, 172.14477618) = **172.14477618 kN**.
- 180 kN > 172.14477618 kN, so the **evaluated three-check result is FAIL**.

### Required independent engineering verification (not automated)

1. Verify steel book edition, gross area, root radius, gauge and leg partition against the user's actual Steel Book.
2. Verify exact figure definitions in IS 800:2007 clauses 6.3.3 and 6.4.1 **and Amendment No. 1 (January 2012)**; verify `bs`, net-leg partition and every possible failure path from the actual sketch.
3. Check hole diameter and bolt-detailing limits (IS 800 clause 10.2/Table 19), which this demonstration does not check.
4. Check bolt shear/bearing, gusset resistance, welded alternatives, slenderness and fatigue if applicable.
5. Do not treat the green PASS as design approval.

## Interactive browser preview testing

The standalone `preview.html` repeats the limited educational formulas in
JavaScript. Its unit cases in `tests/test_preview.js` compare the same 3
independently recorded expected examples, plus invalid sections/material and
load changes. A headless Chromium interaction pass verified that changing the
load from 120 kN to 180 kN updates PASS to FAIL and the displayed utilization,
invalid sections hide results, unsupported compression hides results, and input
reset restores the passing example. This verifies browser functionality, not
compliance of a structural connection design with every IS 800 clause.
