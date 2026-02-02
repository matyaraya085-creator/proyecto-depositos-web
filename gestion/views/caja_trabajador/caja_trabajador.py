from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum, Count, Case, When, IntegerField, F
from django.urls import reverse
from django.db import transaction # Importante para evitar corrupción de datos
from datetime import date, datetime
from django.http import JsonResponse, HttpResponse
import json
import locale
import calendar
from gestion.models import RendicionDiaria, Trabajador, BODEGA_CHOICES, TarifaComision, CierreDiario

# Imports para PDF
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    pass

# Helper para conversiones seguras
def safe_int(valor):
    try:
        if valor is None or valor == '': 
            return 0
        return int(valor)
    except (ValueError, TypeError):
        return 0

# ==========================================
# 1. MENÚ PRINCIPAL
# ==========================================
@login_required
def menu_trabajadores(request):
    return render(request, 'gestion/caja_trabajador/trabajador_menu.html')

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
    url_dashboard = reverse('dashboard_bodega')

    # --- LÓGICA DE CIERRE GLOBAL (POST) ---
    if request.method == 'POST' and 'accion_global' in request.POST:
        accion = request.POST.get('accion_global')
        
        # 1. ACCIÓN: CERRAR DÍA
        if accion == 'cerrar_dia':
            CierreDiario.objects.get_or_create(
                fecha=fecha_seleccionada, 
                bodega=bodega_id, 
                defaults={'cerrado_por': request.user}
            )
            # Cerrar masivamente todas las rendiciones individuales
            RendicionDiaria.objects.filter(
                fecha=fecha_seleccionada, 
                bodega=bodega_id
            ).update(cerrado=True)

            messages.success(request, f"🔒 Día {str_fecha_db} CERRADO globalmente. Todas las cajas individuales han sido cerradas.")
        
        # 2. ACCIÓN: ABRIR DÍA (Solo ADMIN)
        elif accion == 'abrir_dia':
            if request.user.is_superuser:
                CierreDiario.objects.filter(fecha=fecha_seleccionada, bodega=bodega_id).delete()
                # Reabrir masivamente
                RendicionDiaria.objects.filter(
                    fecha=fecha_seleccionada, 
                    bodega=bodega_id
                ).update(cerrado=False)

                messages.warning(request, f"🔓 Día {str_fecha_db} REABIERTO globalmente. Las cajas han sido desbloqueadas.")
            else:
                messages.error(request, "⛔ Solo los administradores pueden REABRIR un día cerrado.")
        
        return redirect(f"{url_dashboard}?bodega={bodega_id}&fecha={str_fecha_db}")

    # --- CONSULTAS ---
    cierre_obj = CierreDiario.objects.filter(fecha=fecha_seleccionada, bodega=bodega_id).first()
    esta_cerrado_global = (cierre_obj is not None)

    rendiciones = RendicionDiaria.objects.filter(
        fecha=fecha_seleccionada,
        bodega=bodega_id 
    ).select_related('trabajador').order_by('created_at')

    # --- FILTRO APLICADO AQUÍ ---
    trabajadores_disponibles = Trabajador.objects.filter(
        Q(bodega_asignada=bodega_id) | Q(bodega_asignada='Ambos'),
        activo=True,
        filtro_trabajador=True
    ).order_by('nombre')

    total_kg_dia = sum(r.total_kilos for r in rendiciones)
    total_diferencia_dia = sum(r.diferencia for r in rendiciones) 

    # --- CORRECCIÓN ERROR 3: ESTADOS VISUALES MEJORADOS ---
    for r in rendiciones:
        r.estado_dinero = "PENDIENTE"
        r.clase_estado = "bg-secondary"
        
        # LÓGICA CORREGIDA:
        if r.total_venta > 0 or r.efectivo_entregado > 0 or r.cerrado:
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
        'esta_cerrado_global': esta_cerrado_global, 
    }
    
    return render(request, 'gestion/caja_trabajador/liquidaciones/trabajadores_liquidacion_lista.html', context)

# ==========================================
# 3. CREACIÓN DE RENDICIÓN
# ==========================================
@login_required
def crear_rendicion_vacia(request):
    if request.method == 'POST':
        fecha_str = request.POST.get('fecha')
        bodega_id = request.POST.get('bodega_id')
        
        url_dashboard = reverse('dashboard_bodega')

        # Verificar bloqueo global
        if CierreDiario.objects.filter(fecha=fecha_str, bodega=bodega_id).exists():
            messages.error(request, "⛔ El día está cerrado globalmente. No se pueden agregar turnos.")
            return redirect(f"{url_dashboard}?bodega={bodega_id}&fecha={fecha_str}")

        trabajador_id = request.POST.get('trabajador_id')
        trabajador = get_object_or_404(Trabajador, id=trabajador_id)
        fecha = date.fromisoformat(fecha_str)

        rendicion = RendicionDiaria.objects.create(
            trabajador=trabajador,
            fecha=fecha,
            bodega=bodega_id,
            detalle_gastos='[]'
        )
        
        return redirect('form_rendicion_editar', rendicion_id=rendicion.id)
    
    return redirect('menu_trabajadores')

