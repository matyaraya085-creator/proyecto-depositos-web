import re
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db.models import Prefetch, Sum
from django.utils import timezone
from gestion.models import AfpConfig, SaludConfig, AsignacionFamiliarConfig, ConfiguracionGlobal, Trabajador, Remuneracion, RendicionDiaria
from django.db import IntegrityError
from datetime import date, datetime
import locale
import calendar
from decimal import Decimal, ROUND_HALF_UP
import json

# Intentamos configurar locale a español para los nombres de meses
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    pass

# ==========================================
# 1. VISTAS DE NAVEGACIÓN
# ==========================================

def menu_remuneraciones(request):
    """
    Vista que renderiza el menú principal de remuneraciones.
    """
    return render(request, 'gestion/remuneraciones/menu_remuneraciones.html')

def nomina_mensual(request):
    """
    Muestra la nómina filtrando trabajadores INTERNOS y ACTIVOS,
    gestionando el estado de avance según la fecha seleccionada.
    """
    # 1. Gestión de Fechas
    fecha_get = request.GET.get('fecha') # Formato YYYY-MM
    hoy = timezone.now()
    
    if fecha_get:
        try:
            anio = int(fecha_get.split('-')[0])
            mes = int(fecha_get.split('-')[1])
            fecha_seleccionada = date(anio, mes, 1)
        except ValueError:
            fecha_seleccionada = hoy.date()
    else:
        fecha_seleccionada = hoy.date()
    
    # String para el input type="month" (YYYY-MM)
    periodo_value = fecha_seleccionada.strftime('%Y-%m')
    # String para mostrar al usuario (Ej: Enero 2026)
    periodo_str = fecha_seleccionada.strftime('%B %Y').title()

    # 2. Filtro de Trabajadores
    # - Tipo: INTERNO (Contrato)
    # - Activo: True (Trabajando actualmente)
    trabajadores_qs = Trabajador.objects.filter(
        tipo='INTERNO', 
        activo=True
    ).order_by('nombre')

    # 3. Optimización con Prefetch
    # Buscamos solo las liquidaciones que coincidan EXACTAMENTE con el periodo seleccionado
    liquidaciones_del_mes = Remuneracion.objects.filter(periodo=periodo_value)

    # Adjuntamos la liquidación al objeto trabajador si existe
    trabajadores_qs = trabajadores_qs.prefetch_related(
        Prefetch('remuneracion_set', queryset=liquidaciones_del_mes, to_attr='liquidacion_mes')
    )

    # 4. Cálculo de Estadísticas (Avance)
    total_trabajadores = trabajadores_qs.count()
    calculados_count = 0
    
    lista_trabajadores = []
    
    for t in trabajadores_qs:
        # Al usar prefetch con to_attr, el resultado es una lista. 
        # Si tiene elementos, es que ya se calculó.
        liq = t.liquidacion_mes[0] if t.liquidacion_mes else None
        
        if liq:
            calculados_count += 1
            
        lista_trabajadores.append({
            'obj': t,
            'liquidacion': liq, # Pasamos el objeto liquidación o None
            'tiene_calculo': bool(liq)
        })

    context = {
        'trabajadores_lista': lista_trabajadores,
        'periodo_str': periodo_str,
        'periodo_value': periodo_value,
        'total_count': total_trabajadores,
        'calculados_count': calculados_count,
    }
    
    return render(request, 'gestion/remuneraciones/nomina_mensual.html', context)

def historial(request):
    """
    Muestra el historial de liquidaciones FILTRADO POR MES.
    """
    # 1. Gestión de Fechas (Igual que en nómina)
    fecha_get = request.GET.get('fecha') # Formato YYYY-MM
    hoy = timezone.now()
    
    if fecha_get:
        try:
            anio = int(fecha_get.split('-')[0])
            mes = int(fecha_get.split('-')[1])
            fecha_seleccionada = date(anio, mes, 1)
        except ValueError:
            fecha_seleccionada = hoy.date()
    else:
        fecha_seleccionada = hoy.date()
        
    periodo_value = fecha_seleccionada.strftime('%Y-%m')
    periodo_str = fecha_seleccionada.strftime('%B %Y').title()

    # 2. Filtrar Liquidaciones por el periodo seleccionado
    liquidaciones = Remuneracion.objects.filter(
        periodo=periodo_value
    ).select_related('trabajador').order_by('trabajador__nombre')
    
    # 3. Calcular Totales para mostrar resumen
    total_pagado = liquidaciones.aggregate(Sum('sueldo_liquido'))['sueldo_liquido__sum'] or 0
    total_registros = liquidaciones.count()

    context = {
        'liquidaciones': liquidaciones,
        'periodo_str': periodo_str,
        'periodo_value': periodo_value,
        'total_pagado': total_pagado,
        'total_registros': total_registros,
    }
    return render(request, 'gestion/remuneraciones/historial.html', context)

