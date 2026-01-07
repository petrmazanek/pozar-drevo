"""
Požární posudek dřevěných nosníků dle ČSN EN 1995-1-2.

Metoda redukovaného průřezu (Reduced cross-section method).
"""
from dataclasses import dataclass
from typing import Literal

from .materials import TimberMaterial
from .sections import RectangularSection
from .loads import LoadCase


# Rychlost zuhelnatění dle ČSN EN 1995-1-2, tab. 3.1 [mm/min]
# β0 = jednorozměrné zuhelnatění (chráněné hrany)
# βn = normové zuhelnatění (včetně zaoblení rohů a trhlin)
CHARRING_RATES: dict[str, dict[str, float]] = {
    "solid": {
        "beta_0": 0.65,  # Rostlé jehličnaté dřevo ρk ≥ 290 kg/m³
        "beta_n": 0.80,
    },
    "glulam": {
        "beta_0": 0.65,  # Lepené lamelové dřevo ρk ≥ 290 kg/m³
        "beta_n": 0.70,
    },
}

# Tloušťka nulové pevnostní vrstvy d0 [mm]
D0 = 7.0

# Součinitel kfi pro přechod na 20% kvantil pevnosti
K_FI = 1.25

# Dílčí součinitel materiálu pro požární situaci
GAMMA_M_FI = 1.0

# Modifikační součinitel kmod,fi dle čl. 4.2.2
KMOD_FI = 1.0


ExposureType = Literal["three_sides", "four_sides"]


@dataclass
class FireExposure:
    """
    Konfigurace požárního namáhání nosníku.

    Attributes:
        duration: Požadovaná požární odolnost [min] (např. 30, 45, 60, 90)
        exposure: Typ vystavení požáru
            - "three_sides": Nosník zapuštěný do stropu (horní hrana chráněna)
            - "four_sides": Nosník volně stojící
        use_beta_n: True = normová rychlost βn, False = jednorozměrná β0
    """
    duration: int  # min (R15, R30, R45, R60, R90, R120)
    exposure: ExposureType = "three_sides"
    use_beta_n: bool = True


@dataclass
class ReducedSection:
    """Redukovaný průřez po požáru."""
    b_fi: float  # Redukovaná šířka [mm]
    h_fi: float  # Redukovaná výška [mm]
    d_char: float  # Hloubka zuhelnatění [mm]
    d_ef: float  # Efektivní hloubka (d_char + d0) [mm]

    @property
    def A_fi(self) -> float:
        """Plocha redukovaného průřezu [mm²]."""
        return self.b_fi * self.h_fi

    @property
    def I_y_fi(self) -> float:
        """Moment setrvačnosti redukovaného průřezu [mm⁴]."""
        return self.b_fi * self.h_fi**3 / 12

    @property
    def W_y_fi(self) -> float:
        """Průřezový modul redukovaného průřezu [mm³]."""
        return self.b_fi * self.h_fi**2 / 6

    @property
    def is_valid(self) -> bool:
        """True pokud průřez není zcela vyhořelý."""
        return self.b_fi > 0 and self.h_fi > 0


@dataclass
class FireCheckResult:
    """Výsledek požárního posudku."""
    name: str
    utilization: float
    stress_d_fi: float  # Návrhové napětí při požáru [MPa]
    strength_d_fi: float  # Návrhová pevnost při požáru [MPa]
    passed: bool

    @property
    def utilization_percent(self) -> float:
        return self.utilization * 100

    def __str__(self) -> str:
        status = "OK" if self.passed else "NEVYHOVUJE"
        return f"{self.name}: {self.utilization_percent:.1f}% [{status}]"


