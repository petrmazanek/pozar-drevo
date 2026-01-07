"""
Průřezové charakteristiky pro dřevěné nosníky.
"""
from dataclasses import dataclass
import math


@dataclass
class RectangularSection:
    """
    Obdélníkový průřez.

    Attributes:
        b: Šířka průřezu [mm]
        h: Výška průřezu [mm]
    """
    b: float  # mm
    h: float  # mm

    def __post_init__(self):
        if self.b <= 0 or self.h <= 0:
            raise ValueError("Rozměry průřezu musí být kladné")

    @property
    def A(self) -> float:
        """Plocha průřezu [mm²]."""
        return self.b * self.h

    @property
    def I_y(self) -> float:
        """Moment setrvačnosti k ose y (ohyb kolem silnější osy) [mm⁴]."""
        return self.b * self.h**3 / 12

    @property
    def I_z(self) -> float:
        """Moment setrvačnosti k ose z (ohyb kolem slabší osy) [mm⁴]."""
        return self.h * self.b**3 / 12

    @property
    def W_y(self) -> float:
        """Průřezový modul k ose y [mm³]."""
        return self.b * self.h**2 / 6

    @property
    def W_z(self) -> float:
        """Průřezový modul k ose z [mm³]."""
        return self.h * self.b**2 / 6

    @property
    def i_y(self) -> float:
        """Poloměr setrvačnosti k ose y [mm]."""
        return self.h / math.sqrt(12)

    @property
    def i_z(self) -> float:
        """Poloměr setrvačnosti k ose z [mm]."""
        return self.b / math.sqrt(12)

    @property
    def I_tor(self) -> float:
        """
        Moment tuhosti v kroucení (St. Venantův) [mm⁴].
        Aproximace pro obdélníkový průřez.
        """
        # Pro h >= b
        a = max(self.h, self.b) / 2
        b = min(self.h, self.b) / 2
        # Aproximace: I_tor ≈ β * a * b³, kde β závisí na poměru a/b
        ratio = a / b
        if ratio <= 1.0:
            beta = 0.141
        elif ratio <= 1.5:
            beta = 0.196
        elif ratio <= 2.0:
            beta = 0.229
        elif ratio <= 3.0:
            beta = 0.263
        elif ratio <= 4.0:
            beta = 0.281
        elif ratio <= 6.0:
            beta = 0.299
        elif ratio <= 10.0:
            beta = 0.312
        else:
            beta = 0.333
        return beta * (2 * a) * (2 * b)**3

    def __str__(self) -> str:
        return f"{self.b:.0f}×{self.h:.0f} mm"

    def __repr__(self) -> str:
        return f"RectangularSection(b={self.b}, h={self.h})"
