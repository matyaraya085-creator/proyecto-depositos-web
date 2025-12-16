from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required

# NOTA: Quitamos el import de Vehiculo y la lógica de alertas

@login_required
def home(request):
    # Simplemente renderizamos el home sin buscar nada en la base de datos de vehículos
    context = {} 
    return render(request, 'gestion/core/home.html', context)

def cerrar_sesion(request):
    """
    Vista personalizada para cerrar sesión mediante petición GET (enlace simple).
    """
    logout(request)
    return redirect('login')