"""
Streamlit aplikace pro posudek dřevěných nosníků.
"""
import streamlit as st

from src.materials import load_timber_database, TimberMaterial
from src.sections import RectangularSection
from src.loads import LoadCase, LOAD_DURATION_NAMES, LoadDuration
from src.timber_check import TimberBeamCheck
from src.fire_check import TimberFireCheck, FireExposure, CHARRING_RATES
from src.pdf_report import generate_pdf_report


st.set_page_config(
    page_title="Posudek dřevěného nosníku",
    page_icon="🪵",
    layout="wide",
)

st.title("Posudek dřevěného nosníku")
st.markdown("**Dle ČSN EN 1995-1-1 (Eurokód 5)**")

# === SIDEBAR - metadata pro PDF ===
with st.sidebar:
    st.header("Export PDF")
    project_name = st.text_input("Název projektu", value="")
    author_name = st.text_input("Zpracoval", value="")

st.divider()

# Načtení databáze materiálů
materials_db = load_timber_database()


# === VSTUPNÍ PARAMETRY ===
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Materiál")

    timber_type = st.radio(
        "Typ dřeva",
        ["Rostlé dřevo", "Lepené lamelové"],
        horizontal=True,
    )

    if timber_type == "Rostlé dřevo":
        available_materials = [m for m in materials_db.values() if m.timber_type == "solid"]
    else:
        available_materials = [m for m in materials_db.values() if m.timber_type == "glulam"]

    material_names = [m.name for m in available_materials]
    default_idx = material_names.index("C24") if "C24" in material_names else (
        material_names.index("GL24h") if "GL24h" in material_names else 0
    )

    selected_material_name = st.selectbox(
        "Třída pevnosti",
        material_names,
        index=default_idx,
    )

    material = materials_db[selected_material_name]

    with st.expander("Vlastnosti materiálu"):
        st.markdown(f"""
        | Vlastnost | Hodnota |
        |-----------|---------|
        | fm,k | {material.fm_k} MPa |
        | fv,k | {material.fv_k} MPa |
        | E0,mean | {material.E_0_mean} MPa |
        | ρk | {material.rho_k} kg/m³ |
        | γM | {material.gamma_M} |
        """)


with col2:
    st.subheader("Průřez")

    b = st.number_input("Šířka b [mm]", min_value=40, max_value=500, value=160, step=10)
    h = st.number_input("Výška h [mm]", min_value=80, max_value=2000, value=400, step=20)

    section = RectangularSection(b=float(b), h=float(h))

    with st.expander("Průřezové charakteristiky"):
        st.markdown(f"""
        | Vlastnost | Hodnota |
        |-----------|---------|
        | A | {section.A / 1e4:.2f} cm² |
        | Iy | {section.I_y / 1e8:.2f} × 10⁸ mm⁴ |
        | Wy | {section.W_y / 1e6:.3f} × 10⁶ mm³ |
        """)


with col3:
    st.subheader("Zatížení")

    span = st.number_input("Rozpětí L [m]", min_value=1.0, max_value=20.0, value=5.0, step=0.5)
    g_k = st.number_input("Stálé zatížení gk [kN/m]", min_value=0.0, max_value=50.0, value=2.0, step=0.5)
    q_k = st.number_input("Proměnné zatížení qk [kN/m]", min_value=0.0, max_value=50.0, value=5.0, step=0.5)

    service_class = st.selectbox(
        "Třída provozu",
        [1, 2, 3],
        index=0,
        help="1 = interiér (≤65% vlhkost), 2 = kryté exteriéry, 3 = exteriér",
    )

    duration_options = list(LOAD_DURATION_NAMES.keys())
    duration_labels = list(LOAD_DURATION_NAMES.values())
    duration_idx = st.selectbox(
        "Doba trvání zatížení",
        range(len(duration_options)),
        index=2,  # medium_term
        format_func=lambda i: duration_labels[i],
    )
    load_duration: LoadDuration = duration_options[duration_idx]


# === POKROČILÉ NASTAVENÍ ===
with st.expander("Pokročilé nastavení"):
    col_adv1, col_adv2 = st.columns(2)

    with col_adv1:
        lef_factor = st.number_input(
            "Součinitel efektivní délky pro klopení",
            min_value=0.5,
            max_value=2.0,
            value=1.0,
            step=0.1,
            help="lef = faktor × L",
        )

    with col_adv2:
        deflection_limit = st.selectbox(
            "Limit průhybu L/",
            [150, 200, 250, 300, 350, 400, 500],
            index=3,  # L/300
        )

