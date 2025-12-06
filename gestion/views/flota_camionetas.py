from django.shortcuts import render
from gestion.models import Vehiculo # Asegúrate de importar el modelo

def menu_camionetas(request):
    """
    Vista para el menú principal del módulo de flota.
    """
    return render(request, 'gestion/camionetas/menu_camionetas.html')

def inventario_flota(request):
    """
    Vista para listar el inventario de camionetas y sus alertas.
    """
    vehiculos = Vehiculo.objects.all()
    
    # Preparamos las alertas para mostrarlas en la tabla si es necesario
    # (Aunque la lógica fuerte ya está en el modelo, aquí pasamos el objeto completo)
    context = {
        'vehiculos': vehiculos
    }
    return render(request, 'gestion/camionetas/inventario.html', context)