# ==========================================
# 2. UTILIDADES
# ==========================================

def format_currency_cl(value, decimal_places=0):
    """
    Formatea un número a string con punto de miles y coma decimal.
    """
    if value is None: return ""
    try:
        if decimal_places == 0:
            formatted = f"{int(value):,}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
        else:
            formatted = f"{value:,.{decimal_places}f}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
        return formatted
    except (ValueError, TypeError):
        return str(value)

def clean_currency(value):
    """Limpia cadenas de texto de símbolos de moneda, puntos de miles y comas para convertir a float."""
    if isinstance(value, str):
        value = value.replace('$', '').replace('.', '').replace(',', '.')
        try:
            return float(value)
        except ValueError:
            return 0.0
    return float(value) if value is not None else 0.0

def get_parametros_calculo():
    """Carga todos los parámetros necesarios en un solo diccionario."""
    config_raw = {c.clave: Decimal(str(c.valor)) for c in ConfiguracionGlobal.objects.all().iterator()}
    
    # Utilizamos el valor UF como tope de referencia para simplificar (81.6 UF)
    valor_uf = config_raw.get('valor_uf', Decimal('36500')) 
    tope_imponible_clp = valor_uf * Decimal('81.6')

    return {
        'sueldo_minimo': config_raw.get('sueldo_minimo', Decimal('460000')),
        'valor_uf': valor_uf,
        'valor_utm': config_raw.get('valor_utm', Decimal('64000')),
        'gratificacion_pct': config_raw.get('gratificacion_legal_pct', Decimal('25')) / 100,
        'seguro_cesantia_pct': config_raw.get('seguro_cesantia_pct', Decimal('0.6')) / 100,
        'tope_imponible': tope_imponible_clp.quantize(Decimal('1'), rounding=ROUND_HALF_UP),
        'tramos_af': AsignacionFamiliarConfig.objects.all().order_by('ingreso_tope'),
    }

# ==========================================
# 3. CONFIGURACIÓN Y PARÁMETROS
# ==========================================

def parametros(request):
    """
    Vista principal que carga toda la configuración y los modales.
    """
    afps = AfpConfig.objects.all().order_by('nombre')
    salud = SaludConfig.objects.all().order_by('nombre')
    tramos = AsignacionFamiliarConfig.objects.all().order_by('ingreso_tope')
    
    config_global_qs = ConfiguracionGlobal.objects.all()
    config_raw = {c.clave: c.valor for c in config_global_qs}

    db_vacia = not afps.exists() or not salud.exists() or not tramos.exists()

    # Solo enviamos lo que el usuario pidió ver: Gratificación y Seguro Cesantía
    config_formato = {
        'gratificacion_legal_pct': config_raw.get('gratificacion_legal_pct', 25.0),
        'seguro_cesantia_pct': config_raw.get('seguro_cesantia_pct', 0.6),
    }

    context = {
        'afps': afps,
        'salud': salud,
        'tramos': tramos,
        'config': config_formato,
        'db_vacia': db_vacia,
    }
    
    return render(request, 'gestion/remuneraciones/parametros.html', context)

