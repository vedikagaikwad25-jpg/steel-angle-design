"""Streamlit front end for the FA-2 single-angle tension checker."""

import json
from dataclasses import asdict

import streamlit as st

from engine import (DesignInput, InputError, UnknownSection, calculate_tension,
                    explanation, find_angle, load_catalog)
from double_angle import calculate_double_tension
from recommendations import BoltSpec, check_bolts, suggest_sections, STANDARD_HOLES
from dataclasses import replace

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

st.info("Scope: single rolled angle OR two identical mirrored angles on opposite faces of one gusset, "
        "bolted through one connected leg per angle with **one straight longitudinal bolt line**. "
        "Other geometries, bolt/gusset checks and full connection design are not evaluated.")

with st.container():
    st.subheader("1. Choose structural member")
    angle_layout = st.radio("Angle design", ["Single Angle", "Double Angle"], horizontal=True)
    if angle_layout == "Double Angle":
        st.info("Double Angle geometry: TWO identical mirrored angles on OPPOSITE faces of a common gusset, "
                "bolted through one connected leg with one aligned straight bolt line. "
                "The total factored load is shared equally. Bolt and gusset capacity are NOT checked.")
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

    st.subheader("4. Bolted connection (one longitudinal row per connected leg)")
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
        r = (calculate_double_tension(angle, inp) if angle_layout == "Double Angle"
             else calculate_tension(angle, inp))
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
            "Member": member_type, "Angle design": angle_layout,
            "Section": f"2 x {angle.name}" if angle_layout == "Double Angle" else angle.name,
            "Connection arrangement": r.arrangement if angle_layout == "Double Angle" else "One single angle; one bolt line",
            "Connected leg a": f"{angle.connected_leg_mm:g} mm",
            "Outstanding leg b": f"{angle.outstanding_leg_mm:g} mm",
            "Thickness t": f"{angle.thickness_mm:g} mm",
            "Total gross area Ag": f"{r.gross_area_mm2:.1f} mm²",
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

        st.markdown("**2. Net-section rupture — Clause 6.3.4 (double) / 6.3.3 (single)**"
                    if angle_layout == "Double Angle" else
                    "**2. Net-section rupture of single angle — Clause 6.3.3**")
        if angle_layout == "Double Angle":
            st.latex(r"A_{nc}=2(a-t/2-d_0)t,\quad A_{go}=2(b-t/2)t")
        else:
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
        if angle_layout == "Double Angle":
            st.latex(r"L_s=e+(n-1)p,\quad A_{vg}=2L_s t,\quad A_{vn}=2[L_s-(n-0.5)d_0]t")
        else:
            st.latex(r"L_s=e+(n-1)p,\quad A_{vg}=L_s t,\quad A_{vn}=[L_s-(n-0.5)d_0]t")
        if angle_layout == "Double Angle":
            st.latex(r"A_{tg}=2(a-g)t,\quad A_{tn}=2(a-g-d_0/2)t")
        else:
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
    if angle_layout == "Double Angle":
        st.write(f"For two identical mirrored angles on opposite faces of a gusset, "
                 f"each angle carries {inp.force_kn / 2:.2f} kN. "
                 f"The three modeled TOTAL strengths are yielding {r.gross_yield_kn:.2f} kN, "
                 f"rupture {r.net_rupture_kn:.2f} kN, and block shear {r.block_shear_kn:.2f} kN. "
                 f"Governing modeled mode: {r.governing_mode}. "
                 f"Member check: {'PASS' if r.overall_pass else 'FAIL'}. "
                 "This is only for the stated symmetric opposite-gusset arrangement; "
                 "bolts, gusset and other failure paths are not checked.")
    else:
        st.write(explanation(r))
    st.warning("Only the assumed one-line block shear path per angle is evaluated; bolt shear/bearing, "
               "gusset design, detailing, slenderness and other failure paths need separate checks. "
               "Confirm section dimensions/properties with YOUR steel book and the actual amended IS 800 code.")

    st.divider()
    st.subheader("6. Suggestions — steel section and number of bolts")
    st.caption("Preliminary, restricted bearing-bolt check for the same one-row connection model. "
               "Includes member yielding/rupture/block shear, bolt threaded-plane shear, "
               "angle + gusset bearing, and long-joint reduction. "
               "NOT a complete structural design or steel-book certification.")
    f1, f2, f3 = st.columns(3)
    with f1:
        area_required = st.number_input("Requested total gross area (mm²; 0 = auto)",
                                        min_value=0.0, value=0.0, step=100.0)
    with f2:
        bolt_d = st.selectbox("Nominal bearing bolt diameter", [12, 16, 20, 24], index=1,
                              format_func=lambda d: f"M{d}")
    with f3:
        bolt_grade = st.selectbox("Bolt grade", ["4.6", "8.8"])
    g1, g2 = st.columns(2)
    with g1:
        gusset_t = st.number_input("Gusset thickness (mm)", min_value=1.0, value=10.0, step=1.0)
    with g2:
        gusset_fu = st.number_input("Gusset ultimate strength (MPa)", min_value=1.0,
                                    value=410.0, step=10.0)
    st.caption(f"M{bolt_d}: standard hole d₀ = {STANDARD_HOLES[bolt_d]} mm. "
               "Update the hole diameter in step 4 to match. Assumptions: "
               "standard round holes, machined edges, threads in ALL shear planes, "
               "no packing or preload, grip no greater than 5d.")
    bolt_spec = BoltSpec(diameter_mm=bolt_d, ultimate_mpa=400 if bolt_grade == "4.6" else 800,
                         gusset_thickness_mm=float(gusset_t),
                         gusset_ultimate_mpa=float(gusset_fu))
    suggested_results = []
    chosen_bolt_result = None
    try:
        double = angle_layout == "Double Angle"
        minimum_yield_area, suggested_results = suggest_sections(
            inp, double, bolt_spec, minimum_area_mm2=float(area_required))
        chosen_bolt_result = check_bolts(angle, inp, double, bolt_spec)
        st.write(f"**Minimum area from yielding alone:** {minimum_yield_area:.1f} mm². "
                 f"**Applied force:** {inp.force_kn:.2f} kN. "
                 f"**Current bolt group ({inp.bolts_in_line} bolts):** "
                 f"{chosen_bolt_result.group_capacity_kn:.2f} kN "
                 f"({chosen_bolt_result.status}).")
        with st.expander("Bolt shear and bearing — step-by-step", expanded=True):
            st.latex(r"A_{nb} \approx 0.78\pi d^2/4")
            st.latex(r"V_{dsb}=\beta_{lj}f_{ub}n_s A_{nb}/(\sqrt{3}\gamma_{mb})")
            st.latex(r"k_b=\min(e/(3d_0),p/(3d_0)-0.25,f_{ub}/f_u,1)")
            st.latex(r"V_{dpb}=2.5k_bdt f_u/\gamma_{mb}")
            st.write({
                "Bolt thread net area (approx. mm²)": round(chosen_bolt_result.net_thread_area_mm2, 2),
                "Shear planes": chosen_bolt_result.shear_planes,
                "Long joint factor": round(chosen_bolt_result.long_joint_factor, 4),
                "Total grip (mm)": round(chosen_bolt_result.grip_mm, 2),
                "Bolt shear capacity (kN / bolt)": round(chosen_bolt_result.shear_per_bolt_kn, 3),
                "Angle bearing capacity (kN / bolt)": round(chosen_bolt_result.bearing_angles_per_bolt_kn, 3),
                "Gusset bearing capacity (kN / bolt)": round(chosen_bolt_result.bearing_gusset_per_bolt_kn, 3),
                "Governing bolt capacity (kN / bolt)": round(chosen_bolt_result.capacity_per_bolt_kn, 3),
                "Total group capacity (kN)": round(chosen_bolt_result.group_capacity_kn, 3),
            })
        if suggested_results:
            st.markdown("**Available catalog matches (smallest total area first)**")
            st.dataframe([{
                "ISA section": q.section,
                "Angle count": q.number_of_angles,
                "Total area (mm²)": round(q.total_area_mm2, 1),
                "Minimum bolts": q.bolts,
                "Yielding (kN)": round(q.gross_yield_kn, 2),
                "Rupture (kN)": round(q.net_rupture_kn, 2),
                "Block shear (kN)": round(q.block_shear_kn, 2),
                "Bolt group (kN)": round(q.bolt_group_capacity_kn, 2),
                "Utilization": round(q.utilization, 3),
                "Result": q.status,
            } for q in suggested_results], use_container_width=True, hide_index=True)
            st.success(f"Smallest available matching shortlist: "
                       f"{suggested_results[0].number_of_angles} × {suggested_results[0].section}, "
                       f"{suggested_results[0].bolts} M{bolt_d} bolts. Preliminary only.")
        else:
            st.warning("No matching section/bolt count in the current 11-item catalog (maximum 30 bolts). "
                       "Check section catalogue, pitch, gauge, thickness, bolt grade and load.")
    except InputError as sug_err:
        st.error(f"Suggestions cannot be calculated: {sug_err}")
    st.caption("Final detailing, alternate tear-out paths, bolt-hole bearing compatibility, "
               "gusset net/block shear, eccentricity, member slenderness and full "
               "connection strength require checking from drawings/IS 800. "
               "A preliminary Satisfies result does not approve the structure.")

    output = {
        "section": angle.name, "angle_design": angle_layout,
        "connection_arrangement": (r.arrangement if angle_layout == "Double Angle"
                                   else "Single angle, one connected leg and one bolt line"),
        "inputs": asdict(inp),
        "gross_yield_kn": r.gross_yield_kn,
        "net_rupture_kn": r.net_rupture_kn,
        "block_shear_kn": r.block_shear_kn,
        "design_strength_kn": r.design_strength_kn,
        "utilization": r.utilization,
        "checks": {n: ("Satisfies" if r.check(v) else "Not Satisfy") for n, v in labels},
        "overall": "PASS" if r.overall_pass else "FAIL",
        "note": "Educational, limited symmetric opposite-gusset double-angle model"             if angle_layout == "Double Angle" else "Educational single-line angle model; not a complete connection design.",
    }
    output["bolt_specification"] = {
        "diameter_mm": bolt_spec.diameter_mm,
        "ultimate_mpa": bolt_spec.ultimate_mpa,
        "gusset_thickness_mm": bolt_spec.gusset_thickness_mm,
        "gusset_ultimate_mpa": bolt_spec.gusset_ultimate_mpa,
    }
    output["selected_bolt_check"] = (asdict(chosen_bolt_result) if chosen_bolt_result else None)
    output["suggested_sections"] = [asdict(q) for q in suggested_results]
    output["suggestions_disclaimer"] = "Preliminary educational shortlist only; no completed connection or structural approval."
    st.download_button("Download result (JSON)", data=json.dumps(output, indent=2),
                       file_name="steel_angle_tension_result.json", mime="application/json")

with st.sidebar:
    st.header("FA-2 Demonstration")
    st.markdown("**Project:** AI Application for Design of Steel Structural Members as per IS 800:2007")
    st.markdown("**Implemented:** Tension / single angle, and symmetric double angles "
                "on opposite gusset faces / one bolt line")
    st.markdown("**Not implemented:** Compression buckling, other connection arrangements, bolt and gusset capacity")
    st.caption("The 'AI-style' paragraph is deterministic and cannot change the computed strength.")
