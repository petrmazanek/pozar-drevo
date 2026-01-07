"""
Posudky dřevěných nosníků dle ČSN EN 1995-1-1 (Eurokód 5).
"""
from dataclasses import dataclass
import math

from .materials import TimberMaterial
from .sections import RectangularSection
from .loads import LoadCase


@dataclass
class CheckResult:
    """Výsledek posudku."""
    name: str
    utilization: float  # Využití [-]
    stress_d: float     # Návrhové napětí [MPa]
    strength_d: float   # Návrhová pevnost [MPa]
    passed: bool

    @property
    def utilization_percent(self) -> float:
        return self.utilization * 100

    def __str__(self) -> str:
        status = "OK" if self.passed else "NEVYHOVUJE"
        return f"{self.name}: {self.utilization_percent:.1f}% [{status}]"


@dataclass
class DeflectionResult:
    """Výsledek posudku průhybu."""
    w_inst: float      # Okamžitý průhyb [mm]
    w_fin: float       # Konečný průhyb [mm]
    w_limit: float     # Limitní průhyb [mm]
    limit_ratio: int   # L/xxx
    passed: bool

    @property
    def utilization(self) -> float:
        return self.w_fin / self.w_limit

    @property
    def utilization_percent(self) -> float:
        return self.utilization * 100

    def __str__(self) -> str:
        status = "OK" if self.passed else "NEVYHOVUJE"
        return f"Průhyb: {self.w_fin:.1f} mm ≤ {self.w_limit:.1f} mm (L/{self.limit_ratio}) [{status}]"


