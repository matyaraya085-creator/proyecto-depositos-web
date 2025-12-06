from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# NOTA: Quitamos el import de Vehiculo y la lógica de alertas

@login_required
def home(request):
    # Simplemente renderizamos el home sin buscar nada en la base de datos de vehículos
    context = {} 
    return render(request, 'gestion/core/home.html', context)