class TimberFireCheck:
    """
    Požární posudek dřevěného nosníku dle ČSN EN 1995-1-2.

    Používá metodu redukovaného průřezu (čl. 4.2.2).
    """

    def __init__(
        self,
        material: TimberMaterial,
        section: RectangularSection,
        load: LoadCase,
        fire: FireExposure,
    ):
        self.mat = material
        self.sec = section
        self.load = load
        self.fire = fire

    @property
    def beta(self) -> float:
        """Rychlost zuhelnatění [mm/min]."""
        rates = CHARRING_RATES[self.mat.timber_type]
        return rates["beta_n"] if self.fire.use_beta_n else rates["beta_0"]

    @property
    def d_char(self) -> float:
        """Hloubka zuhelnatění [mm]."""
        return self.beta * self.fire.duration

    @property
    def d_ef(self) -> float:
        """Efektivní hloubka zuhelnatění [mm] (včetně vrstvy d0)."""
        return self.d_char + D0

    def get_reduced_section(self) -> ReducedSection:
        """
        Vypočte redukovaný průřez.

        Pro three_sides: zuhelnatění ze 3 stran (spodek + 2× bok)
        Pro four_sides: zuhelnatění ze 4 stran
        """
        d_ef = self.d_ef

        if self.fire.exposure == "three_sides":
            # Horní hrana chráněná (zapuštěný nosník)
            b_fi = self.sec.b - 2 * d_ef
            h_fi = self.sec.h - d_ef
        else:  # four_sides
            b_fi = self.sec.b - 2 * d_ef
            h_fi = self.sec.h - 2 * d_ef

        # Zajistit nezáporné hodnoty
        b_fi = max(0, b_fi)
        h_fi = max(0, h_fi)

        return ReducedSection(
            b_fi=b_fi,
            h_fi=h_fi,
            d_char=self.d_char,
            d_ef=d_ef,
        )

    @property
    def fm_d_fi(self) -> float:
        """Návrhová pevnost v ohybu při požáru [MPa]."""
        # f_d,fi = kmod,fi * kfi * f_k / γM,fi
        return KMOD_FI * K_FI * self.mat.fm_k / GAMMA_M_FI

    @property
    def fv_d_fi(self) -> float:
        """Návrhová pevnost ve smyku při požáru [MPa]."""
        return KMOD_FI * K_FI * self.mat.fv_k / GAMMA_M_FI

    @property
    def eta_fi(self) -> float:
        """
        Redukční součinitel účinků zatížení pro požární situaci.

        Zjednodušeně dle čl. 2.4.2: η_fi ≈ 0.6 pro běžné případy
        (poměr kvazistálé kombinace k ULS kombinaci)
        """
        # Přesnější výpočet: η_fi = E_d,fi / E_d
        # kde E_d,fi = G_k + ψ_1,1 * Q_k,1 (mimořádná kombinace)
        # Pro zjednodušení použijeme ψ_1 = 0.5 pro užitná zatížení
        psi_1 = 0.5
        E_d_fi = self.load.g_k + psi_1 * self.load.q_k
        E_d = self.load.q_Ed  # 1.35*G + 1.5*Q

        if E_d > 0:
            return E_d_fi / E_d
        return 0.6

    @property
    def M_Ed_fi(self) -> float:
        """Návrhový moment při požáru [kNm]."""
        return self.eta_fi * self.load.M_Ed

    @property
    def V_Ed_fi(self) -> float:
        """Návrhová posouvající síla při požáru [kN]."""
        return self.eta_fi * self.load.V_Ed

    def check_bending_fire(self) -> FireCheckResult:
        """Posudek na ohyb při požáru."""
        reduced = self.get_reduced_section()

        if not reduced.is_valid:
            return FireCheckResult(
                name="Ohyb (požár)",
                utilization=float("inf"),
                stress_d_fi=float("inf"),
                strength_d_fi=self.fm_d_fi,
                passed=False,
            )

        # σm,d,fi = M_Ed,fi / W_y,fi
        sigma_m_d_fi = self.M_Ed_fi * 1e6 / reduced.W_y_fi

        utilization = sigma_m_d_fi / self.fm_d_fi

        return FireCheckResult(
            name="Ohyb (požár)",
            utilization=utilization,
            stress_d_fi=sigma_m_d_fi,
            strength_d_fi=self.fm_d_fi,
            passed=utilization <= 1.0,
        )

    def check_shear_fire(self) -> FireCheckResult:
        """Posudek na smyk při požáru."""
        reduced = self.get_reduced_section()

        if not reduced.is_valid:
            return FireCheckResult(
                name="Smyk (požár)",
                utilization=float("inf"),
                stress_d_fi=float("inf"),
                strength_d_fi=self.fv_d_fi,
                passed=False,
            )

        # τ_d,fi = 1.5 * V_Ed,fi / A_fi
        # Poznámka: při požáru se kcr neuvažuje (zuhelnatělá vrstva odpadla)
        tau_d_fi = 1.5 * self.V_Ed_fi * 1e3 / reduced.A_fi

        utilization = tau_d_fi / self.fv_d_fi

        return FireCheckResult(
            name="Smyk (požár)",
            utilization=utilization,
            stress_d_fi=tau_d_fi,
            strength_d_fi=self.fv_d_fi,
            passed=utilization <= 1.0,
        )

    def run_all_checks(self) -> dict:
        """Provede všechny požární posudky."""
        reduced = self.get_reduced_section()
        bending = self.check_bending_fire()
        shear = self.check_shear_fire()

        all_passed = bending.passed and shear.passed

        return {
            "reduced_section": reduced,
            "bending": bending,
            "shear": shear,
            "all_passed": all_passed,
            "fire_params": {
                "duration": self.fire.duration,
                "beta": self.beta,
                "d_char": self.d_char,
                "d_ef": self.d_ef,
                "eta_fi": self.eta_fi,
                "M_Ed_fi": self.M_Ed_fi,
                "V_Ed_fi": self.V_Ed_fi,
                "fm_d_fi": self.fm_d_fi,
                "fv_d_fi": self.fv_d_fi,
            },
            "original_section": {
                "b": self.sec.b,
                "h": self.sec.h,
            },
        }


def required_fire_resistance(
    material: TimberMaterial,
    section: RectangularSection,
    load: LoadCase,
    target_duration: int,
    exposure: ExposureType = "three_sides",
) -> dict:
    """
    Ověří, zda průřez splňuje požadovanou požární odolnost.

    Returns:
        Dict s výsledky a případně minimálními rozměry pro splnění.
    """
    fire = FireExposure(duration=target_duration, exposure=exposure)
    check = TimberFireCheck(material, section, load, fire)
    results = check.run_all_checks()

    # Pokud nevyhovuje, spočítáme potřebné zvětšení
    if not results["all_passed"]:
        # Iterativně hledáme minimální průřez
        for delta in range(10, 500, 10):
            test_section = RectangularSection(
                b=section.b + delta,
                h=section.h + delta,
            )
            test_check = TimberFireCheck(material, test_section, load, fire)
            test_results = test_check.run_all_checks()
            if test_results["all_passed"]:
                results["suggested_section"] = {
                    "b": test_section.b,
                    "h": test_section.h,
                    "delta": delta,
                }
                break

    return results
