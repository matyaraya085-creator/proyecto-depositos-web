from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# --- MÓDULO DE CAJA Y FLUJO POR TRABAJADOR ---

@login_required
def menu_trabajadores(request):
    """
    Vista principal del menú.
    """
    return render(request, 'gestion/caja_trabajador/menu_trabajador.html')

@login_required
def form_rendicion(request):
    """
    Vista para el formulario de rendición (Diseño visual).
    """
    return render(request, 'gestion/caja_trabajador/form_rendicion.html')