@login_required
def eliminar_rendicion(request, rendicion_id):
    rendicion = get_object_or_404(RendicionDiaria, id=rendicion_id)
    bodega_id = rendicion.bodega
    fecha_str = rendicion.fecha.strftime('%Y-%m-%d')
    
    url_dashboard = reverse('dashboard_bodega')
    url_retorno = f"{url_dashboard}?bodega={bodega_id}&fecha={fecha_str}"
    
    if CierreDiario.objects.filter(fecha=rendicion.fecha, bodega=rendicion.bodega).exists():
        messages.error(request, "⛔ El día está cerrado globalmente.")
        return redirect(url_retorno)

    if not request.user.is_superuser and rendicion.cerrado:
        messages.error(request, "⛔ No puedes eliminar una rendición que ya fue CERRADA.")
        return redirect(url_retorno)

    rendicion.delete()
    messages.success(request, "Rendición eliminada correctamente.")
    
    return redirect(url_retorno)

# ==========================================
# 4. FORMULARIO DE EDICIÓN
# ==========================================
@login_required
def form_rendicion_editar(request, rendicion_id):
    rendicion = get_object_or_404(RendicionDiaria, id=rendicion_id)
    trabajador = rendicion.trabajador
    bodega_actual = rendicion.bodega 

    dia_cerrado_global = CierreDiario.objects.filter(fecha=rendicion.fecha, bodega=bodega_actual).exists()

    if request.method == 'POST':
        # 1. Chequeo de Cierre Global
        if dia_cerrado_global:
            messages.error(request, "⛔ ACCIÓN DENEGADA: El día tiene un Cierre Global.")
            return redirect('form_rendicion_editar', rendicion_id=rendicion.id)

        accion = request.POST.get('accion')

        # 2. Lógica de REAPERTURA (Exclusiva para Superadmin)
        if accion == 'reabrir':
            if request.user.is_superuser:
                rendicion.cerrado = False
                rendicion.save(update_fields=['cerrado', 'updated_at'])
                messages.success(request, "🔓 Rendición REABIERTA exitosamente.")
                return redirect('form_rendicion_editar', rendicion_id=rendicion.id)
            else:
                messages.error(request, "⛔ No tienes permisos para reabrir.")
                return redirect('form_rendicion_editar', rendicion_id=rendicion.id)

        # 3. Verificación si está cerrada y no es admin
        if rendicion.cerrado and not request.user.is_superuser:
            messages.error(request, "⛔ Esta rendición está CERRADA individualmente.")
            return redirect('form_rendicion_editar', rendicion_id=rendicion.id)
        
        # 4. PROTECCIÓN ADICIONAL
        if rendicion.cerrado and request.user.is_superuser:
            if 'gas_5kg' not in request.POST:
                messages.warning(request, "⚠️ Para editar datos, primero debe REABRIR la caja usando el botón 'Reabrir'.")
                return redirect('form_rendicion_editar', rendicion_id=rendicion.id)

        # 5. PROCESO DE GUARDADO DE DATOS
        try:
            with transaction.atomic():
                def get_val(key, default_val):
                    if key in request.POST:
                        return safe_int(request.POST.get(key))
                    return default_val

                rendicion.gas_5kg = get_val('gas_5kg', rendicion.gas_5kg)
                rendicion.gas_11kg = get_val('gas_11kg', rendicion.gas_11kg)
                rendicion.gas_15kg = get_val('gas_15kg', rendicion.gas_15kg)
                rendicion.gas_45kg = get_val('gas_45kg', rendicion.gas_45kg)
                
                rendicion.gasc_5kg = get_val('gasc_5kg', rendicion.gasc_5kg)
                rendicion.gasc_15kg = get_val('gasc_15kg', rendicion.gasc_15kg)
                rendicion.gas_ultra_15kg = get_val('gas_ultra_15kg', rendicion.gas_ultra_15kg)
                
                rendicion.cilindros_defectuosos = get_val('cilindros_defectuosos', rendicion.cilindros_defectuosos)
                
                # Recálculo de Kilos
                rendicion.total_kilos = (rendicion.gas_5kg * 5) + \
                                        (rendicion.gas_11kg * 11) + \
                                        (rendicion.gas_15kg * 15) + \
                                        (rendicion.gas_45kg * 45) + \
                                        (rendicion.gasc_5kg * 5) + \
                                        (rendicion.gasc_15kg * 15) + \
                                        (rendicion.gas_ultra_15kg * 15)

                # --- 2. CAJA Y GASTOS ---
                rendicion.total_venta = get_val('total_venta', rendicion.total_venta)
                
                rendicion.monto_vales = get_val('monto_vales', rendicion.monto_vales)
                rendicion.monto_transbank = get_val('monto_transbank', rendicion.monto_transbank)
                rendicion.monto_credito = get_val('monto_credito', rendicion.monto_credito)
                rendicion.monto_anticipo = get_val('monto_anticipo', rendicion.monto_anticipo)

                # Procesamiento JSON
                if 'detalle_gastos' in request.POST:
                    json_gastos = request.POST.get('detalle_gastos') or '[]'
                    rendicion.detalle_gastos = json_gastos 
                    try:
                        lista_gastos = json.loads(json_gastos)
                        total_gastos_calculado = sum(safe_int(item.get('monto')) for item in lista_gastos)
                        rendicion.gasto_total = total_gastos_calculado
                    except:
                        pass 
                
                # Efectivo Real
                rendicion.efectivo_entregado = get_val('efectivo_entregado', rendicion.efectivo_entregado)

                # Cálculo Matemático Final
                rendicion.efectivo_esperado = rendicion.total_venta - (
                    rendicion.monto_vales + 
                    rendicion.monto_transbank + 
                    rendicion.monto_credito +
                    rendicion.gasto_total +
                    rendicion.monto_anticipo 
                )
                
                rendicion.diferencia = rendicion.efectivo_entregado - rendicion.efectivo_esperado
                
                # 6. DECISIÓN DE ACCIÓN
                if accion == 'cerrar':
                    rendicion.cerrado = True
                    rendicion.save()
                    messages.success(request, f'🔒 Caja CERRADA correctamente.')
                    
                    url_dashboard = reverse('dashboard_bodega')
                    fecha_str = rendicion.fecha.strftime('%Y-%m-%d')
                    return redirect(f"{url_dashboard}?bodega={bodega_actual}&fecha={fecha_str}")
                
                else:
                    rendicion.save()
                    messages.success(request, f'💾 Guardado correctamente.')
                    return redirect('form_rendicion_editar', rendicion_id=rendicion.id)

        except Exception as e:
            messages.error(request, f'Error crítico al guardar: {str(e)}')
            
    context = {
        'rendicion': rendicion,
        'trabajador': trabajador,
        'bodega_actual': bodega_actual,
        'fecha_str': rendicion.fecha.strftime('%Y-%m-%d'),
        'dia_cerrado_global': dia_cerrado_global
    }
    return render(request, 'gestion/caja_trabajador/liquidaciones/trabajadores_liquidacion_editor.html', context)

