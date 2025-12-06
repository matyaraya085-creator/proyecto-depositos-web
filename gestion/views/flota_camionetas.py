from django.shortcuts import render
from gestion.models import Vehiculo

def menu_camionetas(request):
    """
    Vista para el menú principal del módulo de flota.
    """
    # Asegúrate de que esta ruta de template exista o créala
    return render(request, 'gestion/camionetas/menu_camionetas.html')

def inventario_flota(request):
    """
    Vista para listar el inventario de camionetas y sus alertas.
    """
    vehiculos = Vehiculo.objects.all()
    
    context = {
        'vehiculos': vehiculos
    }
    # Asegúrate de que esta ruta de template exista o créala
    return render(request, 'gestion/camionetas/inventario.html', context)