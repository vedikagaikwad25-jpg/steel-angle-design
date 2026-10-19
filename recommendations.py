"""Preliminary section and bearing-type bolt shortlist for the steel-angle teaching app.

Design BASIS (IS 800:2007) applies only to one straight row, standard circular
holes, threads IN each shear plane, NO packing plate, and supported one-angle or
mirrored twin-angle geometries. This is not a full joint/member design.

Section catalog is limited to what is in data/angles.csv. A real Steel Book,
gusset block shear/net section, edge preparation, end checks, eccentricity,
member slenderness, end connection demands, etc. are NOT validated here.
"""
from dataclasses import dataclass, replace, asdict
from math import pi, sqrt, isfinite

from engine import DesignInput, InputError, calculate_tension, load_catalog
from double_angle import calculate_double_tension

STANDARD_HOLES = {12: 13, 16: 18, 20: 22, 24: 26}
GAMMA_MB = 1.25


@dataclass(frozen=True)
class BoltSpec:
    diameter_mm: int = 16
    ultimate_mpa: int = 400   # ordinary bearing bolts: 4.6; also supports 8.8/800
    gusset_thickness_mm: float = 10.0
    gusset_ultimate_mpa: float = 410.0


@dataclass(frozen=True)
class BoltCheck:
    count: int
    shear_planes: int
    net_thread_area_mm2: float
    long_joint_factor: float
    grip_mm: float
    kb_angle: float
    kb_gusset: float
    shear_per_bolt_kn: float
    bearing_angles_per_bolt_kn: float
    bearing_gusset_per_bolt_kn: float
    capacity_per_bolt_kn: float
    group_capacity_kn: float
    status: str


@dataclass(frozen=True)
class SectionSuggestion:
    section: str
    number_of_angles: int
    total_area_mm2: float
    bolts: int
    gross_yield_kn: float
    net_rupture_kn: float
    block_shear_kn: float
    member_capacity_kn: float
    bolt_group_capacity_kn: float
    governing_capacity_kn: float
    utilization: float
    status: str


def _positive(label, value):
    if not isfinite(value) or value <= 0:
        raise InputError(f'{label} must be positive and finite.')


def _validate_bolt_spec(data: DesignInput, spec: BoltSpec):
    if spec.diameter_mm not in STANDARD_HOLES:
        raise InputError('Supported bearing-bolt diameters: M12, M16, M20, M24.')
    if spec.ultimate_mpa not in (400, 800):
        raise InputError('Supported bolt ultimate strengths: 400 MPa (grade 4.6) or 800 MPa (grade 8.8).')
    _positive('Gusset thickness', spec.gusset_thickness_mm)
    _positive('Gusset ultimate strength', spec.gusset_ultimate_mpa)
    expected = STANDARD_HOLES[spec.diameter_mm]
    if abs(data.hole_diameter_mm - expected) > 1e-6:
        raise InputError(f'M{spec.diameter_mm} standard hole is {expected} mm. Set Hole diameter d0 to {expected} mm.')
    if data.pitch_mm < 2.5 * spec.diameter_mm:
        raise InputError('Pitch is below 2.5 times nominal bolt diameter (minimum spacing check).')
    if data.end_distance_mm < 1.5 * expected:
        raise InputError('End distance is below 1.5 x hole diameter (assumed machined edge).')


