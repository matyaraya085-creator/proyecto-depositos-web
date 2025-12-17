from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum, Count, Case, When, IntegerField, F
from datetime import date, datetime
import json
import locale
from gestion.models import RendicionDiaria, Trabajador, BODEGA_CHOICES, TarifaComision, CierreDiario

try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    pass

# ==========================================
# 1. MENÚ PRINCIPAL
# ==========================================
@login_required
def menu_trabajadores(request):
    return render(request, 'gestion/caja_trabajador/menu_trabajador.html')

# ==========================================
# 2. DASHBOARD (LISTA DIARIA + CIERRE GLOBAL)
# ==========================================
@login_required
def dashboard_bodega(request):
    bodega_id = request.GET.get('bodega')
    fecha_str = request.GET.get('fecha')
    
    if not bodega_id:
        return redirect('menu_trabajadores')
        
    nombre_bodega = dict(BODEGA_CHOICES).get(bodega_id, bodega_id)

    if fecha_str:
        try:
            fecha_seleccionada = date.fromisoformat(fecha_str)
        except ValueError:
            fecha_seleccionada = timezone.now().date()
    else:
        fecha_seleccionada = timezone.now().date()
    
    str_fecha_db = fecha_seleccionada.strftime('%Y-%m-%d')

    # --- LÓGICA DE CIERRE GLOBAL (POST) ---
    if request.method == 'POST' and 'accion_global' in request.POST:
        if not request.user.is_superuser:
             messages.error(request, "Solo administradores pueden cerrar/abrir el día globalmente.")
        else:
            accion = request.POST.get('accion_global')
            if accion == 'cerrar_dia':
                CierreDiario.objects.get_or_create(fecha=fecha_seleccionada, bodega=bodega_id, defaults={'cerrado_por': request.user})
                messages.success(request, f"🔒 Día {str_fecha_db} CERRADO globalmente para bodega {bodega_id}.")
            elif accion == 'abrir_dia':
                CierreDiario.objects.filter(fecha=fecha_seleccionada, bodega=bodega_id).delete()
                messages.warning(request, f"🔓 Día {str_fecha_db} REABIERTO globalmente.")
        
        return redirect(f"{request.path}?bodega={bodega_id}&fecha={str_fecha_db}")

    # --- CONSULTAS ---
    # 1. Verificar si está cerrado globalmente
    cierre_obj = CierreDiario.objects.filter(fecha=fecha_seleccionada, bodega=bodega_id).first()
    esta_cerrado_global = (cierre_obj is not None)

    # 2. Rendiciones
    rendiciones = RendicionDiaria.objects.filter(
        fecha=fecha_seleccionada,
        bodega=bodega_id 
    ).select_related('trabajador').order_by('created_at')

    # 3. Trabajadores (solo mostrar si no está cerrado, o para referencia)
    trabajadores_disponibles = Trabajador.objects.filter(
        Q(bodega_asignada=bodega_id) | Q(bodega_asignada='Ambos')
    ).order_by('nombre')

    # Totales del día
    total_kg_dia = sum(r.total_kilos for r in rendiciones)
    total_diferencia_dia = sum(r.diferencia for r in rendiciones) 

    # Estados visuales
    for r in rendiciones:
        r.estado_dinero = "PENDIENTE"
        r.clase_estado = "bg-secondary"
        if r.total_venta > 0 or r.efectivo_entregado > 0:
            if r.diferencia == 0:
                r.estado_dinero = "CUADRADO"
                r.clase_estado = "bg-success"
            elif r.diferencia < 0:
                r.estado_dinero = "FALTANTE"
                r.clase_estado = "bg-danger"
            else:
                r.estado_dinero = "SOBRANTE"
                r.clase_estado = "bg-primary"

    context = {
        'bodega_id': bodega_id,
        'nombre_bodega': nombre_bodega,
        'fecha_seleccionada': fecha_seleccionada,
        'fecha_str': str_fecha_db,
        'rendiciones': rendiciones,
        'trabajadores_disponibles': trabajadores_disponibles,
        'total_kg_dia': total_kg_dia,
        'total_diferencia_dia': total_diferencia_dia,
        'esta_cerrado_global': esta_cerrado_global, # Variable clave para el Template
    }
    return render(request, 'gestion/caja_trabajador/lista_rendiciones.html', context)