@login_required
def cerrar_rendicion(request, rendicion_id):
    rendicion = get_object_or_404(RendicionDiaria, id=rendicion_id)
    bodega = rendicion.bodega
    fecha_str = rendicion.fecha.strftime('%Y-%m-%d')
    
    url_dashboard = reverse('dashboard_bodega')
    url_retorno = f"{url_dashboard}?bodega={bodega}&fecha={fecha_str}"

    if CierreDiario.objects.filter(fecha=rendicion.fecha, bodega=rendicion.bodega).exists():
        messages.error(request, "⛔ Día Cerrado Globalmente.")
    else:
        rendicion.cerrado = True
        rendicion.save()
        
    return redirect(url_retorno)

@login_required
def abrir_rendicion(request, rendicion_id):
    rendicion = get_object_or_404(RendicionDiaria, id=rendicion_id)
    bodega = rendicion.bodega
    fecha_str = rendicion.fecha.strftime('%Y-%m-%d')
    
    url_dashboard = reverse('dashboard_bodega')
    url_retorno = f"{url_dashboard}?bodega={bodega}&fecha={fecha_str}"

    if not request.user.is_superuser:
        messages.error(request, "Solo administradores.")
    else:
        rendicion.cerrado = False
        rendicion.save()
        
    return redirect(url_retorno)

