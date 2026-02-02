from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from gestion.models import Vehiculo
# Importación corregida para acceder al archivo dentro de la carpeta
from gestion.views.camionetas.camionetas import calcular_estado

@login_required
def home(request):
    # 1. Valores por defecto (Caso Verde: Todo OK)
    flota_status_class = "success" 
    flota_text = "Todo al día"
    flota_icon = "fas fa-check-circle"

    # Solo procesamos la lógica si el usuario es administrador
    if request.user.is_superuser:
        vehiculos = Vehiculo.objects.all()
        
        # Mapeo de prioridades:
        # 0: Verde, 1: Amarillo, 2: Rojo, 3: Negro
        prioridad_actual = 0 
        
        for v in vehiculos:
            # Obtenemos el color individual del vehículo ('success', 'warning', 'danger', 'dark')
            color_vehiculo, _ = calcular_estado(v)
            
            nivel_gravedad = 0
            if color_vehiculo == 'warning':
                nivel_gravedad = 1
            elif color_vehiculo == 'danger':
                nivel_gravedad = 2
            elif color_vehiculo == 'dark':
                nivel_gravedad = 3
            
            # Si encontramos un vehículo con un estado más grave, actualizamos el global
            if nivel_gravedad > prioridad_actual:
                prioridad_actual = nivel_gravedad
        
        # 2. Definimos la apariencia final del bloque según la gravedad más alta
        if prioridad_actual == 1:
            flota_status_class = "warning" # Amarillo
            flota_text = "Precaución"
            flota_icon = "fas fa-exclamation-circle"
            
        elif prioridad_actual == 2:
            flota_status_class = "danger" # Rojo
            flota_text = "Peligro"
            flota_icon = "fas fa-exclamation-triangle"
            
        elif prioridad_actual == 3:
            flota_status_class = "dark" # Negro -> Aquí aplica el estilo status-dark
            flota_text = "Vencido"
            flota_icon = "fas fa-times-circle"

    context = {
        'flota_status_class': flota_status_class,
        'flota_text': flota_text,
        'flota_icon': flota_icon,
    } 
    return render(request, 'gestion/core/home.html', context)

def cerrar_sesion(request):
    """
    Vista personalizada para cerrar sesión mediante petición GET.
    """
    logout(request)
    return redirect('login')