# ==========================================
# 3. CREACIÓN DE RENDICIÓN
# ==========================================
@login_required
def crear_rendicion_vacia(request):
    if request.method == 'POST':
        fecha_str = request.POST.get('fecha')
        bodega_id = request.POST.get('bodega_id')
        
        # Verificar bloqueo global antes de crear
        if CierreDiario.objects.filter(fecha=fecha_str, bodega=bodega_id).exists():
            messages.error(request, "⛔ El día está cerrado globalmente. No se pueden agregar turnos.")
            return redirect(f"/gestion/trabajadores/dashboard/?bodega={bodega_id}&fecha={fecha_str}")

        trabajador_id = request.POST.get('trabajador_id')
        trabajador = get_object_or_404(Trabajador, id=trabajador_id)
        fecha = date.fromisoformat(fecha_str)

        rendicion = RendicionDiaria.objects.create(
            trabajador=trabajador,
            fecha=fecha,
            bodega=bodega_id
        )
        
        return redirect('form_rendicion_editar', rendicion_id=rendicion.id)
    
    return redirect('menu_trabajadores')

@login_required
def eliminar_rendicion(request, rendicion_id):
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para eliminar.")
        return redirect('menu_trabajadores')
        
    rendicion = get_object_or_404(RendicionDiaria, id=rendicion_id)
    
    # Verificar bloqueo global
    if CierreDiario.objects.filter(fecha=rendicion.fecha, bodega=rendicion.bodega).exists():
        messages.error(request, "⛔ El día está cerrado globalmente. Reábrelo para eliminar.")
        return redirect(f"/gestion/trabajadores/dashboard/?bodega={rendicion.bodega}&fecha={rendicion.fecha}")

    bodega_id = rendicion.bodega
    fecha_str = rendicion.fecha.strftime('%Y-%m-%d')
    rendicion.delete()
    messages.success(request, "Rendición eliminada.")
    
    return redirect(f"/gestion/trabajadores/dashboard/?bodega={bodega_id}&fecha={fecha_str}")

