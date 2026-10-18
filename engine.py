"""Deterministic IS 800:2007 tension checks for a narrow bolted-angle case.

Educational prototype; validate the critical rupture and block-shear paths
against the actual drawings and licensed standard. No AI enters this module.
"""

from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path

GAMMA_M0 = 1.10   # IS 800:2007, Table 5: yielding
GAMMA_M1 = 1.25   # IS 800:2007, Table 5: ultimate strength
CATALOG_PATH = Path(__file__).parent / "data" / "angles.csv"


class InputError(ValueError):
    """Geometry or material values cannot produce a valid demonstration."""


class UnknownSection(InputError):
    """Angle designation not in the verified, explicitly limited catalog."""


@dataclass(frozen=True)
class Angle:
    name: str
    connected_leg_mm: float
    outstanding_leg_mm: float
    thickness_mm: float
    area_mm2: float
    source_url: str


@dataclass(frozen=True)
class DesignInput:
    force_kn: float
    fy_mpa: float
    fu_mpa: float
    bolts_in_line: int
    hole_diameter_mm: float
    pitch_mm: float
    end_distance_mm: float
    gauge_mm: float


@dataclass(frozen=True)
class DesignResult:
    angle: Angle
    inputs: DesignInput
    gross_yield_kn: float
    net_rupture_kn: float
    block_shear_kn: float
    block_case_1_kn: float
    block_case_2_kn: float
    design_strength_kn: float
    utilization: float
    governing_mode: str
    gross_area_mm2: float
    connected_net_area_mm2: float
    outstanding_gross_area_mm2: float
    beta_raw: float
    beta_max: float
    beta_used: float
    w_mm: float
    bs_mm: float
    lc_mm: float
    avg_mm2: float
    avn_mm2: float
    atg_mm2: float
    atn_mm2: float

    def check(self, strength_kn: float) -> bool:
        # Tiny floating tolerance to avoid an exact-boundary display mismatch.
        return self.inputs.force_kn <= strength_kn + 1e-9

    @property
    def overall_pass(self) -> bool:
        return self.check(self.gross_yield_kn) and self.check(self.net_rupture_kn) and self.check(self.block_shear_kn)


def normalize_section(text: str) -> str:
    # Permit '75x75x6', 'ISA 75 × 75 × 6', 'L75x75x6'.
    s = text.strip().upper().replace("×", "X").replace("∠", "")
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"^(ISA|L)", "", s)
    if not re.fullmatch(r"\d+(?:\.0+)?X\d+(?:\.0+)?X\d+(?:\.0+)?", s):
        return ""
    return "X".join(str(int(float(x))) for x in s.split("X"))


def load_catalog() -> dict[str, Angle]:
    with CATALOG_PATH.open(encoding="utf-8", newline="") as f:
        rows = csv.DictReader(f)
        angles = {}
        for row in rows:
            a = Angle(
                name=row["section"],
                connected_leg_mm=float(row["a_mm"]),
                outstanding_leg_mm=float(row["b_mm"]),
                thickness_mm=float(row["t_mm"]),
                area_mm2=float(row["gross_area_mm2"]),
                source_url=row["source_url"],
            )
            key = normalize_section(a.name)
            if key in angles:
                raise RuntimeError(f"Duplicate catalog section: {a.name}")
            angles[key] = a
        return angles


def find_angle(section: str) -> Angle:
    angle = load_catalog().get(normalize_section(section))
    if angle is None:
        raise UnknownSection("please select correct section")
    return angle


def _require_positive(name: str, value: float) -> None:
    if not math.isfinite(value) or value <= 0:
        raise InputError(f"{name} must be a positive finite number.")


def validate(angle: Angle, data: DesignInput) -> None:
    values = {
        "Factored force (kN)": data.force_kn,
        "Yield stress fy (MPa)": data.fy_mpa,
        "Ultimate stress fu (MPa)": data.fu_mpa,
        "Hole diameter (mm)": data.hole_diameter_mm,
        "Pitch (mm)": data.pitch_mm,
        "End distance (mm)": data.end_distance_mm,
        "Gauge (mm)": data.gauge_mm,
        "Gross area (mm²)": angle.area_mm2,
    }
    for name, value in values.items():
        _require_positive(name, value)
    if data.fu_mpa <= data.fy_mpa:
        raise InputError("Ultimate stress fu must exceed yield stress fy.")
    if isinstance(data.bolts_in_line, bool) or not isinstance(data.bolts_in_line, int) or data.bolts_in_line < 2:
        raise InputError("At least two bolts in one longitudinal line are needed to define Lc.")
    a, b, t = angle.connected_leg_mm, angle.outstanding_leg_mm, angle.thickness_mm
    if t >= min(a, b):
        raise InputError("Angle thickness must be smaller than the leg widths.")
    if data.hole_diameter_mm >= a - t / 2:
        raise InputError("The hole is too large for the connected leg net section.")
    if not (data.hole_diameter_mm / 2 < data.gauge_mm < a - data.hole_diameter_mm / 2):
        raise InputError("Bolt hole must fit entirely inside the connected leg (gauge from heel).")
    if data.pitch_mm < data.hole_diameter_mm:
        raise InputError("Pitch must be at least the hole diameter to avoid overlapping holes.")
    if data.end_distance_mm <= data.hole_diameter_mm / 2:
        raise InputError("End distance must exceed half the hole diameter.")
    if not (data.end_distance_mm + (data.bolts_in_line - 1) * data.pitch_mm > 0):
        raise InputError("Connection length must be positive.")


