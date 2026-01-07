"""
Generování PDF protokolu pro posudek dřevěného nosníku.
"""
from io import BytesIO
from datetime import datetime
from dataclasses import dataclass
from typing import Any
import unicodedata

from fpdf import FPDF

from .materials import TimberMaterial
from .sections import RectangularSection
from .loads import LoadCase, LOAD_DURATION_NAMES


def remove_diacritics(text: str) -> str:
    """Odstraní diakritiku z textu pro kompatibilitu s Helvetica fontem."""
    # Speciální české znaky
    replacements = {
        'ě': 'e', 'š': 's', 'č': 'c', 'ř': 'r', 'ž': 'z', 'ý': 'y', 'á': 'a',
        'í': 'i', 'é': 'e', 'ú': 'u', 'ů': 'u', 'ť': 't', 'ď': 'd', 'ň': 'n',
        'Ě': 'E', 'Š': 'S', 'Č': 'C', 'Ř': 'R', 'Ž': 'Z', 'Ý': 'Y', 'Á': 'A',
        'Í': 'I', 'É': 'E', 'Ú': 'U', 'Ů': 'U', 'Ť': 'T', 'Ď': 'D', 'Ň': 'N',
    }
    for cz, ascii_char in replacements.items():
        text = text.replace(cz, ascii_char)
    return text


class TimberReportPDF(FPDF):
    """PDF protokol s podporou češtiny."""

    def __init__(self):
        super().__init__()
        self.add_page()
        # Použijeme vestavěný Helvetica font (bez diakritiky)
        # Pro plnou češtinu by bylo potřeba přidat TTF font
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "Staticky posudek dreveneho nosniku", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, "dle CSN EN 1995-1-1 a CSN EN 1995-1-2", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Strana {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title: str):
        """Nadpis sekce."""
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 8, title, fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def add_row(self, label: str, value: str, unit: str = ""):
        """Řádek s popisem a hodnotou."""
        self.set_font("Helvetica", "", 10)
        col_width = 60
        self.cell(col_width, 6, label, new_x="RIGHT")
        self.set_font("Helvetica", "B", 10)
        if unit:
            self.cell(40, 6, value, new_x="RIGHT")
            self.set_font("Helvetica", "", 10)
            self.cell(30, 6, unit, new_x="LMARGIN", new_y="NEXT")
        else:
            self.cell(70, 6, value, new_x="LMARGIN", new_y="NEXT")

    def add_check_result(self, name: str, utilization: float, stress: float, strength: float, passed: bool):
        """Výsledek posudku s progress barem."""
        self.set_font("Helvetica", "", 10)

        # Název posudku
        self.cell(40, 6, name, new_x="RIGHT")

        # Progress bar
        bar_width = 50
        bar_height = 5
        x = self.get_x()
        y = self.get_y()

        # Pozadí
        self.set_fill_color(220, 220, 220)
        self.rect(x, y, bar_width, bar_height, "F")

        # Výplň podle využití
        fill_width = min(utilization, 1.0) * bar_width
        if utilization <= 0.8:
            self.set_fill_color(76, 175, 80)  # Zelená
        elif utilization <= 1.0:
            self.set_fill_color(255, 152, 0)  # Oranžová
        else:
            self.set_fill_color(244, 67, 54)  # Červená
        self.rect(x, y, fill_width, bar_height, "F")

        self.set_xy(x + bar_width + 5, y)

        # Využití
        status = "OK" if passed else "!"
        self.set_font("Helvetica", "B", 10)
        self.cell(25, 6, f"{utilization*100:.1f}% [{status}]", new_x="RIGHT")

        # Napětí
        self.set_font("Helvetica", "", 9)
        self.cell(50, 6, f"({stress:.2f} / {strength:.2f} MPa)", new_x="LMARGIN", new_y="NEXT")

    def add_table(self, headers: list[str], rows: list[list[str]], col_widths: list[int] | None = None):
        """Tabulka s daty."""
        if col_widths is None:
            col_widths = [190 // len(headers)] * len(headers)

        # Hlavička
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(200, 200, 200)
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 7, header, border=1, fill=True, align="C")
        self.ln()

        # Data
        self.set_font("Helvetica", "", 9)
        for row in rows:
            for i, cell in enumerate(row):
                self.cell(col_widths[i], 6, cell, border=1, align="C")
            self.ln()


