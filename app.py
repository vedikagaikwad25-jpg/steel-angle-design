"""Streamlit front end for the FA-2 single-angle tension checker."""

import json
from dataclasses import asdict

import streamlit as st

from engine import (DesignInput, InputError, UnknownSection, calculate_tension,
                    explanation, find_angle, load_catalog)

st.set_page_config(page_title="Steel Angle Design | FA-2", page_icon="📐", layout="wide")
st.markdown("""
<style>
.block-container {max-width: 1150px; padding-top: 2rem;}
.hero {padding:1.2rem 1.4rem; border-radius:14px; background:#10375b;
       color:white; margin-bottom: 16px}
.hero h1{color:white; margin:0; font-size:2rem}
.hero p{color:#dceaf6; margin:.4rem 0 0}
.flag{padding:10px 14px;border:1px solid #e5e7eb;border-radius:10px;margin:6px 0}
[data-testid="stMetricValue"] {font-size: 1.75rem}
</style>
""", unsafe_allow_html=True)

st.markdown("""<div class="hero"><h1>Steel Angle Tension Member Checker</h1>
<p>FA-2 · Design of Steel Structures · Educational IS 800:2007 demonstration</p></div>""",
            unsafe_allow_html=True)
st.caption("Sequence: Member type → Factored force → Material/connection → Enter your angle (last)")

st.info("Scope: one single rolled angle bolted through one leg, with **one straight longitudinal bolt line**. "
        "Other geometries and full connection design are not evaluated.")

with st.container():
    st.subheader("1. Choose structural member")
    member_type = st.radio("What do you want to design?", ["Tensile member", "Compressive member"], horizontal=True)

    st.subheader("2. Applied axial force")
    load = st.number_input("Factored axial force (kN)", min_value=0.01, value=120.0, step=5.0)

    st.subheader("3. Material properties")
    steel_grade = st.selectbox("Steel grade/reference", ["E250 (illustrative only)", "Other grade / custom values"])
    st.caption("Enter fy and fu from your actual grade certificate/standard. E250 label does not automatically assign thickness-dependent properties.")
    c1, c2 = st.columns(2)
    with c1:
        fy = st.number_input("Yield stress fy (MPa = N/mm²)", min_value=1.0, value=250.0, step=10.0)
    with c2:
        fu = st.number_input("Ultimate tensile stress fu (MPa = N/mm²)", min_value=1.0, value=410.0, step=10.0)

    st.subheader("4. Bolted connection (straight row, one connected leg)")
    st.caption("Enter actual **hole diameter**, not bolt shank diameter. Gauge = hole centre to outer back of connected leg. "
               "Pitch = adjacent hole spacing along force. End distance = plate end to first hole centre.")
    c1, c2 = st.columns(2)
    with c1:
        bolts = st.number_input("Bolts in longitudinal line (n)", min_value=2, max_value=30, value=3, step=1)
        hole = st.number_input("Hole diameter d₀ (mm)", min_value=0.1, value=18.0, step=1.0)
        end = st.number_input("End distance e (mm)", min_value=0.1, value=40.0, step=5.0)
    with c2:
        pitch = st.number_input("Pitch p (mm)", min_value=0.1, value=60.0, step=5.0)
        gauge = st.number_input("Bolt gauge g from heel (mm)", min_value=0.1, value=35.0, step=5.0)

    st.subheader("5. Enter your angle (last question)")
    section = st.text_input("Angle size as in steel table (example: ISA 75x75x6)", value="ISA 75x75x6",
                            placeholder="ISA 75x75x6")
    known = sorted((a.name for a in load_catalog().values()))
    st.caption("Catalog: " + " · ".join(known))
    live_update = st.checkbox("Automatically recalculate when inputs change", value=True,
                              help="Uncheck this to calculate only when you press the button.")
    submitted = st.button("Check selected angle", type="primary", use_container_width=True)
    st.caption("Input numbers and angle designation are editable. Computed strengths are read-only; edit inputs to update them.")