def calculate_tension(angle: Angle, data: DesignInput) -> DesignResult:
    """One single rolled angle, one connected leg, one straight bolt line.

    For other hole patterns, end paths, double angles, welded connections,
    or compression, this routine must not be used without expanding the model.
    """
    validate(angle, data)
    a, b, t = angle.connected_leg_mm, angle.outstanding_leg_mm, angle.thickness_mm
    hole = data.hole_diameter_mm

    # 6.2: gross-section yielding. Catalog gross area includes corner radii.
    tdg = (angle.area_mm2 * data.fy_mpa / GAMMA_M0) / 1000

    # 6.3.3: single angle bolted through one leg, straight line of holes.
    # Connected and outstanding leg subareas use mid-thickness partition.
    # The small rolled root-radius contribution is NOT claimed to be an exact
    # measured connected/outstanding partition: check this with the steel book.
    anc = (a - t / 2 - hole) * t
    ago = (b - t / 2) * t
    w = b  # Fig. 6: nominal width of the outstanding leg
    bs = w + data.gauge_mm - t  # Fig. 6: bs = w + w1 - t, w1 = gauge to bolt centre
    lc = (data.bolts_in_line - 1) * data.pitch_mm
    beta_raw = 1.4 - 0.076 * (w / t) * (data.fy_mpa / data.fu_mpa) * (bs / lc)
    # IMPORTANT: IS 800:2007 Amendment 1 (2012) adds 0.9 to beta upper cap.
    beta_max = 0.9 * data.fu_mpa * GAMMA_M0 / (data.fy_mpa * GAMMA_M1)
    beta = min(max(beta_raw, 0.7), beta_max)
    tdn = (0.9 * anc * data.fu_mpa / GAMMA_M1 + beta * ago * data.fy_mpa / GAMMA_M0) / 1000

    # 6.4.1: assumed one-shear-plane + one-tension-plane tear-out path
    # for a ONE-ROW connection in the connected leg (Fig. 7B).
    shear_path_mm = data.end_distance_mm + lc
    avg = shear_path_mm * t
    avn = (shear_path_mm - (data.bolts_in_line - 0.5) * hole) * t
    transverse_to_toe_mm = a - data.gauge_mm
    atg = transverse_to_toe_mm * t
    atn = (transverse_to_toe_mm - hole / 2) * t
    if min(anc, ago, avg, avn, atg, atn) <= 0:
        raise InputError("Net ligament/tear-out area is not positive; revise hole layout.")
    tdb1 = (avg * data.fy_mpa / (math.sqrt(3) * GAMMA_M0)
            + 0.9 * atn * data.fu_mpa / GAMMA_M1) / 1000
    tdb2 = (0.9 * avn * data.fu_mpa / (math.sqrt(3) * GAMMA_M1)
            + atg * data.fy_mpa / GAMMA_M0) / 1000
    tdb = min(tdb1, tdb2)

    strengths = {"Gross-section yielding": tdg, "Net-section rupture": tdn, "Block shear": tdb}
    governing = min(strengths, key=strengths.get)
    td = strengths[governing]
    return DesignResult(
        angle=angle, inputs=data, gross_yield_kn=tdg, net_rupture_kn=tdn,
        block_shear_kn=tdb, block_case_1_kn=tdb1, block_case_2_kn=tdb2,
        design_strength_kn=td, utilization=data.force_kn / td,
        governing_mode=governing, gross_area_mm2=angle.area_mm2,
        connected_net_area_mm2=anc, outstanding_gross_area_mm2=ago,
        beta_raw=beta_raw, beta_max=beta_max, beta_used=beta, w_mm=w,
        bs_mm=bs, lc_mm=lc, avg_mm2=avg, avn_mm2=avn,
        atg_mm2=atg, atn_mm2=atn,
    )


def explanation(r: DesignResult) -> str:
    status = "satisfies" if r.overall_pass else "does NOT satisfy"
    failed = [name for name, val in (
        ("yielding", r.gross_yield_kn), ("rupture", r.net_rupture_kn),
        ("block shear", r.block_shear_kn)) if not r.check(val)]
    why = ("All three evaluated resistance values exceed or equal the applied factored tension."
           if not failed else "The applied load exceeds the calculated " + ", ".join(failed) + " resistance check(s).")
    return (f"The selected {r.angle.name} {status} the three tension checks for the ASSUMED "
            f"one-leg/one-bolt-line layout. It carries a design load of {r.inputs.force_kn:.2f} kN "
            f"against a limiting calculated strength of {r.design_strength_kn:.2f} kN. "
            f"The governing mode is {r.governing_mode.lower()}. {why} "
            "This does not establish bolt strength, gusset strength, detailing compliance, "
            "or global structural safety.")
