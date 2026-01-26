from django.shortcuts import render, redirect, get_object_or_404
from gestion.models import Vehiculo
from datetime import date
from django.db import IntegrityError

def agregar_vehiculo(request):
    if request.method == 'POST':
        try:
            patente = request.POST.get('patente', '').upper()
            
            # Conversión segura de flotante
            km_diarios_str = request.POST.get('km_diarios', '0').replace(',', '.')
            
            Vehiculo.objects.create(
                patente=patente,
                fecha_mantencion=request.POST.get('fecha_mantencion') or None,
                fecha_permiso=request.POST.get('fecha_circulacion') or None,
                fecha_extintor=request.POST.get('fecha_extintor') or None,
                
                # Al crear, el KM actual es la base y la fecha es hoy
                kilometraje_actual=int(request.POST.get('kilometraje') or 0),
                fecha_reporte_km=date.today(), 
                
                kilometraje_maximo=int(request.POST.get('kilometraje_maximo') or 0),
                km_diarios=float(km_diarios_str or 0.0),
                dias_uso_semanal=int(request.POST.get('dias_semana') or 5)
            )
            return redirect('menu_camionetas') 

        except IntegrityError:
            pass
        except Exception as e:
            print(f"Error al agregar: {e}")
            pass
            
    return redirect('menu_camionetas')

def calcular_estado(vehiculo):
    """
    Analiza Mantención, Permiso, Kilometraje (ESTIMADO) y Extintor.
    Prioridades:
    3. NEGRO (dark): Vencido (<= 0 días) - ¡Te pasaste!
    2. ROJO (danger): Urgente (<= 7 días) - ¡Alerta, queda poco!
    1. AMARILLO (warning): Atento (<= 30 días) - Queda menos de 1 mes
    0. VERDE (success): OK (> 30 días) - Estás bien
    """
    hoy = date.today()
    alertas = [] 
    
    # 0: Verde (Base), 1: Amarillo, 2: Rojo, 3: Negro
    prioridad_maxima = 0 
    color_fila = "success" # Por defecto Verde

    def evaluar_fecha(fecha, nombre):
        nonlocal prioridad_maxima, color_fila
        if fecha:
            dias = (fecha - hoy).days
            
            if dias <= 0:
                # NIVEL 3: NEGRO (VENCIDO)
                alertas.append({'msg': f"⚫ {nombre} VENCIDO hace {abs(dias)} días", 'tipo': 'dark'})
                if prioridad_maxima < 3:
                    prioridad_maxima = 3
                    color_fila = "dark"
            
            elif dias <= 7:
                # NIVEL 2: ROJO (URGENTE 1 SEMANA)
                alertas.append({'msg': f"🔴 {nombre}: Vence en {dias} días", 'tipo': 'danger'})
                if prioridad_maxima < 2:
                    prioridad_maxima = 2
                    color_fila = "danger"
            
            elif dias <= 30:
                # NIVEL 1: AMARILLO (ATENTO 1 MES)
                alertas.append({'msg': f"🟡 {nombre}: Vence en {dias} días", 'tipo': 'warning'})
                if prioridad_maxima < 1:
                    prioridad_maxima = 1
                    color_fila = "warning"
            
            # Si dias > 30, no hacemos nada

    # 1. Evaluar Fechas
    evaluar_fecha(vehiculo.fecha_mantencion, "MANTENCIÓN")
    evaluar_fecha(vehiculo.fecha_permiso, "PERMISO")
    evaluar_fecha(vehiculo.fecha_extintor, "EXTINTOR")

    # 2. Evaluar Kilometraje (USANDO EL ESTIMADO)
    if vehiculo.kilometraje_maximo > 0:
        # Aquí usamos la propiedad mágica que calcula solo
        km_actual_estimado = vehiculo.kilometraje_estimado
        km_restante = vehiculo.kilometraje_maximo - km_actual_estimado
        
        if km_restante <= 0:
            # KM EXCEDIDO -> NEGRO
            alertas.append({'msg': f"⚫ KM ESTIMADO EXCEDIDO por {abs(km_restante)} km", 'tipo': 'dark'})
            if prioridad_maxima < 3:
                prioridad_maxima = 3
                color_fila = "dark"
                
        elif km_restante <= 500:
             # MENOS DE 500KM -> ROJO
            alertas.append({'msg': f"🔴 Mantención KM en {km_restante} km (Est.)", 'tipo': 'danger'})
            if prioridad_maxima < 2:
                prioridad_maxima = 2
                color_fila = "danger"
                
        elif km_restante <= 1500: 
            # ALERTA KM -> AMARILLO
            alertas.append({'msg': f"🟡 Mantención KM en {km_restante} km (Est.)", 'tipo': 'warning'})
            if prioridad_maxima < 1:
                prioridad_maxima = 1
                color_fila = "warning"

    return color_fila, alertas