# ==========================================
# 4. FORMULARIO DE EDICIÓN
# ==========================================
@login_required
def form_rendicion_editar(request, rendicion_id):
    rendicion = get_object_or_404(RendicionDiaria, id=rendicion_id)
    trabajador = rendicion.trabajador
    bodega_actual = rendicion.bodega 

    # Verificar si el día está cerrado globalmente
    dia_cerrado_global = CierreDiario.objects.filter(fecha=rendicion.fecha, bodega=bodega_actual).exists()

    if request.method == 'POST':
        if dia_cerrado_global:
            messages.error(request, "⛔ ACCIÓN DENEGADA: El día tiene un Cierre Global de Bodega.")
            return redirect('form_rendicion_editar', rendicion_id=rendicion.id)

        accion = request.POST.get('accion') 

        if rendicion.cerrado and not request.user.is_superuser and accion != 'reabrir':
            messages.error(request, "⛔ Esta rendición está CERRADA individualmente.")
            return redirect('form_rendicion_editar', rendicion_id=rendicion.id)

        try:
            if accion == 'reabrir' and request.user.is_superuser:
                rendicion.cerrado = False
                rendicion.save()
                messages.success(request, "🔓 Rendición REABIERTA exitosamente.")
                return redirect('form_rendicion_editar', rendicion_id=rendicion.id)

            # INVENTARIO
            rendicion.gas_5kg = int(request.POST.get('gas_5kg') or 0)
            rendicion.gas_11kg = int(request.POST.get('gas_11kg') or 0)
            rendicion.gas_15kg = int(request.POST.get('gas_15kg') or 0)
            rendicion.gas_45kg = int(request.POST.get('gas_45kg') or 0)
            
            rendicion.gasc_5kg = int(request.POST.get('gasc_5kg') or 0)
            rendicion.gasc_15kg = int(request.POST.get('gasc_15kg') or 0)
            rendicion.gas_ultra_15kg = int(request.POST.get('gas_ultra_15kg') or 0)
            
            rendicion.cilindros_defectuosos = int(request.POST.get('cilindros_defectuosos') or 0)
            
            # CÁLCULO DE KILOS
            rendicion.total_kilos = (rendicion.gas_5kg * 5) + \
                                    (rendicion.gas_11kg * 11) + \
                                    (rendicion.gas_15kg * 15) + \
                                    (rendicion.gas_45kg * 45) + \
                                    (rendicion.gasc_5kg * 5) + \
                                    (rendicion.gasc_15kg * 15) + \
                                    (rendicion.gas_ultra_15kg * 15)

            # CAJA
            rendicion.total_venta = int(request.POST.get('total_venta') or 0)
            rendicion.monto_vales = int(request.POST.get('monto_vales') or 0)
            rendicion.monto_transbank = int(request.POST.get('monto_transbank') or 0)
            rendicion.efectivo_entregado = int(request.POST.get('efectivo_entregado') or 0)

            # CÁLCULO DINERO
            rendicion.efectivo_esperado = rendicion.total_venta - (rendicion.monto_vales + rendicion.monto_transbank)
            rendicion.diferencia = rendicion.efectivo_entregado - rendicion.efectivo_esperado
            
            if accion == 'cerrar':
                rendicion.cerrado = True
                messages.success(request, f'🔒 Rendición CERRADA.')
            else:
                messages.success(request, f'💾 Guardado correctamente.')

            rendicion.save()
            return redirect('form_rendicion_editar', rendicion_id=rendicion.id)

        except Exception as e:
            messages.error(request, f'Error al guardar: {str(e)}')

    context = {
        'rendicion': rendicion,
        'trabajador': trabajador,
        'bodega_actual': bodega_actual,
        'fecha_str': rendicion.fecha.strftime('%Y-%m-%d'),
        'dia_cerrado_global': dia_cerrado_global # Para bloquear visualmente el form
    }
    return render(request, 'gestion/caja_trabajador/form_rendicion.html', context)

@login_required
def cerrar_rendicion(request, rendicion_id):
    # (Mantenemos esta vista por si se llama desde url, pero agregamos validación)
    rendicion = get_object_or_404(RendicionDiaria, id=rendicion_id)
    if CierreDiario.objects.filter(fecha=rendicion.fecha, bodega=rendicion.bodega).exists():
        messages.error(request, "⛔ Día Cerrado Globalmente.")
    else:
        rendicion.cerrado = True
        rendicion.save()
    bodega = rendicion.bodega
    return redirect(f"/gestion/trabajadores/dashboard/?bodega={bodega}&fecha={rendicion.fecha}")

@login_required
def abrir_rendicion(request, rendicion_id):
    if not request.user.is_superuser:
        messages.error(request, "Solo administradores.")
    else:
        rendicion = get_object_or_404(RendicionDiaria, id=rendicion_id)
        # Aquí permitimos abrir incluso si hay cierre global, pero el form no dejará guardar
        rendicion.cerrado = False
        rendicion.save()
    bodega = rendicion.bodega
    return redirect(f"/gestion/trabajadores/dashboard/?bodega={bodega}&fecha={rendicion.fecha}")