if submitted or live_update:
    if member_type == "Compressive member":
        st.warning("Compression requires IS 800:2007 Section 7 buckling/slenderness checks. "
                   "The three requested yielding/rupture/block-shear checks are TENSION checks. "
                   "Compression is not implemented in this first prototype; no fabricated PASS result is given.")
        st.stop()
    try:
        angle = find_angle(section)
        inp = DesignInput(force_kn=float(load), fy_mpa=float(fy), fu_mpa=float(fu),
                          bolts_in_line=int(bolts), hole_diameter_mm=float(hole),
                          pitch_mm=float(pitch), end_distance_mm=float(end), gauge_mm=float(gauge))
        r = calculate_tension(angle, inp)
    except UnknownSection as err:
        st.error(str(err))
        st.stop()
    except InputError as err:
        st.error(f"Invalid input: {err}")
        st.stop()

    st.divider()
    st.subheader("Final output: Three design checks")
    labels = [
        ("Yielding", r.gross_yield_kn),
        ("Rupture", r.net_rupture_kn),
        ("Block shear", r.block_shear_kn),
    ]
    for label, strength in labels:
        status = "Satisfies" if r.check(strength) else "Not Satisfy"
        if r.check(strength):
            st.success(f"**{label} = {status}**  |  {strength:.2f} kN ≥ {load:.2f} kN")
        else:
            st.error(f"**{label} = {status}**  |  {strength:.2f} kN < {load:.2f} kN")

    c1, c2, c3 = st.columns(3)
    c1.metric("Design tensile strength", f"{r.design_strength_kn:.2f} kN")
    c2.metric("Utilization (load / capacity)", f"{r.utilization:.3f}")
    c3.metric("Member check", "PASS" if r.overall_pass else "FAIL")
    st.write(f"**Governing limit state:** {r.governing_mode}")

    with st.expander("All input data and section properties", expanded=True):
        st.write({
            "Member": member_type, "Section": angle.name,
            "Connected leg a": f"{angle.connected_leg_mm:g} mm",
            "Outstanding leg b": f"{angle.outstanding_leg_mm:g} mm",
            "Thickness t": f"{angle.thickness_mm:g} mm",
            "Steel-book gross area Ag": f"{angle.area_mm2:.1f} mm²",
            "Factored tension": f"{inp.force_kn:.2f} kN",
            "Material grade label": steel_grade,
            "fy": f"{inp.fy_mpa:.1f} MPa", "fu": f"{inp.fu_mpa:.1f} MPa",
            "Bolts (single row)": inp.bolts_in_line, "Hole diameter": f"{inp.hole_diameter_mm:.1f} mm",
            "Pitch": f"{inp.pitch_mm:.1f} mm", "End": f"{inp.end_distance_mm:.1f} mm",
            "Gauge": f"{inp.gauge_mm:.1f} mm", "γm0": 1.10, "γm1": 1.25,
        })
        st.markdown(f"[Section data source (IS 808:2021 table transcription)]({angle.source_url})")

    with st.expander("Step-by-step calculation · IS 800:2007", expanded=True):
        st.markdown("**1. Gross-section yielding — Clause 6.2**")
        st.latex(r"T_{dg}=\frac{A_g f_y}{\gamma_{m0}}")
        st.write(f"Ag = {r.gross_area_mm2:.2f} mm²; γm0 = 1.10 → **Tdg = {r.gross_yield_kn:.3f} kN**")

        st.markdown("**2. Net-section rupture of single angle — Clause 6.3.3**")
        st.latex(r"A_{nc}=(a-t/2-d_0)t,\quad A_{go}=(b-t/2)t")
        st.write(f"Anc = {r.connected_net_area_mm2:.2f} mm²; Ago = {r.outstanding_gross_area_mm2:.2f} mm²")
        st.latex(r"\beta_0=1.4-0.076\frac{w}{t}\frac{f_y}{f_u}\frac{b_s}{L_c}")
        st.write(f"w = {r.w_mm:.2f} mm; bs = {r.bs_mm:.2f} mm; Lc = {r.lc_mm:.2f} mm")
        st.latex(r"\beta=\min\!\left[\max(\beta_0,0.7),\frac{0.9 f_u\gamma_{m0}}{f_y\gamma_{m1}}\right]")
        st.write(f"β unbounded = {r.beta_raw:.4f}; upper cap = {r.beta_max:.4f}; "
                 f"**β used = {r.beta_used:.4f}** (2012 Amendment No. 1)")
        st.latex(r"T_{dn}=\frac{0.9 A_{nc} f_u}{\gamma_{m1}}+\frac{\beta A_{go}f_y}{\gamma_{m0}}")
        st.write(f"**Tdn = {r.net_rupture_kn:.3f} kN**")

        st.markdown("**3. Block shear — Clause 6.4.1 (assumed Fig. 7B path)**")
        st.latex(r"L_s=e+(n-1)p,\quad A_{vg}=L_s t,\quad A_{vn}=[L_s-(n-0.5)d_0]t")
        st.latex(r"A_{tg}=(a-g)t,\quad A_{tn}=(a-g-d_0/2)t")
        st.write(f"Avg = {r.avg_mm2:.2f} mm²; Avn = {r.avn_mm2:.2f} mm²; "
                 f"Atg = {r.atg_mm2:.2f} mm²; Atn = {r.atn_mm2:.2f} mm²")
        st.latex(r"T_{db,1}=\frac{A_{vg}f_y}{\sqrt{3}\gamma_{m0}}+\frac{0.9 A_{tn}f_u}{\gamma_{m1}}")
        st.latex(r"T_{db,2}=\frac{0.9 A_{vn}f_u}{\sqrt{3}\gamma_{m1}}+\frac{A_{tg}f_y}{\gamma_{m0}}")
        st.write(f"Case 1 = {r.block_case_1_kn:.3f} kN; Case 2 = {r.block_case_2_kn:.3f} kN; "
                 f"**Tdb = {r.block_shear_kn:.3f} kN**")
        st.latex(r"T_d=\min(T_{dg},T_{dn},T_{db})")
        st.write(f"Td = {r.design_strength_kn:.3f} kN; Utilization = {r.utilization:.3f}")

    st.subheader("Educational AI-style explanation (rule based, not generative AI)")
    st.write(explanation(r))
    st.warning("Only the assumed single-line block shear path is evaluated; bolt shear/bearing, "
               "gusset design, detailing, slenderness and other failure paths need separate checks. "
               "Confirm section dimensions/properties with YOUR steel book and the actual amended IS 800 code.")

    output = {
        "section": angle.name, "inputs": asdict(inp),
        "gross_yield_kn": r.gross_yield_kn,
        "net_rupture_kn": r.net_rupture_kn,
        "block_shear_kn": r.block_shear_kn,
        "design_strength_kn": r.design_strength_kn,
        "utilization": r.utilization,
        "checks": {n: ("Satisfies" if r.check(v) else "Not Satisfy") for n, v in labels},
        "overall": "PASS" if r.overall_pass else "FAIL",
        "note": "Educational single-line angle model; not a complete connection design.",
    }
    st.download_button("Download result (JSON)", data=json.dumps(output, indent=2),
                       file_name="steel_angle_tension_result.json", mime="application/json")

with st.sidebar:
    st.header("FA-2 Demonstration")
    st.markdown("**Project:** AI Application for Design of Steel Structural Members as per IS 800:2007")
    st.markdown("**Implemented:** Tension / single angle / one connected leg / one bolt line")
    st.markdown("**Not implemented:** Compression buckling, other connection arrangements, bolt and gusset capacity")
    st.caption("The 'AI-style' paragraph is deterministic and cannot change the computed strength.")