# ==========================================
# 5. REPORTE MENSUAL
# ==========================================
@login_required
def reporte_mensual(request):
    trabajador_id = request.GET.get('trabajador_id')
    fecha_str = request.GET.get('fecha_seleccionada')
    
    trabajadores = Trabajador.objects.filter(
        activo=True,
        filtro_trabajador=True
    ).order_by('nombre')

    trabajador_seleccionado = None
    report_data = None
    
    hoy = timezone.now()
    if not fecha_str:
        fecha_str = hoy.strftime('%Y-%m')
        
    try:
        anio, mes = map(int, fecha_str.split('-'))
    except ValueError:
        anio, mes = hoy.year, hoy.month

    if anio < hoy.year or (anio == hoy.year and mes < hoy.month):
        messages.warning(request, 
            f"⚠️ ATENCIÓN: Estás consultando un periodo histórico ({mes}/{anio}), pero el cálculo usa las TARIFAS VIGENTES hoy.")

    tarifas = TarifaComision.objects.last()
    if not tarifas:
        tarifas = TarifaComision()

    _, num_dias_mes = calendar.monthrange(anio, mes)
    
    matriz_mensual = {}
    for d in range(1, num_dias_mes + 1):
        matriz_mensual[d] = {
            'c5': 0, 'c11': 0, 'c15': 0, 'c45': 0,
            'cat5': 0, 'cat15': 0, 'ultra': 0,
            'defectuosos': 0,
            'total_kg': 0
        }

    acumulador_mensual = {
        'c5': 0, 'c11': 0, 'c15': 0, 'c45': 0,
        'cat5': 0, 'cat15': 0, 'ultra': 0,
        'defectuosos': 0
    }

    if trabajador_id:
        trabajador_seleccionado = get_object_or_404(Trabajador, id=trabajador_id)
        
        rendiciones = RendicionDiaria.objects.filter(
            trabajador=trabajador_seleccionado,
            fecha__year=anio,
            fecha__month=mes
        ).order_by('fecha', 'created_at')

        dias_agrupados = {}
        total_kilos_mes = 0
        balance_mes = 0
        total_anticipos = 0

        for r in rendiciones:
            dia_num = r.fecha.day 
            fecha_key = r.fecha
            
            if fecha_key not in dias_agrupados:
                dias_agrupados[fecha_key] = {
                    'fecha': r.fecha,
                    'total_kg': 0,
                    'total_balance': 0,
                    'total_anticipo_dia': 0,
                    'turnos': [],
                    'resumen_dia': {'c5': 0, 'c11': 0, 'c15': 0, 'c45': 0, 'cat5': 0, 'cat15': 0, 'ultra': 0, 'defectuosos': 0}
                }
            
            current_day = dias_agrupados[fecha_key]
            current_day['total_kg'] += r.total_kilos
            current_day['total_balance'] += r.diferencia
            current_day['total_anticipo_dia'] += r.monto_anticipo 
            current_day['turnos'].append(r)
            
            current_day['resumen_dia']['c5'] += r.gas_5kg
            current_day['resumen_dia']['c11'] += r.gas_11kg
            current_day['resumen_dia']['c15'] += r.gas_15kg
            current_day['resumen_dia']['c45'] += r.gas_45kg
            current_day['resumen_dia']['cat5'] += r.gasc_5kg
            current_day['resumen_dia']['cat15'] += r.gasc_15kg
            current_day['resumen_dia']['ultra'] += r.gas_ultra_15kg
            current_day['resumen_dia']['defectuosos'] += r.cilindros_defectuosos

            total_kilos_mes += r.total_kilos
            balance_mes += r.diferencia
            total_anticipos += r.monto_anticipo 
            
            acumulador_mensual['c5'] += r.gas_5kg
            acumulador_mensual['c11'] += r.gas_11kg
            acumulador_mensual['c15'] += r.gas_15kg
            acumulador_mensual['c45'] += r.gas_45kg
            acumulador_mensual['cat5'] += r.gasc_5kg
            acumulador_mensual['cat15'] += r.gasc_15kg
            acumulador_mensual['ultra'] += r.gas_ultra_15kg
            acumulador_mensual['defectuosos'] += r.cilindros_defectuosos

            matriz_mensual[dia_num]['c5'] += r.gas_5kg
            matriz_mensual[dia_num]['c11'] += r.gas_11kg
            matriz_mensual[dia_num]['c15'] += r.gas_15kg
            matriz_mensual[dia_num]['c45'] += r.gas_45kg
            matriz_mensual[dia_num]['cat5'] += r.gasc_5kg
            matriz_mensual[dia_num]['cat15'] += r.gasc_15kg
            matriz_mensual[dia_num]['ultra'] += r.gas_ultra_15kg
            matriz_mensual[dia_num]['total_kg'] += r.total_kilos

        lista_detalle = sorted(dias_agrupados.values(), key=lambda x: x['fecha'])

        dinero_comision = (acumulador_mensual['c5'] * tarifas.tarifa_5kg) + \
                          (acumulador_mensual['c11'] * tarifas.tarifa_11kg) + \
                          (acumulador_mensual['c15'] * tarifas.tarifa_15kg) + \
                          (acumulador_mensual['c45'] * tarifas.tarifa_45kg) + \
                          (acumulador_mensual['cat5'] * tarifas.tarifa_cat_5kg) + \
                          (acumulador_mensual['cat15'] * tarifas.tarifa_cat_15kg) + \
                          (acumulador_mensual['ultra'] * tarifas.tarifa_ultra_15kg)

        report_data = {
            'detalle_dias': lista_detalle,
            'tabla_general': matriz_mensual, 
            'total_kilos': total_kilos_mes,
            'balance': balance_mes,
            'total_comision': dinero_comision,
            'detalle_fisico': acumulador_mensual,
            'total_anticipos': total_anticipos
        }

    context = {
        'trabajadores': trabajadores,
        'trabajador_seleccionado': trabajador_seleccionado,
        'fecha_seleccionada': fecha_str,
        'report_data': report_data
    }
    return render(request, 'gestion/caja_trabajador/reporte_mensual/trabajador_reporte_mensual.html', context)

