# FA-2: AI Application for Design of Steel Structural Members as per IS 800:2007

A beginner-friendly **Streamlit** teaching app that reports the three tension checks
(yielding, net-section rupture with angle shear lag, and block shear) for a **single
rolled steel angle bolted through one leg in one straight bolt row**.
The explanatory paragraph is deterministic (AI-style wording only). The Streamlit
application calculates using `engine.py`. An additional **interactive, standalone
`preview.html`** performs the same narrow calculations in browser-side JavaScript
for offline viewing without installing Python. It is independently tested against
the Python reference cases, not a replacement for engineering verification.

## Start on Windows / VS Code

1. Install Python **3.10+** and open this folder in VS Code or PowerShell.
2. Open a terminal in the same folder as `app.py`.
3. (Optional) Create a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

4. Install dependencies:

```powershell
py -m pip install -r requirements.txt
```

5. Start the Streamlit server:

```powershell
py -m streamlit run app.py
```

Open the browser URL shown in terminal, normally **http://localhost:8501**.
To stop: **Ctrl+C** in the terminal.

**Editable results:** All numeric inputs can be changed. The checkbox
**Automatically recalculate when inputs change** is enabled by default, so
strengths and PASS/FAIL update after an input edit/Enter. Untick it to use
**Check selected angle** only. Engineering formula results are read-only;
change the member inputs rather than overwriting calculated capacities.

## Open an interactive preview without Python or a terminal

Double-click `preview.html` after extracting the ZIP; it works offline in a
modern browser. **Unlike the old static mockup, all numerical inputs and the
angle designation can be edited.** Every change recalculates yielding, rupture,
block shear, utilization, governing strength and PASS/FAIL immediately.

- Use **PASS example**, **FAIL example** or **Invalid section** to demonstrate.
- Enter a section outside the 11-item catalog: `please select correct section`.
- Expand **Step-by-step calculations** to see formulas and intermediate values.
- Choose **Download results** for a JSON of the current calculated case.
- Compression is explicitly not implemented; it does not output a false PASS.
- Because `preview.html` is a separately coded browser implementation, use the
  Streamlit/Python app as the project's authoritative calculation engine.

To validate the offline preview (if Node.js is installed):

```powershell
node tests/test_preview.js
```

If you modify `data/angles.csv` or the browser engine code, regenerate the
self-contained preview with `py tools/build_preview.py` and rerun the tests.

### On macOS/Linux