def check_bolts(angle, data: DesignInput, double: bool, spec: BoltSpec) -> BoltCheck:
    """Combined *bolt shear + plate bearing* check (specific narrow arrangement).

    Per-bolt resistance = minimum of thread-plane shear, angle bearing (one or
    two angles), and gusset bearing. k_b computed separately for each plate fu.
    For long joints applies beta_lj; grips greater than 5d are disallowed rather
    than reporting an unverified reduction. Max pitch/end and other detailing
    must be checked separately against the actual drawing.
    """
    _validate_bolt_spec(data, spec)
    d, d0, n = spec.diameter_mm, data.hole_diameter_mm, data.bolts_in_line
    if n < 2 or n > 30:
        raise InputError('Bolt count must be between 2 and 30 for this one-row demonstration.')
    grip = spec.gusset_thickness_mm + (2 if double else 1) * angle.thickness_mm
    if grip > 5 * d:
        raise InputError('Grip exceeds 5d; large-grip reduction not implemented in the suggestion module.')

    # Gross and thread-root area. 0.78 factor is an APPROXIMATION for standard
    # metric threads and must be confirmed using the actual bolt specification.
    anb = 0.78 * pi * d * d / 4
    planes = 2 if double else 1
    lj = (n - 1) * data.pitch_mm
    beta_lj = 1.0 if n <= 2 or lj <= 15 * d else max(0.75, min(1.0, 1.075 - lj / (200 * d)))
    shear = spec.ultimate_mpa / (sqrt(3) * GAMMA_MB) * planes * anb / 1000 * beta_lj

    def kb(fu):
        return min(data.end_distance_mm / (3 * d0), data.pitch_mm / (3 * d0) - 0.25,
                   spec.ultimate_mpa / fu, 1.0)

    k_angle, k_gusset = kb(data.fu_mpa), kb(spec.gusset_ultimate_mpa)
    if min(k_angle, k_gusset) <= 0:
        raise InputError('Bearing factor k_b is not positive; revise bolt layout.')
    # For a common gusset between two identical angles, the outer angle plates
    # collectively transfer the load to ONE gusset plate. The gusset sees the
    # total load. For single angle both plates transfer the total load.
    bearing_plates = 2.5 * k_angle * d * angle.thickness_mm * data.fu_mpa / GAMMA_MB / 1000 * (2 if double else 1)
    bearing_gusset = 2.5 * k_gusset * d * spec.gusset_thickness_mm * spec.gusset_ultimate_mpa / GAMMA_MB / 1000
    cap = min(shear, bearing_plates, bearing_gusset)
    return BoltCheck(n, planes, anb, beta_lj, grip, k_angle, k_gusset,
                     shear, bearing_plates, bearing_gusset, cap, n * cap,
                     'Satisfies' if n * cap + 1e-9 >= data.force_kn else 'Not Satisfy')


def _member_calculate(angle, data, double):
    return calculate_double_tension(angle, data) if double else calculate_tension(angle, data)


def suggest_sections(data: DesignInput, double: bool, spec: BoltSpec,
                     minimum_area_mm2: float = 0.0, max_bolts: int = 30,
                     max_results: int = 8):
    if not isfinite(minimum_area_mm2) or minimum_area_mm2 < 0:
        raise InputError('Required gross area must be non-negative and finite.')
    _positive('Applied design force', data.force_kn)
    _positive('Yield stress', data.fy_mpa)
    _validate_bolt_spec(data, spec)
    area_needed_for_yielding = data.force_kn * 1000 * 1.10 / data.fy_mpa
    minimum_total_area = max(minimum_area_mm2, area_needed_for_yielding)
    factor = 2 if double else 1
    results = []
    angles = sorted(load_catalog().values(), key=lambda a: (a.area_mm2, a.name))
    for a in angles:
        total_area = factor * a.area_mm2
        if total_area + 1e-9 < minimum_total_area:
            continue
        for n in range(2, min(max_bolts, 30) + 1):
            trial = replace(data, bolts_in_line=n)
            try:
                r = _member_calculate(a, trial, double)
                bolt = check_bolts(a, trial, double, spec)
            except InputError:
                continue
            combined = min(r.design_strength_kn, bolt.group_capacity_kn)
            if combined + 1e-9 >= data.force_kn:
                results.append(SectionSuggestion(
                    a.name, factor, total_area, n, r.gross_yield_kn,
                    r.net_rupture_kn, r.block_shear_kn, r.design_strength_kn,
                    bolt.group_capacity_kn, combined, data.force_kn / combined,
                    'Preliminary Satisfies'))
                break
    results.sort(key=lambda r: (r.total_area_mm2, r.bolts, r.section))
    return area_needed_for_yielding, results[:max_results]