def inicializar_parametros_remuneraciones(request):
    """Función de una sola vez para poblar los datos iniciales."""
    afps_default = [("Capital", 11.44), ("Cuprum", 11.44), ("Habitat", 11.27), ("Modelo", 10.58), ("Planvital", 11.16), ("Provida", 11.45), ("Uno", 10.69)]
    salud_default = [("Fonasa", 7.0), ("Isapre", 7.0)]
    asignacion_default = [("A", 620251, 22007), ("B", 905941, 13505), ("C", 1412957, 4267), ("D", 999999999, 0)]
    
    valores_default = [
        ('sueldo_minimo', 460000, 'Sueldo Mínimo Mensual'),
        ('valor_uf', 36500, 'Valor UF Previsional'),
        ('valor_utm', 63450, 'Valor UTM'),
        ("gratificacion_legal_pct", 25.0, "Porcentaje de Gratificación Legal"),
        ("seguro_cesantia_pct", 0.6, "Porcentaje Seguro de Cesantía (trabajador)"),
    ]

    try:
        for nombre, tasa in afps_default:
            AfpConfig.objects.get_or_create(nombre=nombre, defaults={'tasa': tasa})
        for nombre, tasa in salud_default:
            SaludConfig.objects.get_or_create(nombre=nombre, defaults={'tasa': tasa})
        for tramo, tope, monto in asignacion_default:
             AsignacionFamiliarConfig.objects.get_or_create(tramo=tramo, defaults={'ingreso_tope': tope, 'monto_por_carga': monto})

        for clave, valor, descripcion in valores_default:
            ConfiguracionGlobal.objects.get_or_create(clave=clave, defaults={'valor': valor, 'descripcion': descripcion})

        return redirect('parametros_remuneraciones')
    except IntegrityError:
        return redirect('parametros_remuneraciones')

def guardar_indicadores(request):
    """
    Guarda solo Gratificación y Seguro de Cesantía desde la vista simplificada.
    """
    if request.method == 'POST':
        data_map = {
            'gratificacion_legal_pct': 'gratificacion_legal_pct',
            'seguro_cesantia_pct': 'seguro_cesantia_pct'
        }
        
        for input_name, db_key in data_map.items():
            valor = request.POST.get(input_name)
            if valor:
                try:
                    val_float = float(valor.replace(',', '.'))
                    ConfiguracionGlobal.objects.update_or_create(
                        clave=db_key,
                        defaults={'valor': val_float, 'descripcion': input_name}
                    )
                except (ValueError, TypeError):
                    pass

    return redirect('parametros_remuneraciones')

def crear_entidad_previsional(request):
    """
    Crea una nueva AFP o Isapre desde el Modal.
    """
    if request.method == 'POST':
        tipo = request.POST.get('tipo_entidad') # 'afp' o 'salud'
        nombre = request.POST.get('nombre')
        tasa = request.POST.get('tasa')

        if nombre and tasa:
            try:
                tasa_float = float(tasa.replace(',', '.'))
                if tipo == 'afp':
                    AfpConfig.objects.create(nombre=nombre, tasa=tasa_float)
                elif tipo == 'salud':
                    SaludConfig.objects.create(nombre=nombre, tasa=tasa_float)
            except ValueError:
                pass 

    return redirect('parametros_remuneraciones')

def editar_tasa_previsional(request, modelo, nombre):
    """
    Recibe los datos del Modal de Edición y actualiza la tasa.
    """
    if request.method == 'POST':
        if modelo == 'afp': Model = AfpConfig
        elif modelo == 'salud': Model = SaludConfig
        else: return redirect('parametros_remuneraciones')

        instance = get_object_or_404(Model, nombre=nombre)
        try:
            nueva_tasa = float(request.POST.get('tasa', '0').replace(',', '.'))
            instance.tasa = nueva_tasa
            instance.save()
        except ValueError:
            pass
            
    return redirect('parametros_remuneraciones')

def editar_tramos_asignacion(request):
    """
    Recibe todos los tramos del Modal y los actualiza masivamente.
    """
    if request.method == 'POST':
        tramos_qs = AsignacionFamiliarConfig.objects.all()
        try:
            for tramo in tramos_qs:
                tope_raw = request.POST.get(f'tope_{tramo.tramo}', '0')
                monto_raw = request.POST.get(f'monto_{tramo.tramo}', '0')
                
                tramo.ingreso_tope = int(clean_currency(tope_raw))
                tramo.monto_por_carga = int(clean_currency(monto_raw))
                tramo.save()
        except Exception:
            pass
            
    return redirect('parametros_remuneraciones')


# ==========================================
# 4. LÓGICA CORE: CÁLCULO DE SUELDO
# ==========================================

