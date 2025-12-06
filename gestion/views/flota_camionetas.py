from django.shortcuts import render
from gestion.models import Vehiculo
from datetime import date, timedelta

def calcular_estado(vehiculo):
    """
    Replica la lógica de tu script Python para definir el estado y alertas.
    Retorna: (color_bootstrap, lista_de_mensajes)
    """
    hoy = date.today()
    mensajes = []
    color = "success" # Verde por defecto (Todo ok)
    
    # 1. Análisis de Mantención
    if vehiculo.fecha_mantencion:
        dias_mant = (vehiculo.fecha_mantencion - hoy).days
        if dias_mant <= 0:
            mensajes.append("🔴 MANTENCIÓN VENCIDA")
            color = "danger"
        elif dias_mant <= 30:
            mensajes.append(f"🟡 Mantención en {dias_mant} días")
            if color != "danger": color = "warning"

    # 2. Análisis de Permiso de Circulación
    if vehiculo.fecha_permiso:
        dias_perm = (vehiculo.fecha_permiso - hoy).days
        if dias_perm <= 0:
            mensajes.append("🔴 PERMISO VENCIDO")
            color = "danger"
        elif dias_perm <= 30:
            mensajes.append(f"🟡 Permiso vence en {dias_perm} días")
            if color != "danger": color = "warning"

    # 3. Análisis de Kilometraje
    # (Asumimos que kilometraje_maximo es el próximo cambio de aceite/revisión)
    if vehiculo.kilometraje_maximo > 0:
        km_restante = vehiculo.kilometraje_maximo - vehiculo.kilometraje_actual
        if km_restante <= 0:
            mensajes.append(f"🔴 KILOMETRAJE EXCEDIDO ({km_restante} km)")
            color = "danger"
        elif km_restante <= 1000: # Alerta a los 1000km antes
            mensajes.append(f"🟡 Cambio de aceite en {km_restante} km")
            if color != "danger": color = "warning"

    if not mensajes:
        mensajes.append("🟢 Todo en orden")

    return color, mensajes

def menu_camionetas(request):
    """
    Vista principal: Muestra la tabla de control con semáforos.
    """
    vehiculos_query = Vehiculo.objects.all()
    lista_vehiculos = []

    for v in vehiculos_query:
        # Calculamos estado para cada camioneta
        color, alertas = calcular_estado(v)
        
        # Creamos un diccionario con todo lo necesario para el HTML
        lista_vehiculos.append({
            'patente': v.patente,
            'fecha_mantencion': v.fecha_mantencion,
            'fecha_permiso': v.fecha_permiso,
            'km_actual': v.kilometraje_actual,
            'km_max': v.kilometraje_maximo,
            'color': color,
            'alertas': alertas,
            'id': v.id # Para editar/borrar futuro
        })

    context = {
        'vehiculos': lista_vehiculos,
        'hoy': date.today()
    }
    return render(request, 'gestion/camionetas/menu_camionetas.html', context)

def inventario_flota(request):
    # Por ahora redirigimos al menú que ya tiene el inventario
    return menu_camionetas(request)