# ==========================================
# 6. ESTADÍSTICAS Y CONFIG
# ==========================================
@login_required
def estadisticas_globales(request):
    hoy = timezone.now()
    try:
        anio_actual = int(request.GET.get('anio', hoy.year))
        mes_actual = int(request.GET.get('mes', hoy.month))
    except ValueError:
        anio_actual = hoy.year
        mes_actual = hoy.month
        
    bodega_seleccionada = request.GET.get('bodega', '')

    rendiciones = RendicionDiaria.objects.filter(
        fecha__year=anio_actual,
        fecha__month=mes_actual
    )

    if bodega_seleccionada in ['1221', '1225']:
        rendiciones = rendiciones.filter(bodega=bodega_seleccionada)

    resumen = rendiciones.aggregate(
        total_kilos=Sum('total_kilos'),
        total_dinero=Sum('total_venta'),
        balance_neto=Sum('diferencia')
    )
    
    kpi_kilos = resumen['total_kilos'] or 0
    kpi_dinero = resumen['total_dinero'] or 0
    kpi_balance = resumen['balance_neto'] or 0

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

    ranking = rendiciones.values('trabajador__nombre').annotate(
        total_diferencia=Sum('diferencia'),
        total_kilos_vendidos=Sum('total_kilos')
    ).order_by('total_diferencia')

    lista_meses = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
    ]
    
    lista_anios = range(2025, 2031)

    context = {
        'anio_actual': anio_actual,
        'mes_actual': mes_actual,
        'bodega_seleccionada': bodega_seleccionada,
        'anios_disponibles': lista_anios,
        'meses_disponibles': lista_meses,
        'kpi_kilos': kpi_kilos,
        'kpi_dinero': kpi_dinero,
        'kpi_balance': kpi_balance,
        'chart_labels': json.dumps(fechas_labels),
        'chart_kilos': json.dumps(data_kilos),
        'chart_balance': json.dumps(data_balance),
        'chart_estados': json.dumps([estados['cuadrado'], estados['faltante'], estados['sobrante']]),
        'ranking': ranking,
    }

    return render(request, 'gestion/caja_trabajador/trabajador_estadisticas_mensual.html', context)

@login_required
def configurar_comisiones(request):
    if not request.user.is_superuser:
        messages.error(request, "⛔ Acceso denegado: Solo administradores pueden configurar tarifas.")
        return redirect('reporte_mensual_trabajador')

    tarifas = TarifaComision.objects.last()
    if not tarifas:
        tarifas = TarifaComision.objects.create(nombre="Tarifa Inicial 2025")

    if request.method == 'POST':
        try:
            tarifas.tarifa_5kg = safe_int(request.POST.get('tarifa_5kg'))
            tarifas.tarifa_11kg = safe_int(request.POST.get('tarifa_11kg'))
            tarifas.tarifa_15kg = safe_int(request.POST.get('tarifa_15kg'))
            tarifas.tarifa_45kg = safe_int(request.POST.get('tarifa_45kg'))
            
            tarifas.tarifa_cat_5kg = safe_int(request.POST.get('tarifa_cat_5kg'))
            tarifas.tarifa_cat_15kg = safe_int(request.POST.get('tarifa_cat_15kg'))
            tarifas.tarifa_ultra_15kg = safe_int(request.POST.get('tarifa_ultra_15kg'))
            
            tarifas.save()
            messages.success(request, "✅ Tarifas de comisión actualizadas correctamente.")
            return redirect('reporte_mensual_trabajador')
            
        except Exception as e:
            messages.error(request, f"Error al guardar: {e}")

    return render(request, 'gestion/caja_trabajador/reporte_mensual/trabajador_comisiones.html', {'tarifas': tarifas})

