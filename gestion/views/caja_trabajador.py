from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# --- MÓDULO DE CAJA Y FLUJO POR TRABAJADOR ---

@login_required
def menu_trabajadores(request):
    """
    Vista principal del menú de flujo por trabajador.
    Renderiza el menú de opciones (Lista, Saldos, Historial).
    """
    return render(request, 'gestion/trabajadores/menu_trabajador.html')