class TimberBeamCheck:
    """
    Posudek dřevěného nosníku dle EC5.

    Předpokládá prostý nosník s rovnoměrným zatížením.
    """

    def __init__(
        self,
        material: TimberMaterial,
        section: RectangularSection,
        load: LoadCase,
        lef_factor: float = 1.0,
        deflection_limit: int = 300,
    ):
        """
        Args:
            material: Materiál (třída pevnosti dřeva)
            section: Průřez nosníku
            load: Zatěžovací stav
            lef_factor: Součinitel efektivní délky pro klopení (lef = factor * L)
            deflection_limit: Limit průhybu jako L/xxx (default L/300)
        """
        self.mat = material
        self.sec = section
        self.load = load
        self.lef_factor = lef_factor
        self.deflection_limit = deflection_limit

    # === Návrhové pevnosti ===

    @property
    def fm_d(self) -> float:
        """Návrhová pevnost v ohybu [MPa]."""
        return self.load.kmod * self.mat.fm_k / self.mat.gamma_M

    @property
    def fv_d(self) -> float:
        """Návrhová pevnost ve smyku [MPa]."""
        return self.load.kmod * self.mat.fv_k / self.mat.gamma_M

    # === Posudek ohybu (čl. 6.1.6) ===

    def check_bending(self) -> CheckResult:
        """Posudek na ohyb."""
        # M_Ed v kNm -> Nm, W_y v mm³
        # σ = M / W = (M * 10^6 Nmm) / (W mm³) = M * 10^6 / W [MPa]
        sigma_m_d = self.load.M_Ed * 1e6 / self.sec.W_y  # MPa

        utilization = sigma_m_d / self.fm_d

        return CheckResult(
            name="Ohyb",
            utilization=utilization,
            stress_d=sigma_m_d,
            strength_d=self.fm_d,
            passed=utilization <= 1.0,
        )

    # === Posudek smyku (čl. 6.1.7) ===

    def check_shear(self) -> CheckResult:
        """Posudek na smyk."""
        # τ = 1.5 * V / (kcr * A)
        # V_Ed v kN -> N, A v mm²
        tau_d = 1.5 * self.load.V_Ed * 1e3 / (self.mat.kcr * self.sec.A)  # MPa

        utilization = tau_d / self.fv_d

        return CheckResult(
            name="Smyk",
            utilization=utilization,
            stress_d=tau_d,
            strength_d=self.fv_d,
            passed=utilization <= 1.0,
        )

    # === Posudek klopení (čl. 6.3.3) ===

    def _calc_sigma_m_crit(self) -> float:
        """
        Kritické napětí v ohybu pro klopení [MPa].
        Zjednodušený výpočet dle čl. 6.3.3.
        """
        # Efektivní délka
        lef = self.lef_factor * self.load.span * 1000  # mm

        # Pro obdélníkový průřez: σm,crit = 0.78 * b² * E_0.05 / (h * lef)
        sigma_m_crit = (
            0.78 * self.sec.b**2 * self.mat.E_0_05 / (self.sec.h * lef)
        )
        return sigma_m_crit

    def _calc_lambda_rel_m(self) -> float:
        """Poměrná štíhlost pro klopení [-]."""
        sigma_m_crit = self._calc_sigma_m_crit()
        return math.sqrt(self.mat.fm_k / sigma_m_crit)

    def _calc_kcrit(self) -> float:
        """Součinitel klopení kcrit [-]."""
        lambda_rel_m = self._calc_lambda_rel_m()

        if lambda_rel_m <= 0.75:
            return 1.0
        elif lambda_rel_m <= 1.4:
            return 1.56 - 0.75 * lambda_rel_m
        else:
            return 1.0 / lambda_rel_m**2

    def check_lateral_torsional_buckling(self) -> CheckResult:
        """Posudek na klopení."""
        kcrit = self._calc_kcrit()

        # σm,d / (kcrit * fm,d) ≤ 1.0
        sigma_m_d = self.load.M_Ed * 1e6 / self.sec.W_y
        fm_d_red = kcrit * self.fm_d

        utilization = sigma_m_d / fm_d_red

        return CheckResult(
            name="Klopení",
            utilization=utilization,
            stress_d=sigma_m_d,
            strength_d=fm_d_red,
            passed=utilization <= 1.0,
        )

    # === Posudek průhybu (čl. 7.2) ===

    def check_deflection(self) -> DeflectionResult:
        """Posudek průhybu (SLS)."""
        # w = 5 * q * L^4 / (384 * E * I)
        # q v kN/m -> N/mm, L v m -> mm, E v MPa, I v mm⁴

        L_mm = self.load.span * 1000
        q_char_N_mm = self.load.q_char  # kN/m = N/mm (1:1 konverze)

        # Okamžitý průhyb od charakteristické kombinace
        w_inst = (
            5 * q_char_N_mm * L_mm**4
            / (384 * self.mat.E_0_mean * self.sec.I_y)
        )

        # Konečný průhyb včetně dotvarování
        # Zjednodušeně: w_fin = w_inst,G * (1 + kdef) + w_inst,Q * (1 + ψ2 * kdef)
        # Pro jednoduchost aproximace:
        q_g_ratio = self.load.g_k / self.load.q_char if self.load.q_char > 0 else 1.0
        q_q_ratio = self.load.q_k / self.load.q_char if self.load.q_char > 0 else 0.0

        w_fin = w_inst * (
            q_g_ratio * (1 + self.load.kdef)
            + q_q_ratio * (1 + self.load.psi_2 * self.load.kdef)
        )

        w_limit = L_mm / self.deflection_limit

        return DeflectionResult(
            w_inst=w_inst,
            w_fin=w_fin,
            w_limit=w_limit,
            limit_ratio=self.deflection_limit,
            passed=w_fin <= w_limit,
        )

    # === Souhrnný výpočet ===

    def run_all_checks(self) -> dict:
        """Provede všechny posudky a vrátí výsledky."""
        bending = self.check_bending()
        shear = self.check_shear()
        ltb = self.check_lateral_torsional_buckling()
        deflection = self.check_deflection()

        all_passed = all([
            bending.passed,
            shear.passed,
            ltb.passed,
            deflection.passed,
        ])

        max_uls_util = max(
            bending.utilization,
            shear.utilization,
            ltb.utilization,
        )

        return {
            "bending": bending,
            "shear": shear,
            "lateral_torsional_buckling": ltb,
            "deflection": deflection,
            "all_passed": all_passed,
            "max_uls_utilization": max_uls_util,
            "internal_forces": {
                "M_Ed": self.load.M_Ed,
                "V_Ed": self.load.V_Ed,
            },
            "design_values": {
                "kmod": self.load.kmod,
                "gamma_M": self.mat.gamma_M,
                "fm_d": self.fm_d,
                "fv_d": self.fv_d,
                "kcrit": self._calc_kcrit(),
                "lambda_rel_m": self._calc_lambda_rel_m(),
            },
        }
