"""
Materiálové modely pro dřevo dle ČSN EN 338 a ČSN EN 14080.
"""
from dataclasses import dataclass
from typing import Literal
from pathlib import Path
import yaml


TimberType = Literal["solid", "glulam"]


@dataclass
class TimberMaterial:
    """Třída pevnosti dřeva."""
    name: str
    timber_type: TimberType
    fm_k: float       # Charakteristická pevnost v ohybu [MPa]
    ft_0_k: float     # Pevnost v tahu rovnoběžně [MPa]
    fv_k: float       # Pevnost ve smyku [MPa]
    E_0_mean: float   # Střední modul pružnosti [MPa]
    E_0_05: float     # 5% kvantil modulu pružnosti [MPa]
    rho_k: float      # Charakteristická hustota [kg/m³]
    rho_mean: float   # Střední hustota [kg/m³]

    @property
    def gamma_M(self) -> float:
        """Dílčí součinitel materiálu γM dle ČSN EN 1995-1-1, tab. 2.3."""
        if self.timber_type == "solid":
            return 1.3
        else:  # glulam
            return 1.25

    @property
    def kcr(self) -> float:
        """Součinitel pro redukci průřezu při smyku (trhliny)."""
        if self.timber_type == "solid":
            return 0.67
        else:  # glulam
            return 0.67  # Stejná hodnota pro lepené dřevo


def load_timber_database(yaml_path: Path | None = None) -> dict[str, TimberMaterial]:
    """
    Načte databázi materiálů z YAML souboru.

    Returns:
        Dict s klíčem = název třídy (např. "C24", "GL24h")
    """
    if yaml_path is None:
        yaml_path = Path(__file__).parent.parent / "data" / "timber_classes.yaml"

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    materials: dict[str, TimberMaterial] = {}

    # Rostlé dřevo
    for name, props in data.get("solid_timber", {}).items():
        materials[name] = TimberMaterial(
            name=name,
            timber_type="solid",
            fm_k=props["fm_k"],
            ft_0_k=props["ft_0_k"],
            fv_k=props["fv_k"],
            E_0_mean=props["E_0_mean"],
            E_0_05=props["E_0_05"],
            rho_k=props["rho_k"],
            rho_mean=props["rho_mean"],
        )

    # Lepené lamelové
    for name, props in data.get("glulam", {}).items():
        materials[name] = TimberMaterial(
            name=name,
            timber_type="glulam",
            fm_k=props["fm_k"],
            ft_0_k=props["ft_0_k"],
            fv_k=props["fv_k"],
            E_0_mean=props["E_0_mean"],
            E_0_05=props["E_0_05"],
            rho_k=props["rho_k"],
            rho_mean=props["rho_mean"],
        )

    return materials


def get_material(name: str) -> TimberMaterial:
    """Získá materiál podle názvu."""
    db = load_timber_database()
    if name not in db:
        raise ValueError(f"Neznámá třída dřeva: {name}. Dostupné: {list(db.keys())}")
    return db[name]


def list_materials(timber_type: TimberType | None = None) -> list[str]:
    """Vrátí seznam dostupných materiálů."""
    db = load_timber_database()
    if timber_type is None:
        return list(db.keys())
    return [name for name, mat in db.items() if mat.timber_type == timber_type]