def menu_camionetas(request):
    vehiculos_query = Vehiculo.objects.all().order_by('patente')
    lista_vehiculos = []
    
    total_flota = vehiculos_query.count()
    total_alertas = 0

    for v in vehiculos_query:
        color, alertas = calcular_estado(v)
        
        # Contar alertas si no es verde
        if color in ['dark', 'danger', 'warning']:
            total_alertas += 1

        lista_vehiculos.append({
            'patente': v.patente,
            'fecha_mantencion': v.fecha_mantencion,
            'fecha_permiso': v.fecha_permiso,
            'fecha_extintor': v.fecha_extintor,
            
            # Enviamos el estimado para visualización
            'km_actual': v.kilometraje_estimado, 
            # Enviamos el base (real) para el modal de edición
            'km_base_real': v.kilometraje_actual,
            'fecha_reporte_km': v.fecha_reporte_km,
            
            'km_max': v.kilometraje_maximo,
            'km_diarios': v.km_diarios,      
            'dias_semana': v.dias_uso_semanal, 
            'color': color,
            'alertas': alertas,
        })

    context = {
        'vehiculos': lista_vehiculos,
        'hoy': date.today(),
        'total_flota': total_flota,
        'total_alertas': total_alertas
    }
    return render(request, 'gestion/camionetas/camionetas.html', context)

def editar_vehiculo(request, patente):
    vehiculo = get_object_or_404(Vehiculo, patente=patente)

    if request.method == 'POST':
        try:
            # --- CAMBIO DE PATENTE ---
            nueva_patente = request.POST.get('patente', '').upper().strip()
            
            # Si la patente cambió, verificamos que no exista otra igual
            if nueva_patente and nueva_patente != vehiculo.patente:
                if Vehiculo.objects.filter(patente=nueva_patente).exists():
                    print("Error: La patente ya existe, no se puede duplicar.")
                    # Opcional: Agregar mensaje de error al usuario
                else:
                    vehiculo.patente = nueva_patente

            # Fechas (Si vienen vacías, guardar None)
            vehiculo.fecha_mantencion = request.POST.get('fecha_mantencion') or None
            vehiculo.fecha_permiso = request.POST.get('fecha_circulacion') or None
            vehiculo.fecha_extintor = request.POST.get('fecha_extintor') or None
            
            # KM y Configuración
            nuevo_km_base = int(request.POST.get('kilometraje') or 0)
            vehiculo.kilometraje_actual = nuevo_km_base
            # IMPORTANTE: Al guardar el form de edición, asumimos que el usuario
            # está confirmando o corrigiendo el KM actual, así que reseteamos la fecha de cálculo a HOY.
            vehiculo.fecha_reporte_km = date.today()
            
            vehiculo.kilometraje_maximo = int(request.POST.get('kilometraje_maximo') or 0)
            
            # Números Flotantes
            km_diarios_input = request.POST.get('km_diarios', '0')
            km_diarios_input = km_diarios_input.replace(',', '.') 
            vehiculo.km_diarios = float(km_diarios_input or 0.0)
            
            vehiculo.dias_uso_semanal = int(request.POST.get('dias_semana') or 5)
            
            vehiculo.save()
        except Exception as e:
            print(f"Error al editar: {e}")
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