# === DOKUMENTACE METODY ===
with st.expander("Dokumentace výpočtu (ČSN EN 1995-1-1)"):
    st.markdown("""
### Posudek dřevěného nosníku dle ČSN EN 1995-1-1

#### 1. Návrhové hodnoty pevnosti (čl. 2.4.1)
```
fd = kmod × fk / γM
```

| Součinitel | Popis |
|------------|-------|
| **kmod** | Modifikační součinitel zohledňující vliv trvání zatížení a vlhkosti (tab. 3.1) |
| **γM** | Dílčí součinitel materiálu: 1,3 (rostlé), 1,25 (lepené) |

#### 2. Posudek ohybu (čl. 6.1.6)
```
σm,d = MEd / Wy ≤ fm,d
```

Pro prostý nosník s rovnoměrným zatížením:
```
MEd = qEd × L² / 8
qEd = 1,35×gk + 1,5×qk
```

#### 3. Posudek smyku (čl. 6.1.7)
```
τd = 1,5 × VEd / (kcr × A) ≤ fv,d
```

| Parametr | Hodnota | Význam |
|----------|---------|--------|
| **kcr** | 0,67 | Součinitel trhlin (rostlé i lepené) |
| **VEd** | qEd×L/2 | Posouvající síla na podpoře |

#### 4. Posudek klopení (čl. 6.3.3)
```
σm,d / (kcrit × fm,d) ≤ 1,0
```

**Výpočet kcrit:**
- λrel,m ≤ 0,75: kcrit = 1,0
- 0,75 < λrel,m ≤ 1,4: kcrit = 1,56 - 0,75×λrel,m
- λrel,m > 1,4: kcrit = 1/λrel,m²

**Poměrná štíhlost:**
```
λrel,m = √(fm,k / σm,crit)
σm,crit = 0,78 × b² × E0,05 / (h × lef)
```

#### 5. Posudek průhybu (čl. 7.2)
```
winst = 5 × q × L⁴ / (384 × E × I)
wfin = winst,G × (1+kdef) + winst,Q × (1+ψ2×kdef)
wfin ≤ wlim = L/300
```

| Třída provozu | kdef |
|---------------|------|
| 1 (suchá) | 0,6 |
| 2 (vlhká) | 0,8 |
| 3 (mokrá) | 2,0 |

---
*Statické schéma: Prostý nosník s rovnoměrným spojitým zatížením*
    """)

# === POŽÁRNÍ ODOLNOST ===
with st.expander("Požární odolnost (ČSN EN 1995-1-2)"):
    col_fire1, col_fire2, col_fire3 = st.columns(3)

    with col_fire1:
        fire_enabled = st.checkbox("Posoudit požární odolnost", value=False)

    with col_fire2:
        fire_duration = st.selectbox(
            "Požadovaná odolnost",
            [15, 30, 45, 60, 90, 120],
            index=1,
            format_func=lambda x: f"R {x}",
            disabled=not fire_enabled,
        )

    with col_fire3:
        fire_exposure = st.selectbox(
            "Vystavení požáru",
            ["three_sides", "four_sides"],
            index=0,
            format_func=lambda x: "3 strany (strop)" if x == "three_sides" else "4 strany (volný)",
            disabled=not fire_enabled,
            help="3 strany = nosník zapuštěný do stropu, 4 strany = volně stojící",
        )

    # Dokumentace metody
    with st.container():
        st.markdown("---")
        show_docs = st.checkbox("Zobrazit dokumentaci metody", value=False)
        if show_docs:
            st.markdown("""
### Metoda redukovaného průřezu dle ČSN EN 1995-1-2

#### Princip metody (čl. 4.2.2)
Metoda spočívá ve **zmenšení rozměrů průřezu** o efektivní hloubku zuhelnatění.
Mechanické vlastnosti zbytkového průřezu se uvažují v plné hodnotě.

#### Postup výpočtu

**KROK 1: Rychlost zuhelnatění** (tab. 3.1)

| Materiál | β₀ [mm/min] | βₙ [mm/min] |
|----------|-------------|-------------|
| Rostlé jehličnaté | 0,65 | 0,80 |
| Lepené lamelové | 0,65 | 0,70 |

*βₙ = normová rychlost (zahrnuje vliv zaoblení rohů a trhlin)*

**KROK 2: Hloubka zuhelnatění** (vzorec 3.2)
```
dchar,n = βn × t
```

**KROK 3: Efektivní hloubka** (vzorec 4.1)
```
def = dchar,n + d0
```
kde d₀ = 7 mm (vrstva s nulovými mechanickými vlastnostmi)

**KROK 4: Redukovaný průřez**

*3 strany (nosník v stropu):*
```
bfi = b - 2×def
hfi = h - def
```

*4 strany (volný nosník):*
```
bfi = b - 2×def
hfi = h - 2×def
```

**KROK 5: Redukce zatížení** (vzorec 2.8)
```
Ed,fi = ηfi × Ed
ηfi = (Gk + ψ1×Qk) / (1,35×Gk + 1,5×Qk)
```

**KROK 6: Návrhová pevnost při požáru** (vzorec 4.2)
```
fd,fi = kmod,fi × kfi × fk / γM,fi
```

| Součinitel | Hodnota | Význam |
|------------|---------|--------|
| kmod,fi | 1,0 | Modifikační součinitel |
| kfi | 1,25 | Přechod na 20% kvantil |
| γM,fi | 1,0 | Dílčí součinitel materiálu |

**KROK 7: Posouzení**
```
σm,d,fi = MEd,fi / Wfi ≤ fm,d,fi
τd,fi = 1,5 × VEd,fi / Afi ≤ fv,d,fi
```

---
*Poznámka: Pro finální dokumentaci ověřte výsledky autorizovaným inženýrem.*
            """)


