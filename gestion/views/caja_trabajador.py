from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# --- MÓDULO DE CAJA Y FLUJO POR TRABAJADOR ---

@login_required
def menu_trabajadores(request):
    return render(request, 'gestion/caja_trabajador/menu_trabajador.html')

@login_required
def form_rendicion(request):
    return render(request, 'gestion/caja_trabajador/form_rendicion.html')

@login_required
def reporte_mensual(request):
    """
    Vista para el reporte mensual acumulado.
    """
    return render(request, 'gestion/caja_trabajador/reporte_mensual.html')