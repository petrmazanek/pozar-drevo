"""
Zatížení a kombinace dle ČSN EN 1990.
"""
from dataclasses import dataclass
from typing import Literal


LoadDuration = Literal["permanent", "long_term", "medium_term", "short_term", "instantaneous"]
ServiceClass = Literal[1, 2, 3]


# Součinitel kmod dle ČSN EN 1995-1-1, tab. 3.1
# [třída provozu][doba trvání zatížení]
KMOD_TABLE: dict[ServiceClass, dict[LoadDuration, float]] = {
    1: {
        "permanent": 0.60,
        "long_term": 0.70,
        "medium_term": 0.80,
        "short_term": 0.90,
        "instantaneous": 1.10,
    },
    2: {
        "permanent": 0.60,
        "long_term": 0.70,
        "medium_term": 0.80,
        "short_term": 0.90,
        "instantaneous": 1.10,
    },
    3: {
        "permanent": 0.50,
        "long_term": 0.55,
        "medium_term": 0.65,
        "short_term": 0.70,
        "instantaneous": 0.90,
    },
}

# Součinitel kdef dle ČSN EN 1995-1-1, tab. 3.2
# Pro rostlé dřevo a lepené lamelové dřevo
KDEF_TABLE: dict[ServiceClass, float] = {
    1: 0.60,
    2: 0.80,
    3: 2.00,
}

# Součinitel ψ2 pro kvazistálou kombinaci dle ČSN EN 1990
PSI_2: dict[str, float] = {
    "cat_A": 0.3,   # Obytné budovy
    "cat_B": 0.3,   # Kanceláře
    "cat_C": 0.6,   # Shromažďovací prostory
    "cat_D": 0.6,   # Obchody
    "cat_E": 0.8,   # Sklady
    "cat_H": 0.0,   # Střechy (nepřístupné)
    "snow": 0.0,    # Sníh (< 1000 m n.m.)
    "wind": 0.0,    # Vítr
}


LOAD_DURATION_NAMES: dict[LoadDuration, str] = {
    "permanent": "Stálé",
    "long_term": "Dlouhodobé",
    "medium_term": "Střednědobé",
    "short_term": "Krátkodobé",
    "instantaneous": "Okamžité",
}


@dataclass
class LoadCase:
    """
    Zatěžovací stav pro prostý nosník.

    Attributes:
        g_k: Charakteristické stálé zatížení [kN/m]
        q_k: Charakteristické proměnné zatížení [kN/m]
        span: Rozpětí nosníku [m]
        service_class: Třída provozu (1, 2, 3)
        load_duration: Doba trvání rozhodujícího zatížení
        load_category: Kategorie zatížení pro ψ2
    """
    g_k: float  # kN/m
    q_k: float  # kN/m
    span: float  # m
    service_class: ServiceClass = 1
    load_duration: LoadDuration = "medium_term"
    load_category: str = "cat_A"

    def __post_init__(self):
        if self.g_k < 0:
            raise ValueError("Stálé zatížení g_k nemůže být záporné")
        if self.q_k < 0:
            raise ValueError("Proměnné zatížení q_k nemůže být záporné")
        if self.span <= 0:
            raise ValueError("Rozpětí musí být kladné")

    @property
    def kmod(self) -> float:
        """Modifikační součinitel kmod."""
        return KMOD_TABLE[self.service_class][self.load_duration]

    @property
    def kdef(self) -> float:
        """Součinitel dotvarování kdef."""
        return KDEF_TABLE[self.service_class]

    @property
    def psi_2(self) -> float:
        """Součinitel ψ2 pro kvazistálou kombinaci."""
        return PSI_2.get(self.load_category, 0.3)

    # === Kombinace zatížení ===

    @property
    def q_Ed(self) -> float:
        """Návrhové zatížení pro ULS [kN/m] - kombinace 6.10."""
        return 1.35 * self.g_k + 1.5 * self.q_k

    @property
    def q_char(self) -> float:
        """Charakteristická kombinace pro SLS [kN/m]."""
        return self.g_k + self.q_k

    @property
    def q_quasi(self) -> float:
        """Kvazistálá kombinace pro SLS [kN/m]."""
        return self.g_k + self.psi_2 * self.q_k

    # === Vnitřní síly pro prostý nosník ===

    @property
    def M_Ed(self) -> float:
        """Návrhový ohybový moment [kNm]."""
        return self.q_Ed * self.span**2 / 8

    @property
    def V_Ed(self) -> float:
        """Návrhová posouvající síla [kN]."""
        return self.q_Ed * self.span / 2

    @property
    def M_char(self) -> float:
        """Charakteristický ohybový moment [kNm] - pro SLS."""
        return self.q_char * self.span**2 / 8

    @property
    def M_quasi(self) -> float:
        """Kvazistálý ohybový moment [kNm] - pro průhyb."""
        return self.q_quasi * self.span**2 / 8
