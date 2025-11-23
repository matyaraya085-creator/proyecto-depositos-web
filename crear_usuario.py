import os
import django

# Configurar entorno
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "configuracion.settings")
django.setup()

from django.contrib.auth.models import User

# Crear superusuario si no existe
try:
    if not User.objects.filter(username='admin').exists():
        print("Creando usuario 'admin'...")
        User.objects.create_superuser('admin', 'admin@lipigas.cl', 'lipigas123')
        print("✅ ¡Usuario creado exitosamente!")
        print("Usuario: admin")
        print("Clave: lipigas123")
    else:
        print("⚠️ El usuario 'admin' ya existía.")
except Exception as e:
    print(f"❌ Error al crear usuario: {e}")