# === VÝPOČET ===
try:
    load = LoadCase(
        g_k=g_k,
        q_k=q_k,
        span=span,
        service_class=service_class,
        load_duration=load_duration,
    )

    check = TimberBeamCheck(
        material=material,
        section=section,
        load=load,
        lef_factor=lef_factor,
        deflection_limit=deflection_limit,
    )

    results = check.run_all_checks()

    st.divider()

    # === VNITŘNÍ SÍLY ===
    st.subheader("Vnitřní síly")
    col_forces1, col_forces2, col_forces3 = st.columns(3)

    with col_forces1:
        st.metric("Návrhové zatížení qEd", f"{load.q_Ed:.2f} kN/m")
    with col_forces2:
        st.metric("Ohybový moment MEd", f"{results['internal_forces']['M_Ed']:.2f} kNm")
    with col_forces3:
        st.metric("Posouvající síla VEd", f"{results['internal_forces']['V_Ed']:.2f} kN")

    st.divider()

    # === POSUDKY ULS ===
    st.subheader("Mezní stav únosnosti (ULS)")

    col_uls1, col_uls2, col_uls3 = st.columns(3)

    def show_check(result, container):
        util = result.utilization_percent
        if util <= 80:
            color = "green"
            icon = "✅"
        elif util <= 100:
            color = "orange"
            icon = "⚠️"
        else:
            color = "red"
            icon = "❌"

        container.markdown(f"### {icon} {result.name}")
        container.progress(min(util / 100, 1.0))
        container.markdown(f"**Využití: {util:.1f}%**")
        container.caption(f"σd = {result.stress_d:.2f} MPa ≤ fd = {result.strength_d:.2f} MPa")

    show_check(results["bending"], col_uls1)
    show_check(results["shear"], col_uls2)
    show_check(results["lateral_torsional_buckling"], col_uls3)

    # Dodatečné info o klopení
    with col_uls3.expander("Detaily klopení"):
        dv = results["design_values"]
        st.markdown(f"""
        - λrel,m = {dv['lambda_rel_m']:.3f}
        - kcrit = {dv['kcrit']:.3f}
        - kmod = {dv['kmod']:.2f}
        """)

    st.divider()

    # === POSUDEK SLS ===
    st.subheader("Mezní stav použitelnosti (SLS)")

    defl = results["deflection"]
    util = defl.utilization_percent

    if util <= 80:
        icon = "✅"
    elif util <= 100:
        icon = "⚠️"
    else:
        icon = "❌"

    col_sls1, col_sls2 = st.columns([2, 1])

    with col_sls1:
        st.markdown(f"### {icon} Průhyb")
        st.progress(min(util / 100, 1.0))
        st.markdown(f"**Využití: {util:.1f}%**")
        st.markdown(f"""
        - Okamžitý průhyb: **winst = {defl.w_inst:.1f} mm**
        - Konečný průhyb: **wfin = {defl.w_fin:.1f} mm** ≤ wlim = {defl.w_limit:.1f} mm (L/{defl.limit_ratio})
        """)

    with col_sls2:
        st.metric("kdef", f"{load.kdef:.2f}")

    # === POŽÁRNÍ POSUDEK ===
    if fire_enabled:
        st.divider()
        st.subheader(f"Požární odolnost R {fire_duration}")

        fire_exposure_obj = FireExposure(
            duration=fire_duration,
            exposure=fire_exposure,
        )
        fire_check = TimberFireCheck(material, section, load, fire_exposure_obj)
        fire_results = fire_check.run_all_checks()

        reduced = fire_results["reduced_section"]
        fp = fire_results["fire_params"]

        # Info o zuhelnatění
        col_char1, col_char2, col_char3 = st.columns(3)
        with col_char1:
            st.metric("Rychlost zuhelnatění βn", f"{fp['beta']:.2f} mm/min")
        with col_char2:
            st.metric("Hloubka zuhelnatění dchar", f"{fp['d_char']:.1f} mm")
        with col_char3:
            st.metric("Efektivní hloubka def", f"{fp['d_ef']:.1f} mm")

        # Redukovaný průřez
        st.markdown("**Redukovaný průřez:**")
        col_red1, col_red2, col_red3 = st.columns(3)
        with col_red1:
            st.metric(
                "Šířka bfi",
                f"{reduced.b_fi:.0f} mm",
                delta=f"-{section.b - reduced.b_fi:.0f} mm",
                delta_color="inverse",
            )
        with col_red2:
            st.metric(
                "Výška hfi",
                f"{reduced.h_fi:.0f} mm",
                delta=f"-{section.h - reduced.h_fi:.0f} mm",
                delta_color="inverse",
            )
        with col_red3:
            reduction_pct = (1 - reduced.A_fi / section.A) * 100 if section.A > 0 else 100
            st.metric("Redukce plochy", f"{reduction_pct:.1f}%")

        # Posudky při požáru
        if reduced.is_valid:
            st.markdown("**Posudky při požáru:**")
            col_fire_uls1, col_fire_uls2 = st.columns(2)

            def show_fire_check(result, container):
                util = result.utilization_percent
                if util <= 80:
                    icon = "✅"
                elif util <= 100:
                    icon = "⚠️"
                else:
                    icon = "❌"

                container.markdown(f"### {icon} {result.name}")
                container.progress(min(util / 100, 1.0))
                container.markdown(f"**Využití: {util:.1f}%**")
                container.caption(f"σd,fi = {result.stress_d_fi:.2f} MPa ≤ fd,fi = {result.strength_d_fi:.2f} MPa")

            show_fire_check(fire_results["bending"], col_fire_uls1)
            show_fire_check(fire_results["shear"], col_fire_uls2)

            # Info o redukci zatížení
            with st.expander("Detaily požárního výpočtu"):
                st.markdown(f"""
                | Parametr | Hodnota |
                |----------|---------|
                | ηfi (redukce zatížení) | {fp['eta_fi']:.3f} |
                | MEd,fi | {fp['M_Ed_fi']:.2f} kNm |
                | VEd,fi | {fp['V_Ed_fi']:.2f} kN |
                | fm,d,fi | {fp['fm_d_fi']:.2f} MPa |
                | fv,d,fi | {fp['fv_d_fi']:.2f} MPa |
                | kfi | 1.25 |
                | γM,fi | 1.0 |
                """)
        else:
            st.error(f"Průřez je při R {fire_duration} zcela vyhořelý!")

    st.divider()

    # === SOUHRN ===
    all_checks_passed = results["all_passed"]
    summary_parts = [f"ULS: {results['max_uls_utilization']*100:.1f}%"]

    if fire_enabled:
        fire_passed = fire_results["all_passed"] and fire_results["reduced_section"].is_valid
        all_checks_passed = all_checks_passed and fire_passed
        if fire_passed:
            max_fire_util = max(
                fire_results["bending"].utilization,
                fire_results["shear"].utilization,
            )
            summary_parts.append(f"Požár R{fire_duration}: {max_fire_util*100:.1f}%")
        else:
            summary_parts.append(f"Požár R{fire_duration}: NEVYHOVUJE")

    summary_text = " | ".join(summary_parts)

    if all_checks_passed:
        st.success(f"**NOSNÍK VYHOVUJE** | {summary_text}")
    else:
        st.error(f"**NOSNÍK NEVYHOVUJE** | {summary_text}")

    # === EXPORT PDF ===
    st.divider()

    # Připravit data pro PDF
    fire_results_for_pdf = None
    fire_duration_for_pdf = None
    if fire_enabled:
        fire_results_for_pdf = fire_results
        fire_duration_for_pdf = fire_duration

    # Generovat PDF
    pdf_bytes = generate_pdf_report(
        material=material,
        section=section,
        load=load,
        results=results,
        fire_results=fire_results_for_pdf,
        fire_duration=fire_duration_for_pdf,
        project_name=project_name,
        author=author_name,
    )

    # Název souboru
    filename = f"posudek_{material.name}_{section.b:.0f}x{section.h:.0f}"
    if fire_enabled:
        filename += f"_R{fire_duration}"
    filename += ".pdf"

    st.download_button(
        label="Stáhnout PDF protokol",
        data=pdf_bytes,
        file_name=filename,
        mime="application/pdf",
        type="primary",
    )

except Exception as e:
    st.error(f"Chyba výpočtu: {e}")


# === FOOTER ===
st.divider()
st.caption("Posudek dle ČSN EN 1995-1-1 a ČSN EN 1995-1-2. Pro informativní účely - ověřte autorizovaným inženýrem.")
