from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# --- VISTA HOME ---
@login_required
def home(request):
    context = {}
    return render(request, 'gestion/core/home.html', context)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
# Importamos el modelo nuevo
from gestion.models import Vehiculo 

@login_required
def home(request):
    # 1. Obtenemos todos los vehículos
    vehiculos = Vehiculo.objects.all()
    
    # 2. Recopilamos alertas
    lista_notificaciones = []
    
    for v in vehiculos:
        alertas = v.get_alertas()
        for alerta in alertas:
            # Guardamos un diccionario con la info para el HTML
            lista_notificaciones.append({
                'patente': v.patente,
                'mensaje': alerta,
                'tipo': 'danger' if '🔴' in alerta else 'warning'
            })
            
    cantidad_alertas = len(lista_notificaciones)

    context = {
        'notificaciones': lista_notificaciones,
        'cantidad_alertas': cantidad_alertas
    }
    # Fíjate que agregamos la ruta completa dentro de templates
    return render(request, 'gestion/core/home.html', context)