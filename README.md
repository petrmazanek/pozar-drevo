# Posudek dřevěného nosníku

Webová aplikace pro statický posudek prostého dřevěného nosníku dle **ČSN EN 1995-1-1** (Eurokód 5) včetně požární odolnosti dle **ČSN EN 1995-1-2**.

## Funkce

- **Materiály**: Rostlé dřevo (C14-C40), lepené lamelové (GL20h-GL32h)
- **Posudky ULS**: Ohyb, smyk, klopení
- **Posudek SLS**: Průhyb (okamžitý + konečný s dotvarováním)
- **Požární odolnost**: R15 až R120, metoda redukovaného průřezu
- **Export PDF**: Kompletní statický protokol

## Spuštění lokálně

```bash
pip install -r requirements.txt
streamlit run app.py
```

Aplikace bude dostupná na `http://localhost:8501`

## Deployment

Aplikace je připravena pro [Streamlit Cloud](https://streamlit.io/cloud).

## Technologie

- Python 3.10+
- Streamlit
- fpdf2

## Disclaimer

Pro informativní účely. Výsledky ověřte autorizovaným inženýrem.
