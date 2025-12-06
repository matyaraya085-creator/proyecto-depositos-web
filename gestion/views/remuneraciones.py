from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

# --- MÓDULO DE REMUNERACIONES ---

@login_required
def menu_remuneraciones(request):
    """
    Menú principal de remuneraciones.
    """
    return render(request, 'gestion/remuneraciones/menu_remuneraciones.html')

@login_required
def nomina_mensual(request):
    """
    Tabla donde se listan los trabajadores para el cálculo del mes.
    """
    return render(request, 'gestion/remuneraciones/nomina_mensual.html')

@login_required
def calcular_sueldo(request):
    """
    Formulario para ingresar las variables del mes (días, horas extras, etc.)
    """
    if request.method == 'POST':
        # AQUÍ IRÁ TU LÓGICA DE CÁLCULO MÁS ADELANTE
        # Por ahora, solo simulamos que guardamos y volvemos a la nómina
        return redirect('nomina_mensual')
        
    return render(request, 'gestion/remuneraciones/formulario_calculo.html')