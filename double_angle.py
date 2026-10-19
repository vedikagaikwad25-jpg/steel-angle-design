"""Symmetric, twin-angle BOLTED TENSION teaching model (IS 800:2007).

Supported geometry ONLY: two identical mirrored rolled angles on opposite faces
of ONE common gusset; one continuous line of n through-bolts connects one leg
of each angle and the gusset; same material, gauge, pitch, hole, equal load
sharing; critical shear-lag distance per half is the connected-leg bolt line to
the farthest outstanding-leg edge. Under these assumptions the three *member*
limit-state resistances add, because each angle has the same independent section
and block-shear path. This does NOT verify bolts or the gusset, alternative tear
paths, combined bearing, eccentricity, member slenderness or compression.

IS 800:2007 cl. 6.2, 6.3.4 referring to 6.3.3, 6.4.1.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from engine import Angle, DesignInput, DesignResult, calculate_tension

ARRANGEMENT = (
    'Two identical mirrored angles on opposite faces of a common gusset; '
    'one straight through-bolt line in each connected leg, equal load sharing.'
)
_TOTALS = frozenset((
    'gross_yield_kn', 'net_rupture_kn', 'block_shear_kn',
    'block_case_1_kn', 'block_case_2_kn', 'design_strength_kn',
    'gross_area_mm2', 'connected_net_area_mm2',
    'outstanding_gross_area_mm2', 'avg_mm2', 'avn_mm2',
    'atg_mm2', 'atn_mm2',
))
_UNSCALED = frozenset((
    'beta_raw', 'beta_max', 'beta_used', 'w_mm', 'bs_mm',
    'lc_mm', 'governing_mode',
))


@dataclass(frozen=True)
class DoubleAngleResult:
    angle: Angle
    inputs: DesignInput
    per_angle: DesignResult
    angle_count: int = 2
    arrangement: str = ARRANGEMENT

    def __getattr__(self, name: str):
        if name in _TOTALS:
            return 2.0 * getattr(self.per_angle, name)
        if name in _UNSCALED:
            return getattr(self.per_angle, name)
        raise AttributeError(name)

    def check(self, strength_kn: float) -> bool:
        return self.inputs.force_kn <= strength_kn + 1e-9

    @property
    def overall_pass(self) -> bool:
        return (self.check(self.gross_yield_kn)
                and self.check(self.net_rupture_kn)
                and self.check(self.block_shear_kn))

    @property
    def utilization(self) -> float:
        return self.inputs.force_kn / self.design_strength_kn


def calculate_double_tension(angle: Angle, data: DesignInput) -> DoubleAngleResult:
    """Evaluate symmetric twin angle member only, not the complete joint.

    Whole-member demand is split equally between two *identical* angles.
    Strengths and areas combine; geometry and shear-lag beta are per-angle.
    Must NOT be used for both angles on one gusset side, different sections,
    distinct hole patterns, or any compression configuration.
    """
    per = calculate_tension(angle, replace(data, force_kn=data.force_kn / 2))
    return DoubleAngleResult(angle=angle, inputs=data, per_angle=per)
