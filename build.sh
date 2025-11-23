#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. Instalar librerías
pip install -r requirements.txt

# 2. Recolectar archivos estáticos (CSS, imágenes)
python manage.py collectstatic --no-input

# 3. Crear las tablas en la base de datos (ESTO ARREGLA EL ERROR 500)
python manage.py migrate