# ==========================================
# 5. REPORTE MENSUAL (CON VALORIZACIÓN)
# ==========================================
@login_required
def reporte_mensual(request):
    trabajador_id = request.GET.get('trabajador_id')
    fecha_str = request.GET.get('fecha_seleccionada')
    
    trabajadores = Trabajador.objects.all().order_by('nombre')
    trabajador_seleccionado = None
    report_data = None
    
    hoy = timezone.now()
    if not fecha_str:
        fecha_str = hoy.strftime('%Y-%m')
        
    try:
        anio, mes = map(int, fecha_str.split('-'))
    except ValueError:
        anio, mes = hoy.year, hoy.month

    # OBTENER TARIFAS DE COMISIÓN (Última registrada o ceros)
    tarifas = TarifaComision.objects.last()
    if not tarifas:
        tarifas = TarifaComision() # Objeto vacío con 0s

    if trabajador_id:
        trabajador_seleccionado = get_object_or_404(Trabajador, id=trabajador_id)
        
        rendiciones = RendicionDiaria.objects.filter(
            trabajador=trabajador_seleccionado,
            fecha__year=anio,
            fecha__month=mes
        ).order_by('fecha', 'created_at')

        if rendiciones.exists():
            dias_agrupados = {}
            total_kilos_mes = 0
            balance_mes = 0

            # Acumuladores para Comisión
            sum_5kg = 0
            sum_11kg = 0
            sum_15kg = 0
            sum_45kg = 0
            sum_cat5 = 0
            sum_cat15 = 0
            sum_ultra = 0

            for r in rendiciones:
                # Agrupación visual por día
                fecha_key = r.fecha 
                if fecha_key not in dias_agrupados:
                    dias_agrupados[fecha_key] = {
                        'fecha': r.fecha,
                        'total_kg': 0,
                        'total_balance': 0,
                        'turnos': []
                    }
                
                dias_agrupados[fecha_key]['total_kg'] += r.total_kilos
                dias_agrupados[fecha_key]['total_balance'] += r.diferencia
                dias_agrupados[fecha_key]['turnos'].append(r)
                
                total_kilos_mes += r.total_kilos
                balance_mes += r.diferencia

                # Sumar cantidades individuales para comisión
                sum_5kg += r.gas_5kg
                sum_11kg += r.gas_11kg
                sum_15kg += r.gas_15kg
                sum_45kg += r.gas_45kg
                sum_cat5 += r.gasc_5kg
                sum_cat15 += r.gasc_15kg
                sum_ultra += r.gas_ultra_15kg

            lista_detalle = sorted(dias_agrupados.values(), key=lambda x: x['fecha'])

            # CÁLCULO FINAL DE DINERO COMISIÓN
            dinero_comision = (sum_5kg * tarifas.tarifa_5kg) + \
                              (sum_11kg * tarifas.tarifa_11kg) + \
                              (sum_15kg * tarifas.tarifa_15kg) + \
                              (sum_45kg * tarifas.tarifa_45kg) + \
                              (sum_cat5 * tarifas.tarifa_cat_5kg) + \
                              (sum_cat15 * tarifas.tarifa_cat_15kg) + \
                              (sum_ultra * tarifas.tarifa_ultra_15kg)

            report_data = {
                'detalle_dias': lista_detalle,
                'total_kilos': total_kilos_mes,
                'balance': balance_mes,
                'total_comision': dinero_comision # Dato nuevo
            }

    context = {
        'trabajadores': trabajadores,
        'trabajador_seleccionado': trabajador_seleccionado,
        'fecha_seleccionada': fecha_str,
        'report_data': report_data
    }
    return render(request, 'gestion/caja_trabajador/reporte_mensual.html', context)

