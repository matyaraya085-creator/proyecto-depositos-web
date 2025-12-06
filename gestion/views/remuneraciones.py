from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# --- MÓDULO DE REMUNERACIONES ---

@login_required
def menu_remuneraciones(request):
    """
    Vista principal del menú de remuneraciones.
    """
    # Asegúrate de crear la carpeta 'remuneraciones' dentro de templates/gestion/
    return render(request, 'gestion/remuneraciones/menu_remuneraciones.html')