def generate_pdf_report(
    material: TimberMaterial,
    section: RectangularSection,
    load: LoadCase,
    results: dict[str, Any],
    fire_results: dict[str, Any] | None = None,
    fire_duration: int | None = None,
    project_name: str = "",
    author: str = "",
) -> bytes:
    """
    Generuje PDF protokol.

    Returns:
        PDF jako bytes pro stažení.
    """
    pdf = TimberReportPDF()
    pdf.alias_nb_pages()

    # === HLAVIČKA ===
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(95, 6, f"Projekt: {remove_diacritics(project_name) or '-'}", new_x="RIGHT")
    pdf.cell(95, 6, f"Datum: {datetime.now().strftime('%d.%m.%Y')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(95, 6, f"Zpracoval: {remove_diacritics(author) or '-'}", new_x="RIGHT")
    pdf.cell(95, 6, "", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # === VSTUPNÍ ÚDAJE ===
    pdf.section_title("1. Vstupni udaje")

    # Materiál
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Material:", new_x="LMARGIN", new_y="NEXT")
    pdf.add_row("Trida pevnosti:", material.name)
    pdf.add_row("Typ dreva:", "Rostle" if material.timber_type == "solid" else "Lepene lamelove")
    pdf.add_row("fm,k =", f"{material.fm_k}", "MPa")
    pdf.add_row("fv,k =", f"{material.fv_k}", "MPa")
    pdf.add_row("E0,mean =", f"{material.E_0_mean}", "MPa")
    pdf.add_row("Gamma_M =", f"{material.gamma_M}")
    pdf.ln(3)

    # Průřez
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Prurez:", new_x="LMARGIN", new_y="NEXT")
    pdf.add_row("Sirka b =", f"{section.b:.0f}", "mm")
    pdf.add_row("Vyska h =", f"{section.h:.0f}", "mm")
    pdf.add_row("Plocha A =", f"{section.A/100:.1f}", "cm2")
    pdf.add_row("Moment setrv. Iy =", f"{section.I_y/1e4:.1f}", "cm4")
    pdf.add_row("Prurez. modul Wy =", f"{section.W_y/1e3:.1f}", "cm3")
    pdf.ln(3)

    # Zatížení
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Zatizeni a geometrie:", new_x="LMARGIN", new_y="NEXT")
    pdf.add_row("Rozpeti L =", f"{load.span:.2f}", "m")
    pdf.add_row("Stale zatizeni gk =", f"{load.g_k:.2f}", "kN/m")
    pdf.add_row("Promenne zatizeni qk =", f"{load.q_k:.2f}", "kN/m")
    pdf.add_row("Trida provozu:", f"{load.service_class}")
    pdf.add_row("Doba trvani zatizeni:", remove_diacritics(LOAD_DURATION_NAMES.get(load.load_duration, load.load_duration)))
    pdf.add_row("kmod =", f"{load.kmod:.2f}")
    pdf.ln(5)

    # === VNITŘNÍ SÍLY ===
    pdf.section_title("2. Vnitrni sily (prosty nosnik)")

    pdf.add_row("Navrhove zatizeni qEd =", f"{load.q_Ed:.2f}", "kN/m")
    pdf.add_row("(1.35*gk + 1.5*qk)", "")
    pdf.ln(2)
    pdf.add_row("Ohybovy moment MEd =", f"{results['internal_forces']['M_Ed']:.2f}", "kNm")
    pdf.add_row("(qEd * L^2 / 8)", "")
    pdf.ln(2)
    pdf.add_row("Posouvajici sila VEd =", f"{results['internal_forces']['V_Ed']:.2f}", "kN")
    pdf.add_row("(qEd * L / 2)", "")
    pdf.ln(5)

    # === POSUDEK ULS ===
    pdf.section_title("3. Mezni stav unosnosti (ULS)")

    dv = results["design_values"]
    pdf.add_row("fm,d = kmod * fm,k / Gamma_M =", f"{dv['fm_d']:.2f}", "MPa")
    pdf.add_row("fv,d = kmod * fv,k / Gamma_M =", f"{dv['fv_d']:.2f}", "MPa")
    pdf.ln(3)

    # Ohyb
    bending = results["bending"]
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Posudek na ohyb (cl. 6.1.6):", new_x="LMARGIN", new_y="NEXT")
    pdf.add_check_result(
        "sigma_m,d / fm,d",
        bending.utilization,
        bending.stress_d,
        bending.strength_d,
        bending.passed,
    )
    pdf.ln(2)

    # Smyk
    shear = results["shear"]
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Posudek na smyk (cl. 6.1.7):", new_x="LMARGIN", new_y="NEXT")
    pdf.add_check_result(
        "tau_d / fv,d",
        shear.utilization,
        shear.stress_d,
        shear.strength_d,
        shear.passed,
    )
    pdf.ln(2)

    # Klopení
    ltb = results["lateral_torsional_buckling"]
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Posudek na klopeni (cl. 6.3.3):", new_x="LMARGIN", new_y="NEXT")
    pdf.add_row("lambda_rel,m =", f"{dv['lambda_rel_m']:.3f}")
    pdf.add_row("kcrit =", f"{dv['kcrit']:.3f}")
    pdf.add_check_result(
        "sigma_m,d / (kcrit*fm,d)",
        ltb.utilization,
        ltb.stress_d,
        ltb.strength_d,
        ltb.passed,
    )
    pdf.ln(5)

    # === POSUDEK SLS ===
    pdf.section_title("4. Mezni stav pouzitelnosti (SLS)")

    defl = results["deflection"]
    pdf.add_row("Okamzity pruhyb w_inst =", f"{defl.w_inst:.1f}", "mm")
    pdf.add_row("kdef =", f"{load.kdef:.2f}")
    pdf.add_row("Konecny pruhyb w_fin =", f"{defl.w_fin:.1f}", "mm")
    pdf.add_row("Limitni pruhyb w_lim = L/", f"{defl.limit_ratio} = {defl.w_limit:.1f}", "mm")
    pdf.ln(2)

    status = "VYHOVUJE" if defl.passed else "NEVYHOVUJE"
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, f"Posudek pruhybu: {defl.utilization_percent:.1f}% - {status}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # === POŽÁRNÍ ODOLNOST ===
    if fire_results and fire_duration:
        pdf.section_title(f"5. Pozarni odolnost R {fire_duration} (CSN EN 1995-1-2)")

        fp = fire_results["fire_params"]
        rs = fire_results["reduced_section"]

        pdf.add_row("Rychlost zuhelnateni beta_n =", f"{fp['beta']:.2f}", "mm/min")
        pdf.add_row("Doba pozaru t =", f"{fire_duration}", "min")
        pdf.add_row("Hloubka zuhelnateni d_char =", f"{fp['d_char']:.1f}", "mm")
        pdf.add_row("Nulova vrstva d0 =", "7.0", "mm")
        pdf.add_row("Efektivni hloubka d_ef =", f"{fp['d_ef']:.1f}", "mm")
        pdf.ln(3)

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "Redukovany prurez:", new_x="LMARGIN", new_y="NEXT")
        pdf.add_row("b_fi =", f"{rs.b_fi:.0f}", "mm")
        pdf.add_row("h_fi =", f"{rs.h_fi:.0f}", "mm")

        if rs.is_valid:
            pdf.add_row("A_fi =", f"{rs.A_fi/100:.1f}", "cm2")
            pdf.ln(3)

            pdf.add_row("Redukce zatizeni eta_fi =", f"{fp['eta_fi']:.3f}")
            pdf.add_row("M_Ed,fi =", f"{fp['M_Ed_fi']:.2f}", "kNm")
            pdf.add_row("V_Ed,fi =", f"{fp['V_Ed_fi']:.2f}", "kN")
            pdf.ln(2)

            pdf.add_row("fm,d,fi = kmod,fi * kfi * fm,k / Gamma_M,fi =", f"{fp['fm_d_fi']:.2f}", "MPa")
            pdf.add_row("fv,d,fi =", f"{fp['fv_d_fi']:.2f}", "MPa")
            pdf.ln(3)

            # Posudky
            fire_bending = fire_results["bending"]
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, "Posudek na ohyb pri pozaru:", new_x="LMARGIN", new_y="NEXT")
            pdf.add_check_result(
                "sigma_m,d,fi / fm,d,fi",
                fire_bending.utilization,
                fire_bending.stress_d_fi,
                fire_bending.strength_d_fi,
                fire_bending.passed,
            )
            pdf.ln(2)

            fire_shear = fire_results["shear"]
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, "Posudek na smyk pri pozaru:", new_x="LMARGIN", new_y="NEXT")
            pdf.add_check_result(
                "tau_d,fi / fv,d,fi",
                fire_shear.utilization,
                fire_shear.stress_d_fi,
                fire_shear.strength_d_fi,
                fire_shear.passed,
            )
        else:
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(255, 0, 0)
            pdf.cell(0, 6, "PRUREZ JE PRI POZARU ZCELA VYHORENY!", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)

        pdf.ln(5)

    # === ZÁVĚR ===
    section_num = 6 if fire_results else 5
    pdf.section_title(f"{section_num}. Zaver")

    all_passed = results["all_passed"]
    if fire_results:
        all_passed = all_passed and fire_results["all_passed"] and fire_results["reduced_section"].is_valid

    pdf.set_font("Helvetica", "B", 12)
    if all_passed:
        pdf.set_text_color(0, 128, 0)
        pdf.cell(0, 10, "NOSNIK VYHOVUJE", align="C", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 10, "NOSNIK NEVYHOVUJE", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)

    pdf.ln(3)
    pdf.set_font("Helvetica", "", 9)
    pdf.add_table(
        ["Posudek", "Vyuziti", "Stav"],
        [
            ["Ohyb (ULS)", f"{results['bending'].utilization_percent:.1f}%",
             "OK" if results['bending'].passed else "!"],
            ["Smyk (ULS)", f"{results['shear'].utilization_percent:.1f}%",
             "OK" if results['shear'].passed else "!"],
            ["Klopeni (ULS)", f"{results['lateral_torsional_buckling'].utilization_percent:.1f}%",
             "OK" if results['lateral_torsional_buckling'].passed else "!"],
            ["Pruhyb (SLS)", f"{results['deflection'].utilization_percent:.1f}%",
             "OK" if results['deflection'].passed else "!"],
        ] + (
            [
                [f"Ohyb R{fire_duration}", f"{fire_results['bending'].utilization_percent:.1f}%",
                 "OK" if fire_results['bending'].passed else "!"],
                [f"Smyk R{fire_duration}", f"{fire_results['shear'].utilization_percent:.1f}%",
                 "OK" if fire_results['shear'].passed else "!"],
            ] if fire_results and fire_results["reduced_section"].is_valid else []
        ),
        [80, 50, 60],
    )

    # Generování PDF do paměti
    return bytes(pdf.output())
