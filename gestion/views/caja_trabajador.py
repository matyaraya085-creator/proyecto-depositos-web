from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# --- VISTA DEL MENÚ ---
@login_required
def menu_trabajadores(request):
    # CORRECCIÓN: Ahora apuntamos a la carpeta 'caja_trabajador'
    return render(request, 'gestion/caja_trabajador/menu_trabajador.html')