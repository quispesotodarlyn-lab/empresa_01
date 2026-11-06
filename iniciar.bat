@echo off
echo === Creaciones GMD ===
echo 1) Abre XAMPP y pulsa START en MySQL
echo 2) Instalando dependencias...
pip install -r requirements.txt
echo 3) Iniciando sistema en http://localhost:5000
start http://localhost:5000
python app.py
pause