def calcular_sueldo(request, id):
    """
    Calcula el sueldo soportando múltiples listas dinámicas y 
    AUTOMÁTICAMENTE agrega faltantes de caja si aplica.
    """
    # 1. Determinar el Objeto Base y Periodo
    try:
        # Intenta cargar liquidación existente (Recalcular)
        liquidacion_existente = Remuneracion.objects.select_related('trabajador', 'trabajador__afp', 'trabajador__salud').get(id=id)
        trabajador = liquidacion_existente.trabajador
        periodo_actual = liquidacion_existente.periodo
        
    except Remuneracion.DoesNotExist:
        # Nuevo cálculo (ID es de Trabajador)
        trabajador = get_object_or_404(Trabajador.objects.select_related('afp', 'salud'), id=id)
        liquidacion_existente = None
        
        # --- Recuperar fecha desde URL o usar hoy ---
        periodo_get = request.GET.get('periodo')
        if periodo_get:
            periodo_actual = periodo_get
        else:
            periodo_actual = date.today().strftime('%Y-%m')

    p = get_parametros_calculo()
    
    # 3. Lógica POST: Calcular y Guardar
    if request.method == 'POST':
        
        dias_trabajados = int(request.POST.get('dias') or 30)
        horas_extras = float(request.POST.get('horas_extras') or 0)
        anticipo_fijo = clean_currency(request.POST.get('anticipo', 0))
        
        # --- NUEVO: ABONO A FALTANTE (TABLA 6) ---
        abono_faltante = clean_currency(request.POST.get('abono_faltante', 0))
        
        # Procesamiento de Listas Dinámicas
        json_haberes = request.POST.get('detalle_haberes', '[]')
        try:
            lista_haberes = json.loads(json_haberes)
            total_haberes_imponibles = sum(int(b.get('monto', 0) or 0) for b in lista_haberes)
        except:
            lista_haberes = []
            total_haberes_imponibles = 0

        json_asignaciones = request.POST.get('detalle_asignaciones', '[]')
        try:
            lista_asignaciones = json.loads(json_asignaciones)
            total_asignaciones_manuales = sum(int(b.get('monto', 0) or 0) for b in lista_asignaciones)
        except:
            lista_asignaciones = []
            total_asignaciones_manuales = 0

        json_bonos = request.POST.get('detalle_bonos', '[]')
        try:
            lista_bonos = json.loads(json_bonos)
            total_no_imponibles = sum(int(b.get('monto', 0) or 0) for b in lista_bonos)
        except:
            lista_bonos = []
            total_no_imponibles = 0

        json_descuentos = request.POST.get('detalle_descuentos', '[]')
        try:
            lista_descuentos = json.loads(json_descuentos)
            total_otros_descuentos = sum(int(b.get('monto', 0) or 0) for b in lista_descuentos)
        except:
            lista_descuentos = []
            total_otros_descuentos = 0
        
        # --- CÁLCULOS MATEMÁTICOS ---
        
        # A. Base Imponible Parcial (Para calcular Gratificación)
        sueldo_base_dia = Decimal(trabajador.sueldo_base) / Decimal(30)
        sueldo_base_prop = (sueldo_base_dia * Decimal(dias_trabajados)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        valor_hora_extra = Decimal(trabajador.valor_hora_extra)
        monto_horas_extras = (Decimal(horas_extras) * valor_hora_extra).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        
        base_pre_gratificacion = sueldo_base_prop + monto_horas_extras + Decimal(total_haberes_imponibles)
        
        # B. Gratificación Legal
        gratificacion_bruta = (base_pre_gratificacion * p['gratificacion_pct']).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        
        # C. SUELDO IMPONIBLE FINAL (Base para Descuentos Legales)
        sueldo_imponible = base_pre_gratificacion + gratificacion_bruta
        
        # Tope Imponible
        base_calculo_descuentos = min(sueldo_imponible, p['tope_imponible'])
        
        # D. Descuentos Legales
        monto_afp = (base_calculo_descuentos * Decimal(trabajador.afp.tasa) / Decimal(100)).quantize(Decimal('1'), rounding=ROUND_HALF_UP) if trabajador.afp else Decimal('0')
        monto_salud = (base_calculo_descuentos * Decimal(trabajador.salud.tasa) / Decimal(100)).quantize(Decimal('1'), rounding=ROUND_HALF_UP) if trabajador.salud else Decimal('0')
        
        # Lógica Seguro Cesantía (Exención 11 años)
        tasa_cesantia_aplicada = p['seguro_cesantia_pct']
        cumplio_11_anos = False
        if trabajador.fecha_ingreso:
            hoy = date.today()
            antiguedad_anos = hoy.year - trabajador.fecha_ingreso.year - ((hoy.month, hoy.day) < (trabajador.fecha_ingreso.month, trabajador.fecha_ingreso.day))
            if antiguedad_anos >= 11:
                tasa_cesantia_aplicada = Decimal('0')
                cumplio_11_anos = True

        monto_seguro_cesantia = (base_calculo_descuentos * tasa_cesantia_aplicada).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        
        # E. Asignación Familiar CON DETALLE DE TRAMO
        monto_asignacion_automatica = Decimal('0')
        tramo_letra_aplicado = None
        tramo_monto_unitario = 0

        if trabajador.tiene_asignacion_familiar and trabajador.cargas_familiares > 0:
            for tramo in p['tramos_af']:
                if sueldo_imponible <= Decimal(tramo.ingreso_tope):
                    # Guardamos el detalle para mostrarlo en el PDF
                    tramo_letra_aplicado = tramo.tramo
                    tramo_monto_unitario = tramo.monto_por_carga
                    
                    monto_asignacion_automatica = Decimal(tramo.monto_por_carga) * Decimal(trabajador.cargas_familiares)
                    break
        
        monto_asignacion_familiar_total = monto_asignacion_automatica + Decimal(total_asignaciones_manuales)

        # --- IMPUESTO ÚNICO ---
        afecto_impuesto = sueldo_imponible - (monto_afp + monto_salud + monto_seguro_cesantia)
        if afecto_impuesto > 0:
            impuesto_determinado = afecto_impuesto * Decimal('0.04')
            rebaja_impuesto = Decimal('37218.42')
            monto_impuesto_final = max(Decimal('0'), impuesto_determinado - rebaja_impuesto)
            monto_impuesto_final = monto_impuesto_final.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        else:
            monto_impuesto_final = Decimal('0')

        # --- FALTANTE DE CAJA (Con lógica de Abono) ---
        monto_faltante_automatico = Decimal('0')
        if trabajador.filtro_trabajador:
            try:
                anio_liq, mes_liq = map(int, periodo_actual.split('-'))
                balance_mes = RendicionDiaria.objects.filter(
                    trabajador=trabajador,
                    fecha__year=anio_liq,
                    fecha__month=mes_liq
                ).aggregate(Sum('diferencia'))['diferencia__sum'] or 0
                
                # Si el balance es negativo, hay faltante. Si es positivo, es saldo a favor (sobrante)
                if balance_mes < 0:
                    monto_faltante_automatico = Decimal(abs(balance_mes))
            except:
                pass
        
        # Aplicar el abono (resta)
        # La fórmula es: Faltante Final = Max(0, FaltanteAuto - Abono)
        monto_faltante_final = max(Decimal(0), monto_faltante_automatico - Decimal(abono_faltante))
        monto_faltante_final = monto_faltante_final.quantize(Decimal('1'), rounding=ROUND_HALF_UP)


        # F. Total de Haberes
        total_haberes = sueldo_imponible + monto_asignacion_familiar_total + Decimal(total_no_imponibles)
        
        # G. Total Descuentos
        total_descuentos_legales = monto_afp + monto_salud + monto_seguro_cesantia + monto_impuesto_final
        total_descuentos = total_descuentos_legales + Decimal(anticipo_fijo) + Decimal(total_otros_descuentos) + monto_faltante_final
        
        # H. Sueldo Líquido
        sueldo_liquido = total_haberes - total_descuentos
        
        detalle_calculo = {
            'sueldo_base_original': str(trabajador.sueldo_base),
            'sueldo_base_proporcional': str(sueldo_base_prop),
            'dias_trabajados': dias_trabajados,
            'horas_extras': horas_extras,
            'monto_horas_extras': str(monto_horas_extras),
            'lista_haberes': lista_haberes,
            'lista_asignaciones': lista_asignaciones,
            'lista_bonos': lista_bonos,
            'lista_descuentos': lista_descuentos,
            'monto_anticipo': str(anticipo_fijo),
            
            # --- DATOS FALTANTE ---
            'faltante_automatico_original': str(monto_faltante_automatico), # Para mostrar que venía de la caja
            'abono_faltante': str(abono_faltante), # Lo que ingresó el usuario
            
            # Totales Parciales
            'monto_otros_haberes_total': str(Decimal(total_no_imponibles)),
            
            'asignacion_familiar': str(monto_asignacion_automatica),
            'monto_asignaciones_total': str(monto_asignacion_familiar_total),
            
            'monto_otros_descuentos_total': str(Decimal(total_otros_descuentos)),

            'sueldo_imponible': str(sueldo_imponible), 
            'gratificacion': str(gratificacion_bruta),
            'afp_nombre': trabajador.afp.nombre if trabajador.afp else 'N/A',
            'afp_tasa': float(trabajador.afp.tasa) if trabajador.afp else 0.0,
            'monto_afp': str(monto_afp),
            'salud_nombre': trabajador.salud.nombre if trabajador.salud else 'N/A',
            'salud_tasa': float(trabajador.salud.tasa) if trabajador.salud else 0.0,
            'monto_salud': str(monto_salud),
            'monto_seguro_cesantia': str(monto_seguro_cesantia),
            'cumplio_11_anos': cumplio_11_anos,

            'tramo_letra': tramo_letra_aplicado,
            'tramo_monto_unitario': str(tramo_monto_unitario),

            'monto_impuesto': str(monto_impuesto_final),
            'afecto_impuesto': str(afecto_impuesto),
            'impuesto_determinado': str(impuesto_determinado if afecto_impuesto > 0 else 0),
            
            # Faltante Final
            'monto_faltante': str(monto_faltante_final),

            'total_haberes_calculado': str(total_haberes),
            'total_descuentos_calculado': str(total_descuentos),
            'periodo': periodo_actual,
            'rut': trabajador.rut
        }
        
        defaults = {
            'sueldo_liquido': int(sueldo_liquido),
            'total_haberes': int(total_haberes),
            'total_descuentos': int(total_descuentos),
            'monto_impuesto': int(monto_impuesto_final),
            'monto_faltante': int(monto_faltante_final),
            'detalle_json': detalle_calculo
        }
        
        if liquidacion_existente:
            for key, value in defaults.items():
                setattr(liquidacion_existente, key, value)
            liquidacion_existente.save()
            id_final = liquidacion_existente.id
        else:
            nueva = Remuneracion.objects.create(trabajador=trabajador, periodo=periodo_actual, **defaults)
            id_final = nueva.id
        
        return redirect('ver_liquidacion', id=id_final)
        
    # 4. LÓGICA GET: Cargar datos para el formulario
    
    # Valores por defecto
    initial_dias = 30
    initial_horas = 0
    initial_anticipo = 0
    
    # Faltantes por defecto
    initial_faltante_auto = 0
    initial_abono_faltante = 0

    l_haberes = []
    l_asignaciones = []
    l_bonos = []
    l_descuentos = []

    if liquidacion_existente:
        detalle = liquidacion_existente.detalle_json
        initial_dias = detalle.get('dias_trabajados', 30)
        initial_horas = detalle.get('horas_extras', 0)
        try: initial_anticipo = int(float(detalle.get('monto_anticipo', 0)))
        except: initial_anticipo = 0
        
        # Recuperar datos de faltante guardados
        try: initial_faltante_auto = int(float(detalle.get('faltante_automatico_original', 0)))
        except: initial_faltante_auto = 0
        
        try: initial_abono_faltante = int(float(detalle.get('abono_faltante', 0)))
        except: initial_abono_faltante = 0

        l_haberes = detalle.get('lista_haberes', [])
        l_asignaciones = detalle.get('lista_asignaciones', [])
        l_bonos = detalle.get('lista_bonos', [])
        l_descuentos = detalle.get('lista_descuentos', [])
        
        if not l_bonos and detalle.get('monto_bonos'):
             try:
                 val = int(float(detalle.get('monto_bonos')))
                 if val > 0: l_bonos = [{'desc': 'Bono General', 'monto': val}]
             except: pass
    
    else:
        # Si es nueva liquidación, calculamos el faltante automático en tiempo real
        if trabajador.filtro_trabajador:
            try:
                anio_liq, mes_liq = map(int, periodo_actual.split('-'))
                balance_mes = RendicionDiaria.objects.filter(
                    trabajador=trabajador,
                    fecha__year=anio_liq,
                    fecha__month=mes_liq
                ).aggregate(Sum('diferencia'))['diferencia__sum'] or 0
                
                if balance_mes < 0:
                    initial_faltante_auto = abs(balance_mes)
            except:
                initial_faltante_auto = 0

    initial_data = {
        'dias': initial_dias,
        'horas_extras': initial_horas,
        'anticipo': initial_anticipo,
        'abono_faltante': initial_abono_faltante, # Para rellenar el input
        'json_haberes': json.dumps(l_haberes),
        'json_asignaciones': json.dumps(l_asignaciones),
        'json_bonos': json.dumps(l_bonos),
        'json_descuentos': json.dumps(l_descuentos),
    }

    context = {
        'trabajador': trabajador,
        'periodo_str': date(int(periodo_actual[:4]), int(periodo_actual[5:]), 1).strftime('%B %Y').upper(),
        'periodo_mes_nombre': date(int(periodo_actual[:4]), int(periodo_actual[5:]), 1).strftime('%B'),
        'initial': initial_data,
        'faltante_automatico': initial_faltante_auto # Dato de solo lectura
    }
    
    return render(request, 'gestion/remuneraciones/formulario_calculo.html', context)

def ver_liquidacion(request, id):
    """
    Muestra el detalle de una liquidación calculada o guardada.
    """
    liquidacion = get_object_or_404(Remuneracion.objects.select_related('trabajador'), id=id)
    detalle = liquidacion.detalle_json
    
    detalle_formateado = {}
    for key, value in detalle.items():
        # Excepciones que deben mantenerse como float (Tasas y Horas)
        if key in ['afp_tasa', 'salud_tasa', 'horas_extras']:
            try:
                detalle_formateado[key] = float(value)
            except (ValueError, TypeError):
                detalle_formateado[key] = 0.0
        else:
            # El resto (Montos) tratamos de pasarlos a int para quitar .0
            try:
                detalle_formateado[key] = int(float(value))
            except (ValueError, TypeError):
                detalle_formateado[key] = value

    # --- CORRECCIÓN RUT ---
    # Limpiamos puntos y guiones para obtener cuerpo puro y formatear correctamente
    rut_raw = liquidacion.trabajador.rut
    rut_formateado = rut_raw
    
    if rut_raw and len(rut_raw) > 1:
        # 1. Quitamos cualquier formato existente
        rut_limpio = rut_raw.replace('.', '').replace('-', '').strip()
        
        if len(rut_limpio) > 1:
            cuerpo = rut_limpio[:-1]
            dv = rut_limpio[-1].upper()
            try:
                # Intentamos formatear con miles
                cuerpo_fmt = "{:,}".format(int(cuerpo)).replace(',', '.')
                rut_formateado = f"{cuerpo_fmt}-{dv}"
            except ValueError:
                # Si falla (ej: tiene letras raras), mostramos el original limpio
                rut_formateado = rut_raw

    # Lógica de Bodega (Facturación vs Asignada)
    bodega_mostrar = liquidacion.trabajador.bodega_asignada
    if bodega_mostrar == 'Ambos':
        bodega_mostrar = liquidacion.trabajador.bodega_facturacion
    
    # Nombre legible de bodega
    nombre_bodega = "Desconocida"
    if bodega_mostrar == '1221': nombre_bodega = "Bodega 1221 (Manuel Peñafiel)"
    elif bodega_mostrar == '1225': nombre_bodega = "Bodega 1225 (David Perry)"

    context = {
        'liquidacion': liquidacion,
        't': liquidacion.trabajador,
        'rut_fmt': rut_formateado,
        'bodega_real': nombre_bodega,
        'detalle': detalle_formateado,
        'total_haberes_brutos': liquidacion.total_haberes,
        'periodo_str': date(int(detalle_formateado['periodo'][:4]), int(detalle_formateado['periodo'][5:]), 1).strftime('%B %Y').upper(),
    }
    return render(request, 'gestion/remuneraciones/liquidacion_detalle.html', context)

def vista_excel_simulacion(request, id):
    """
    Vista que muestra la pantalla intermedia para simular la exportación a Excel.
    """
    liquidacion = get_object_or_404(Remuneracion, id=id)
    return render(request, 'gestion/remuneraciones/remuneracion_excel.html', {'liquidacion': liquidacion})