@login_required
def api_auto_guardar_rendicion(request, rendicion_id):
    if request.method == 'POST':
        rendicion = get_object_or_404(RendicionDiaria, id=rendicion_id)
        
        if rendicion.cerrado:
            return JsonResponse({'status': 'error', 'message': 'CAJA CERRADA: Debe reabrir para editar.'}, status=403)
             
        if CierreDiario.objects.filter(fecha=rendicion.fecha, bodega=rendicion.bodega).exists():
             return JsonResponse({'status': 'error', 'message': 'Día cerrado globalmente'}, status=403)

        try:
            with transaction.atomic():
                # --- 1. PROCESAR INVENTARIO (KILOS) ---
                rendicion.gas_5kg = safe_int(request.POST.get('gas_5kg'))
                rendicion.gas_11kg = safe_int(request.POST.get('gas_11kg'))
                rendicion.gas_15kg = safe_int(request.POST.get('gas_15kg'))
                rendicion.gas_45kg = safe_int(request.POST.get('gas_45kg'))
                
                rendicion.gasc_5kg = safe_int(request.POST.get('gasc_5kg'))
                rendicion.gasc_15kg = safe_int(request.POST.get('gasc_15kg'))
                rendicion.gas_ultra_15kg = safe_int(request.POST.get('gas_ultra_15kg'))
                
                rendicion.cilindros_defectuosos = safe_int(request.POST.get('cilindros_defectuosos'))
                
                # Recálculo de Kilos
                rendicion.total_kilos = (rendicion.gas_5kg * 5) + \
                                        (rendicion.gas_11kg * 11) + \
                                        (rendicion.gas_15kg * 15) + \
                                        (rendicion.gas_45kg * 45) + \
                                        (rendicion.gasc_5kg * 5) + \
                                        (rendicion.gasc_15kg * 15) + \
                                        (rendicion.gas_ultra_15kg * 15)

                # --- 2. PROCESAR CAJA Y GASTOS ---
                rendicion.total_venta = safe_int(request.POST.get('total_venta'))
                rendicion.monto_vales = safe_int(request.POST.get('monto_vales'))
                rendicion.monto_transbank = safe_int(request.POST.get('monto_transbank'))
                rendicion.monto_credito = safe_int(request.POST.get('monto_credito')) 
                rendicion.monto_anticipo = safe_int(request.POST.get('monto_anticipo'))

                rendicion.efectivo_entregado = safe_int(request.POST.get('efectivo_entregado'))
                
                json_gastos = request.POST.get('detalle_gastos') or '[]'
                rendicion.detalle_gastos = json_gastos 
                
                try:
                    lista_gastos = json.loads(json_gastos)
                    total_gastos_calculado = sum(safe_int(item.get('monto')) for item in lista_gastos)
                except:
                    total_gastos_calculado = 0
                
                rendicion.gasto_total = total_gastos_calculado

                rendicion.efectivo_esperado = rendicion.total_venta - (
                    rendicion.monto_vales + 
                    rendicion.monto_transbank + 
                    rendicion.monto_credito +
                    rendicion.gasto_total +
                    rendicion.monto_anticipo 
                )
                
                rendicion.diferencia = rendicion.efectivo_entregado - rendicion.efectivo_esperado
                
                rendicion.save()
            
            return JsonResponse({'status': 'ok', 'message': 'Guardado'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
    return JsonResponse({'status': 'error'}, status=400)

# ==========================================
# 7. GENERACIÓN PDF MENSUAL
# ==========================================
@login_required
def exportar_pdf_mensual(request):
    trabajador_id = request.GET.get('trabajador_id')
    fecha_str = request.GET.get('fecha_seleccionada')
    
    if not trabajador_id or not fecha_str:
        messages.error(request, "Datos insuficientes para generar reporte")
        return redirect('reporte_mensual_trabajador')
    
    trabajador = get_object_or_404(Trabajador, id=trabajador_id)
    anio, mes = map(int, fecha_str.split('-'))
    
    # Obtener rendiciones ordenadas
    rendiciones = RendicionDiaria.objects.filter(
        trabajador=trabajador,
        fecha__year=anio,
        fecha__month=mes
    ).order_by('fecha', 'created_at')

    # --- CÁLCULO DE TOTALES ---
    total_kilos = 0
    total_balance = 0
    total_anticipos = 0
    
    # Contadores físicos
    c5 = c11 = c15 = c45 = cat5 = cat15 = ultra = defectuosos = 0
    
    # Contadores monetarios detallados
    total_venta = 0
    total_tbk = 0
    total_credito = 0
    total_gastos = 0
    total_efectivo = 0
    total_prepagos = 0 # Nuevo para Vales

    for r in rendiciones:
        # Sumas Físicas
        c5 += r.gas_5kg
        c11 += r.gas_11kg
        c15 += r.gas_15kg
        c45 += r.gas_45kg
        cat5 += r.gasc_5kg
        cat15 += r.gasc_15kg
        ultra += r.gas_ultra_15kg
        defectuosos += r.cilindros_defectuosos
        
        # Sumas Generales
        total_kilos += r.total_kilos
        total_balance += r.diferencia
        total_anticipos += r.monto_anticipo
        
        # Sumas Detalladas Monetarias
        total_venta += r.total_venta
        total_tbk += r.monto_transbank
        total_credito += r.monto_credito
        total_efectivo += r.efectivo_entregado
        total_prepagos += r.monto_vales
        
        # Calcular Gasto real (por si acaso el total no coincide con json)
        try:
            lista = json.loads(r.detalle_gastos)
            gasto_dia = sum(safe_int(item.get('monto')) for item in lista)
        except:
            gasto_dia = r.gasto_total
        total_gastos += gasto_dia

    # CALCULAR COMISIÓN
    tarifas = TarifaComision.objects.last()
    if not tarifas:
        tarifas = TarifaComision()
        
    comision_estimada = (c5 * tarifas.tarifa_5kg) + \
                        (c11 * tarifas.tarifa_11kg) + \
                        (c15 * tarifas.tarifa_15kg) + \
                        (c45 * tarifas.tarifa_45kg) + \
                        (cat5 * tarifas.tarifa_cat_5kg) + \
                        (cat15 * tarifas.tarifa_cat_15kg) + \
                        (ultra * tarifas.tarifa_ultra_15kg)

    # --- CONFIGURACIÓN REPORTLAB ---
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(LETTER), topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    
    # ESTILOS PERSONALIZADOS
    style_titulo = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=16, alignment=1, spaceAfter=10)
    style_subtitulo = ParagraphStyle('Subtitulo', parent=styles['Normal'], fontSize=12, alignment=1, spaceAfter=20)
    
    # 1. ENCABEZADO
    elements.append(Paragraph(f"Resumen Mensual de Rendiciones", style_titulo))
    elements.append(Paragraph(f"<b>Trabajador:</b> {trabajador.nombre} | <b>Periodo:</b> {mes}/{anio}", style_subtitulo))
    
    # 2. TABLA DE TOTALES (RESUMEN SUPERIOR) - Agregado PREPAGOS
    data_resumen = [
        ['TOTAL KILOS', 'BALANCE NETO', 'ANTICIPOS', 'GASTOS', 'TRANSBANK', 'PREPAGOS'],
        [
            f"{int(total_kilos)} Kg",
            f"${total_balance:,.0f}".replace(',', '.'),
            f"${total_anticipos:,.0f}".replace(',', '.'),
            f"${total_gastos:,.0f}".replace(',', '.'),
            f"${total_tbk:,.0f}".replace(',', '.'),
            f"${total_prepagos:,.0f}".replace(',', '.')
        ]
    ]
    
    # Ajuste ancho columnas para que quepan 6
    t_resumen = Table(data_resumen, colWidths=[1.2*inch]*6)
    t_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0d6efd')), # Azul Encabezado
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#f8f9fa')),
        ('FONTSIZE', (0,1), (-1,1), 11),
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    elements.append(t_resumen)
    elements.append(Spacer(1, 10))

    # 3. TABLA DE CILINDROS (RESUMEN FÍSICO)
    data_cilindros = [
        ['5kg', '11kg', '15kg', '45kg', 'Cat 5', 'Cat 15', 'Ultra', 'Defect.'],
        [c5, c11, c15, c45, cat5, cat15, ultra, defectuosos]
    ]
    
    t_cilindros = Table(data_cilindros, colWidths=[1*inch]*8)
    t_cilindros.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#6c757d')), # Gris
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    elements.append(t_cilindros)
    elements.append(Spacer(1, 20))
    
    # 4. TABLA DETALLADA DÍA A DÍA (DINERO)
    elements.append(Paragraph("Detalle Financiero Diario", style_subtitulo))
    
    headers_detalle = ['Fecha', 'Bodega', 'Tot. Venta', 'Prepago', 'Crédito', 'Transbank', 'Gastos', 'Anticipo', 'Efectivo Real', 'Diferencia']
    data_detalle = [headers_detalle]

    headers_fisico = ['Fecha', 'Bodega', '5kg', '11kg', '15kg', '45kg', 'Cat5', 'Cat15', 'Ultra', 'Defect.']
    data_fisico = [headers_fisico]

    for r in rendiciones:
        try:
            l_gastos = json.loads(r.detalle_gastos)
            g_dia = sum(safe_int(x.get('monto')) for x in l_gastos)
        except:
            g_dia = r.gasto_total
            
        # FILA DINERO
        row_dinero = [
            r.fecha.strftime('%d/%m'),
            r.bodega,
            f"${r.total_venta:,.0f}",
            f"${r.monto_vales:,.0f}",
            f"${r.monto_credito:,.0f}",
            f"${r.monto_transbank:,.0f}",
            f"${g_dia:,.0f}",
            f"${r.monto_anticipo:,.0f}",
            f"${r.efectivo_entregado:,.0f}",
            f"${r.diferencia:,.0f}"
        ]
        data_detalle.append(row_dinero)
        
        # FILA FISICA
        row_fisico = [
            r.fecha.strftime('%d/%m'),
            r.bodega,
            str(r.gas_5kg),
            str(r.gas_11kg),
            str(r.gas_15kg),
            str(r.gas_45kg),
            str(r.gasc_5kg),
            str(r.gasc_15kg),
            str(r.gas_ultra_15kg),
            str(r.cilindros_defectuosos)
        ]
        data_fisico.append(row_fisico)
        
    # --- CONSTRUCCIÓN TABLA DINERO ---
    col_widths_dinero = [0.6*inch, 0.6*inch, 0.9*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.9*inch, 0.9*inch]
    t_detalle = Table(data_detalle, colWidths=col_widths_dinero, repeatRows=1)
    
    estilo_dinero = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#198754')), # Verde Encabezado
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]
    
    # Colorear diferencia
    for i, row in enumerate(data_detalle[1:], start=1):
        val_dif = int(row[9].replace('$','').replace('.','').replace(',',''))
        if val_dif < 0:
            estilo_dinero.append(('TEXTCOLOR', (9, i), (9, i), colors.red))
        elif val_dif > 0:
            estilo_dinero.append(('TEXTCOLOR', (9, i), (9, i), colors.blue))
        else:
            estilo_dinero.append(('TEXTCOLOR', (9, i), (9, i), colors.green))
            
    t_detalle.setStyle(TableStyle(estilo_dinero))
    elements.append(t_detalle)
    
    elements.append(Spacer(1, 25))
    
    # --- CONSTRUCCIÓN TABLA FÍSICA ---
    elements.append(Paragraph("Detalle de Carga Diaria (Cilindros)", style_subtitulo))
    
    col_widths_fisico = [0.8*inch, 0.8*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.6*inch]
    t_fisico = Table(data_fisico, colWidths=col_widths_fisico, repeatRows=1)
    
    estilo_fisico = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#6c757d')), # Gris Encabezado
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]
    t_fisico.setStyle(TableStyle(estilo_fisico))
    elements.append(t_fisico)

    # --- SECCIÓN FINAL: TOTAL GANADO ---
    elements.append(Spacer(1, 30))
    
    # Tabla simple para mostrar la ganancia final destacada
    data_ganancia = [
        ['TOTAL GANADO A LA FECHA (Estimado)'],
        [f"${comision_estimada:,.0f}".replace(',', '.')]
    ]
    
    t_ganancia = Table(data_ganancia, colWidths=[4*inch])
    t_ganancia.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#20c997')), # Verde turquesa
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 12),
        ('BOTTOMPADDING', (0,0), (-1,0), 10),
        ('TOPPADDING', (0,0), (-1,0), 10),
        ('BACKGROUND', (0,1), (-1,1), colors.white),
        ('TEXTCOLOR', (0,1), (-1,1), colors.black),
        ('FONTSIZE', (0,1), (-1,1), 16),
        ('BOX', (0,0), (-1,-1), 2, colors.HexColor('#20c997')),
    ]))
    
    elements.append(t_ganancia)

    # GENERAR PDF
    doc.build(elements)
    buffer.seek(0)
    
    filename = f"Reporte_{trabajador.nombre.replace(' ','_')}_{mes}_{anio}.pdf"
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response