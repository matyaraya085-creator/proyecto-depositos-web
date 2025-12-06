from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# --- MÓDULO DE REMUNERACIONES ---

@login_required
def menu_remuneraciones(request):
    """
    Menú principal.
    """
    return render(request, 'gestion/remuneraciones/menu_remuneraciones.html')

@login_required
def nomina_mensual(request):
    """
    Tabla principal donde se listan los trabajadores para el cálculo del mes.
    """
    # En el futuro aquí cargaremos: trabajadores = Trabajador.objects.all()
    return render(request, 'gestion/remuneraciones/nomina_mensual.html')