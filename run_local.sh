#!/bin/bash
# Spuštění aplikace v lokální síti

cd "$(dirname "$0")"

# Aktivace venv pokud existuje
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Zjistit IP adresu
IP=$(hostname -I | awk '{print $1}')

echo "=========================================="
echo "  Posudek dřevěného nosníku"
echo "=========================================="
echo ""
echo "  Lokální přístup:  http://localhost:8501"
echo "  Síťový přístup:   http://$IP:8501"
echo ""
echo "=========================================="
echo ""

streamlit run app.py \
    --server.address 0.0.0.0 \
    --server.port 8501 \
    --server.headless true