```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

### Test the calculation engine without Streamlit

```bash
python -m unittest discover -s tests -v
```

## Demo (2 minutes)

1. Choose **Tensile member**.
2. Use `120 kN`, `fy 250 MPa`, `fu 410 MPa`.
3. Use `n=3`, hole `18 mm`, pitch `60 mm`, end `40 mm`, gauge `35 mm`.
4. Last entry **Enter your angle**: `ISA 75x75x6`. Click **Check selected angle**.
5. View the automatically calculated three checks, a PASS result, `Td ≈ 172.145 kN`, and the detailed formulas.
6. Change force to `180 kN` (automatically refreshes): **Block shear = Not Satisfy**; overall FAIL.
7. Enter `ISA 79x79x7`: result **please select correct section**.
8. Choose **Compressive member**: a notice explains why compression requires its
   own IS 800 Section 7 buckling module. No fabricated strength is calculated.

## User flow

Member selection → Factored axial load → Material and bolt details → **Enter your angle LAST**
→ Validate → Yield / Rupture / Block shear → PASS/FAIL → Worked solution → AI-style explanation.

## File structure

```
app.py                     Streamlit interface with editable inputs and automatic refresh
engine.py                  Pure Python deterministic equations and validation
data/angles.csv            Small explicitly verified section shortlist
preview.html               Standalone offline INTERACTIVE browser calculator
tools/preview_calculator.js JS equivalent of restricted Python equations
tools/preview_template.html HTML/CSS/JS template
tools/build_preview.py    Rebuilds preview.html using catalog and JS calculator
tests/test_preview.js      Reference tests for browser calculation engine
requirements.txt          Streamlit dependency
VALIDATION.md             Independent expected reference values and manual verification plan
tests/test_engine.py       12 repeatable unit tests
README.md                  This guide
```

## Engineering assumptions and limits

- This is **not a professional full design**; green PASS only means **the three
  implemented simplified checks** pass under the assumed one-row bolted geometry.
- `Ag` comes from a curated **IS 808:2021** table transcription (QuickBOQ), not
  from the student's unprovided Steel Book. IS 808 editions can differ. The app
  allows only the explicitly stored sizes and warns for any other designation.
- The connected/outstanding leg area split is a textbook mid-thickness rectangular
  approximation; the precise rolled corner-radius distribution must be checked
  with the institution's Steel Book. It is not an exact breakdown of tabulated `Ag`.
- Single angle rupture uses **IS 800:2007 clause 6.3.3**, including the adjusted
  `0.9 fu γm0/(fy γm1)` beta upper limit in **Amendment No.1, January 2012**.
  Some online copies show the superseded upper bound without `0.9`.
- Block shear uses **one assumed tear-out path** of Figure 7B for the specified
  single-bolt-row connection. Other critical paths are **not** automatically identified.
- Bolt hole clearance, edge distance, pitch requirements, bolt resistance,
  gusset capacity, plate/angle local effects, slenderness, fatigue, compression
  buckling and full load combinations are outside this prototype. Apply IS 800
  clause 10 detailing and actual structural calculations separately.
- The UI's `fy=250 MPa`, `fu=410 MPa` are user-editable illustrative values,
  **not** guaranteed for every product thickness and grade.
- Do **not** use the tension checks for compression; compression needs a different
  implementation under IS 800 Section 7.

## Clauses and source links

- IS 800:2007: §6.1 design tension, §6.2 gross yielding,
  §6.3.3 single-angle rupture/shear lag, §6.4.1 bolted block shear,
  §5.4.1/Table 5 partial material factors, §10.2 bolt detailing.
- **2012 Amendment No.1** changes the cap in clause 6.3.3. Verify the original
  clause and amendment from the actual standard held by your college.
- Standard overview and amend: https://studylib.net/doc/28105314/is.800.2007
- Published online excerpt with original formulas: https://www.bnec.ac.in/assets/images/civil/Civildatabooks/IS.800.2007.pdf
- 2012 amendment excerpt: https://www.scribd.com/document/548343410/IS-800A1
- Curated section data from IS 808:2021 transcription:
  https://quickboq.in/steel/tables/angles/

**The user's actual 2 PDFs (IS 800 and Steel Book) and example image sketches were not
available as readable attachments here.** Before academic submission, check the
values and paths against those supplied documents; do not claim this matches the
unseen worked images exactly.


## Double-angle tension mode (limited supported arrangement)

Select **Double Angle** in the Streamlit app or the standalone `preview.html`.
The implementation is for **two identical mirrored angles on opposite faces of one
common end gusset**, bolted through one connected leg each with **one aligned
straight through-bolt row**, matching materials and hole geometry, and equal load
sharing. A factored member force `T` is compared with combined capacities.

- Gross yielding: `Tdg,2 = 2 Ag fy / gamma_m0` (IS 800:2007, 6.2).
- Rupture: `Tdn,2 = 2[0.9 Anc fu/gamma_m1 + beta Ago fy/gamma_m0]`
  (6.3.4 refers to 6.3.3 for shear lag; `bs` measured to the farthest
  outstanding-leg edge, same per-angle geometry in this symmetric case).
- Bolted angle tearout/block shear: `Tdb,2 = 2 min(Tdb1, Tdb2)` for the
  explicitly assumed **independent, identical** shear/tension tear-out path
  of each angle (6.4.1).
- `T_design = min(Tdg,2, Tdn,2, Tdb,2)`. All pass/fail checks use **TOTAL**
  member factored force, **not** the half-force.

**Not supported:** two angles on the same gusset face, dissimilar angle sizes,
other bolt patterns, welded connections, other block-shear paths, eccentric
load distribution, compression. Bolt shear/bearing, gusset net section, gusset
block shear, spacing/clearance, slenderness and all connection details are not
checked. Therefore member PASS is not design approval. Obtain the student's
actual example/connection sketch before claiming a general double-angle design.

After modifying the offline preview source, regenerate and test:

```powershell
py tools/build_preview.py
node tests/test_preview.js
py -m unittest discover -s tests -v
```


## Preliminary Steel Angle Suggestions (Streamlit)

Suggestions compare the eleven angle sizes currently in `data/angles.csv` and
search 2–30 bearing bolts in one longitudinal row. The search compares total
gross area, section yielding, net-section rupture, modeled block shear,
threaded-plane bolt shear (single vs double shear), angle bearing, gusset bearing
and long-joint reduction. Inputs include applied force, requested area, bolt
diameter/grade, steel strengths and gusset thickness/strength.

Only a *preliminary educational shortlist* is provided. This is NOT a complete
connection design. Edge preparation is assumed machined; check all IS 800
detailing, thread root area, packing, bolt spacing, grip and joint geometry,
alternate block paths, gusset net/block shear, eccentricity, slenderness,
member effective length and all applicable load cases independently.

Both the Streamlit app and regenerated standalone browser `preview.html`
include automatic preliminary bolt/section suggestions.
