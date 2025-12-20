from django.shortcuts import render, redirect, get_object_or_404
from gestion.models import Vehiculo
from datetime import date
from django.db import IntegrityError

def agregar_vehiculo(request):
    if request.method == 'POST':
        try:
            patente = request.POST.get('patente', '').upper()
            
            Vehiculo.objects.create(
                patente=patente,
                fecha_mantencion=request.POST.get('fecha_mantencion'),
                fecha_permiso=request.POST.get('fecha_circulacion'),
                fecha_extintor=request.POST.get('fecha_extintor'), # <--- NUEVO CAMPO
                
                kilometraje_actual=int(request.POST.get('kilometraje') or 0), 
                kilometraje_maximo=int(request.POST.get('kilometraje_maximo') or 0),
                km_diarios=float(request.POST.get('km_diarios') or 0.0),
                dias_uso_semanal=int(request.POST.get('dias_semana') or 5)
            )
            return redirect('menu_camionetas') 

        except IntegrityError:
            pass
        except Exception:
            pass
            
    return redirect('menu_camionetas')

# REEMPLAZA LA FUNCIÓN calcular_estado COMPLETA CON ESTO:

def calcular_estado(vehiculo):
    """
    Analiza Mantención, Permiso, Kilometraje y Extintor con lógica de 3 niveles:
    - NEGRO (dark): Vencido (<= 0 días)
    - ROJO (danger): Urgente (<= 7 días)
    - AMARILLO (warning): Alerta (<= 30 días)
    """
    hoy = date.today()
    alertas = [] # Ahora guardaremos diccionarios: {'msg': '...', 'tipo': '...'}
    
    # Definimos una prioridad para decidir el color general de la fila
    # 3: Negro, 2: Rojo, 1: Amarillo, 0: Verde
    prioridad_maxima = 0 
    color_fila = "success"

    def evaluar_fecha(fecha, nombre):
        nonlocal prioridad_maxima, color_fila
        if fecha:
            dias = (fecha - hoy).days
            if dias <= 0:
                # NIVEL 1: NEGRO (VENCIDO)
                alertas.append({'msg': f"⚫ {nombre} VENCIDO", 'tipo': 'dark'})
                if prioridad_maxima < 3:
                    prioridad_maxima = 3
                    color_fila = "dark"
            elif dias <= 7:
                # NIVEL 2: ROJO (URGENTE - 1 SEMANA)
                alertas.append({'msg': f"🔴 {nombre}: {dias} días", 'tipo': 'danger'})
                if prioridad_maxima < 2:
                    prioridad_maxima = 2
                    color_fila = "danger"
            elif dias <= 30:
                # NIVEL 3: AMARILLO (ALERTA - 1 MES)
                alertas.append({'msg': f"🟡 {nombre}: {dias} días", 'tipo': 'warning'})
                if prioridad_maxima < 1:
                    prioridad_maxima = 1
                    color_fila = "warning"

    # 1. Evaluar Fechas
    evaluar_fecha(vehiculo.fecha_mantencion, "MANTENCIÓN")
    evaluar_fecha(vehiculo.fecha_permiso, "PERMISO")
    evaluar_fecha(vehiculo.fecha_extintor, "EXTINTOR")

    # 2. Evaluar Kilometraje (Lógica especial)
    if vehiculo.kilometraje_maximo > 0:
        km_restante = vehiculo.kilometraje_maximo - vehiculo.kilometraje_actual
        
        if km_restante <= 0:
            # KM EXCEDIDO -> NEGRO
            alertas.append({'msg': f"⚫ KM EXCEDIDO ({km_restante})", 'tipo': 'dark'})
            if prioridad_maxima < 3:
                prioridad_maxima = 3
                color_fila = "dark"
                
        elif km_restante <= 500:
             # MENOS DE 500KM -> ROJO
            alertas.append({'msg': f"🔴 Cambio Aceite en {km_restante} km", 'tipo': 'danger'})
            if prioridad_maxima < 2:
                prioridad_maxima = 2
                color_fila = "danger"
                
        elif km_restante <= 1000:
            # MENOS DE 1000KM -> AMARILLO
            alertas.append({'msg': f"🟡 Cambio Aceite en {km_restante} km", 'tipo': 'warning'})
            if prioridad_maxima < 1:
                prioridad_maxima = 1
                color_fila = "warning"

    return color_fila, alertas

def menu_camionetas(request):
    vehiculos_query = Vehiculo.objects.all()
    lista_vehiculos = []
    
    # Contadores para el Dashboard
    total_flota = vehiculos_query.count()
    total_alertas = 0

    for v in vehiculos_query:
        color, alertas = calcular_estado(v)
        
        if color in ['danger', 'warning']:
            total_alertas += 1

        lista_vehiculos.append({
            'patente': v.patente,
            'fecha_mantencion': v.fecha_mantencion,
            'fecha_permiso': v.fecha_permiso,
            'fecha_extintor': v.fecha_extintor, # <--- NUEVO
            'km_actual': v.kilometraje_actual,
            'km_max': v.kilometraje_maximo,
            'km_diarios': v.km_diarios,      # Necesario para el modal editar
            'dias_semana': v.dias_uso_semanal, # Necesario para el modal editar
            'color': color,
            'alertas': alertas,
        })

    context = {
        'vehiculos': lista_vehiculos,
        'hoy': date.today(),
        'total_flota': total_flota,
        'total_alertas': total_alertas
    }
    return render(request, 'gestion/camionetas/menu_camionetas.html', context)

def editar_vehiculo(request, patente):
    vehiculo = get_object_or_404(Vehiculo, patente=patente)

    if request.method == 'POST':
        try:
            vehiculo.fecha_mantencion = request.POST.get('fecha_mantencion')
            vehiculo.fecha_permiso = request.POST.get('fecha_circulacion')
            vehiculo.fecha_extintor = request.POST.get('fecha_extintor') # <--- NUEVO
            
            vehiculo.kilometraje_actual = int(request.POST.get('kilometraje') or 0)
            vehiculo.kilometraje_maximo = int(request.POST.get('kilometraje_maximo') or 0)
            vehiculo.km_diarios = float(request.POST.get('km_diarios') or 0.0)
            vehiculo.dias_uso_semanal = int(request.POST.get('dias_semana') or 5)
            
            vehiculo.save()
        except Exception:
            pass
        return redirect('menu_camionetas')
        
    return redirect('menu_camionetas')

def eliminar_vehiculo(request, patente):
    if request.method == 'POST':
        try:
            vehiculo = get_object_or_404(Vehiculo, patente=patente)
            vehiculo.delete()
        except Exception:
            pass
    return redirect('menu_camionetas')