# ==========================================
# 6. ESTADÍSTICAS GLOBALES (+ RANKING)
# ==========================================
@login_required
def estadisticas_globales(request):
    hoy = timezone.now()
    anio_actual = int(request.GET.get('anio', hoy.year))
    mes_actual = int(request.GET.get('mes', hoy.month))
    bodega_seleccionada = request.GET.get('bodega', '')

    rendiciones = RendicionDiaria.objects.filter(
        fecha__year=anio_actual,
        fecha__month=mes_actual
    )

    if bodega_seleccionada in ['1221', '1225']:
        rendiciones = rendiciones.filter(bodega=bodega_seleccionada)

    # 1. KPIs Generales
    resumen = rendiciones.aggregate(
        total_kilos=Sum('total_kilos'),
        total_dinero=Sum('total_venta'),
        balance_neto=Sum('diferencia')
    )
    
    kpi_kilos = resumen['total_kilos'] or 0
    kpi_dinero = resumen['total_dinero'] or 0
    kpi_balance = resumen['balance_neto'] or 0

    # 2. Datos Gráficos
    datos_diarios = rendiciones.values('fecha').annotate(
        suma_kilos=Sum('total_kilos'),
        suma_balance=Sum('diferencia')
    ).order_by('fecha')

    fechas_labels = [d['fecha'].strftime('%d/%m') for d in datos_diarios]
    data_kilos = [d['suma_kilos'] for d in datos_diarios]
    data_balance = [d['suma_balance'] for d in datos_diarios]

    estados = rendiciones.aggregate(
        cuadrado=Count(Case(When(diferencia=0, then=1), output_field=IntegerField())),
        faltante=Count(Case(When(diferencia__lt=0, then=1), output_field=IntegerField())),
        sobrante=Count(Case(When(diferencia__gt=0, then=1), output_field=IntegerField()))
    )

    # 3. RANKING DE FALTANTES (NUEVO)
    # Agrupar por trabajador y sumar diferencias
    # Ordenar ASCENDENTE (Los números más negativos primero = Más faltante)
    ranking = rendiciones.values('trabajador__nombre').annotate(
        total_diferencia=Sum('diferencia'),
        total_kilos_vendidos=Sum('total_kilos')
    ).order_by('total_diferencia') 

    context = {
        'anio_actual': anio_actual,
        'mes_actual': mes_actual,
        'bodega_seleccionada': bodega_seleccionada,
        'anios_disponibles': range(2024, hoy.year + 2),
        'meses_disponibles': range(1, 13),
        'kpi_kilos': kpi_kilos,
        'kpi_dinero': kpi_dinero,
        'kpi_balance': kpi_balance,
        'chart_labels': json.dumps(fechas_labels),
        'chart_kilos': json.dumps(data_kilos),
        'chart_balance': json.dumps(data_balance),
        'chart_estados': json.dumps([estados['cuadrado'], estados['faltante'], estados['sobrante']]),
        
        'ranking': ranking, # Pasamos la lista ordenada
    }

    return render(request, 'gestion/caja_trabajador/estadisticas.html', context)

# ... al final del archivo ...

@login_required
def configurar_comisiones(request):
    """
    Vista para editar las tarifas de pago por cilindro.
    Funciona como un 'Singleton' (siempre edita el último registro activo).
    """
    # 1. Obtener la última tarifa o crear una vacía si es la primera vez
    tarifas = TarifaComision.objects.last()
    if not tarifas:
        tarifas = TarifaComision.objects.create(nombre="Tarifa Inicial 2025")

    # 2. Guardar cambios
    if request.method == 'POST':
        try:
            tarifas.tarifa_5kg = int(request.POST.get('tarifa_5kg') or 0)
            tarifas.tarifa_11kg = int(request.POST.get('tarifa_11kg') or 0)
            tarifas.tarifa_15kg = int(request.POST.get('tarifa_15kg') or 0)
            tarifas.tarifa_45kg = int(request.POST.get('tarifa_45kg') or 0)
            
            tarifas.tarifa_cat_5kg = int(request.POST.get('tarifa_cat_5kg') or 0)
            tarifas.tarifa_cat_15kg = int(request.POST.get('tarifa_cat_15kg') or 0)
            tarifas.tarifa_ultra_15kg = int(request.POST.get('tarifa_ultra_15kg') or 0)
            
            tarifas.save()
            messages.success(request, "✅ Tarifas de comisión actualizadas correctamente.")
            
            # Redirigir de vuelta al reporte mensual
            return redirect('reporte_mensual_trabajador')
            
        except Exception as e:
            messages.error(request, f"Error al guardar: {e}")

    return render(request, 'gestion/caja_trabajador/config_comisiones.html', {'tarifas': tarifas})