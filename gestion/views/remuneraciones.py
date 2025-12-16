import re
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from gestion.models import AfpConfig, SaludConfig, AsignacionFamiliarConfig, ConfiguracionGlobal, Trabajador, Remuneracion 
from django.db import IntegrityError
from datetime import date, timedelta
import json
from decimal import Decimal, ROUND_HALF_UP

# --- VISTAS DE NAVEGACIÓN ---

def menu_remuneraciones(request):
    """
    Vista que renderiza el menú principal de remuneraciones.
    (Ruta: 'menu_remuneraciones')
    """
    return render(request, 'gestion/remuneraciones/menu_remuneraciones.html')

def nomina_mensual(request):
    """
    Muestra la nómina de sueldos (tabla principal).
    (Ruta: 'nomina_mensual')
    """
    # Lógica pendiente: Cargar lista de trabajadores y su estado
    trabajadores = Trabajador.objects.all()
    
    # Aquí puedes agregar lógica para verificar si la liquidación del mes ya existe
    
    return render(request, 'gestion/remuneraciones/nomina_mensual.html', {'trabajadores': trabajadores})

# En gestion/views/remuneraciones.py

def historial(request):
    """
    Muestra el historial de liquidaciones.
    (Ruta: 'historial_remuneraciones')
    """
    
    # 1. Obtener todas las liquidaciones guardadas, ordenadas por periodo
    # Usamos select_related para obtener el nombre del trabajador sin consultas extra
    liquidaciones_historicas = Remuneracion.objects.all().select_related('trabajador').order_by('-periodo')
    
    context = {
        'liquidaciones': liquidaciones_historicas
    }
    
    # Lógica pendiente: Cargar datos históricos
    return render(request, 'gestion/remuneraciones/historial.html', context)

def calcular_sueldo(request):
    """
    Muestra el formulario para ingresar variables de cálculo (Horas Extras, Anticipo).
    (Ruta: 'calcular_sueldo')
    """
    # Lógica pendiente: Cargar trabajador específico
    return render(request, 'gestion/remuneraciones/formulario_calculo.html', {})

def ver_liquidacion(request):
    """
    Muestra el detalle de una liquidación calculada o guardada.
    (Ruta: 'ver_liquidacion')
    """
    # Lógica pendiente: Cargar detalles del JSON de Remuneracion
    # Por ahora solo muestra la plantilla estática
    return render(request, 'gestion/remuneraciones/liquidacion_detalle.html', {})

# Coloca esta función ANTES de la función 'parametros'

def format_currency_cl(value, decimal_places=0):
    """
    Formatea un número a string con punto de miles y coma decimal.
    Ej: 460000 -> 460.000
    Ej: 36500.00 -> 36.500,00
    """
    if value is None: return ""
    try:
        # Usa el formato estándar de Python y luego reemplaza los separadores
        if decimal_places == 0:
            # Para enteros: 460000 -> 460.000
            formatted = f"{int(value):,}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
        else:
            # Para decimales: 36500.00 -> 36.500,00
            formatted = f"{value:,.{decimal_places}f}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
        return formatted
    except (ValueError, TypeError):
        return str(value)

# ... (Luego sigue la función 'parametros') ...

def parametros(request):
    """
    Vista que carga y muestra la configuración (AFP, Salud, Tramos)
    """
    
    afps = AfpConfig.objects.all()
    salud = SaludConfig.objects.all()
    tramos = AsignacionFamiliarConfig.objects.all().order_by('ingreso_tope')
    
    config_global_qs = ConfiguracionGlobal.objects.all()
    config_raw = {c.clave: c.valor for c in config_global_qs}

    # 🚨 NUEVA LÓGICA: Comprobar si la base de datos está vacía 🚨
    db_vacia = not afps.exists() or not salud.exists() or not tramos.exists()

    config_formato = {
        # ... (lógica de formato existente) ...
        'sueldo_minimo': format_currency_cl(config_raw.get('sueldo_minimo')),
        'valor_uf': format_currency_cl(config_raw.get('valor_uf'), 2),
        'valor_utm': format_currency_cl(config_raw.get('valor_utm')),
        'gratificacion_legal_pct': int(config_raw.get('gratificacion_legal_pct', 0)),
    }

    context = {
        'afps': afps,
        'salud': salud,
        'tramos': tramos,
        'config': config_formato,
        'db_vacia': db_vacia, # <-- Agregamos esta variable
    }
    
    return render(request, 'gestion/remuneraciones/parametros.html', context)

# --- VISTA DE INICIALIZACIÓN (Paso Anterior) ---

def inicializar_parametros_remuneraciones(request):
    """
    Función de una sola vez para poblar los datos iniciales de AFP, Salud y Tramos.
    (Ruta: 'inicializar_parametros')
    """
    
    # Datos extraídos de database.py
    afps_default = [("Capital", 11.44), ("Cuprum", 11.44), ("Habitat", 11.27), ("Modelo", 10.58), ("Planvital", 11.16), ("Provida", 11.45), ("Uno", 10.69)]
    salud_default = [("Fonasa", 7.0), ("Isapre", 7.0)]
    asignacion_default = [
        ("A", 620251, 22007),
        ("B", 905941, 13505),
        ("C", 1412957, 4267),
        ("D", 999999999, 0) 
    ]
    config_default = [
        ("gratificacion_legal_pct", 25.0, "Porcentaje de Gratificación Legal"),
        ("seguro_cesantia_pct", 0.6, "Porcentaje Seguro de Cesantía (trabajador)"),
    ]

    try:
        # Insertar AFPs
        for nombre, tasa in afps_default:
            AfpConfig.objects.get_or_create(nombre=nombre, defaults={'tasa': tasa})
        
        # Insertar Salud
        for nombre, tasa in salud_default:
            SaludConfig.objects.get_or_create(nombre=nombre, defaults={'tasa': tasa})

        # Insertar Tramos de Asignación Familiar
        for tramo, tope, monto in asignacion_default:
             AsignacionFamiliarConfig.objects.get_or_create(tramo=tramo, defaults={'ingreso_tope': tope, 'monto_por_carga': monto})

        # Insertar Configuración Global (Solo si no existe Sueldo Mínimo, etc.)
        ConfiguracionGlobal.objects.get_or_create(clave='sueldo_minimo', defaults={'valor': 460000, 'descripcion': 'Sueldo Mínimo Mensual'})
        ConfiguracionGlobal.objects.get_or_create(clave='valor_uf', defaults={'valor': 36500, 'descripcion': 'Valor UF Previsional'})
        ConfiguracionGlobal.objects.get_or_create(clave='valor_utm', defaults={'valor': 63450, 'descripcion': 'Valor UTM'})

        for clave, valor, descripcion in config_default:
            ConfiguracionGlobal.objects.get_or_create(clave=clave, defaults={'valor': valor, 'descripcion': descripcion})

        # Redirigir al menú principal de parámetros
        return redirect('parametros_remuneraciones')

    except IntegrityError:
        # Si ya existe, simplemente redirige.
        return redirect('parametros_remuneraciones')
    
def clean_currency(value):
    """Limpia cadenas de texto de símbolos de moneda, puntos de miles y comas para convertir a float."""
    if isinstance(value, str):
        # Elimina $, puntos de miles y reemplaza la coma por punto decimal (si se usa)
        value = value.replace('$', '').replace('.', '').replace(',', '.')
        try:
            return float(value)
        except ValueError:
            return 0.0
    return float(value) if value is not None else 0.0


def guardar_indicadores(request):
    """
    Recibe los datos del formulario de Indicadores Económicos y actualiza
    los valores en el modelo ConfiguracionGlobal.
    """
    if request.method == 'POST':
        
        # Diccionario que mapea el nombre del campo del formulario a su tipo de limpieza
        keys_to_update = {
            'sueldo_minimo': 'currency',
            'valor_uf': 'currency',
            'valor_utm': 'currency',
            'gratificacion_legal_pct': 'float' # Este ya viene limpio (number input)
        }
        
        for key, value_type in keys_to_update.items():
            if key in request.POST:
                raw_value = request.POST.get(key)
                
                # Limpiar valor según el tipo de campo
                if value_type == 'currency':
                    clean_value = clean_currency(raw_value)
                else: 
                    try:
                        clean_value = float(raw_value)
                    except ValueError:
                        clean_value = 0.0

                try:
                    # Busca el objeto por clave (ej: 'sueldo_minimo') y lo actualiza
                    config = ConfiguracionGlobal.objects.get(clave=key)
                    config.valor = clean_value
                    config.save()
                    
                except ConfiguracionGlobal.DoesNotExist:
                    # En un caso extremo, si el indicador fue borrado, lo recreamos
                    pass 
                except Exception:
                    pass
        
        # Redirigir a la misma página para ver los cambios actualizados
        return redirect('parametros_remuneraciones')
        
    return redirect('parametros_remuneraciones')
# En tu archivo remuneraciones.py, agrega esta función de utilidad:

def format_currency_cl(value, decimal_places=0):
    """
    Formatea un número a string con punto de miles y coma decimal.
    Ej: 460000 -> 460.000
    Ej: 36500.00 -> 36.500,00
    """
    if value is None: return ""
    try:
        # Usa el formato estándar de Python y luego reemplaza los separadores
        if decimal_places == 0:
            formatted = f"{int(value):,}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
        else:
            formatted = f"{value:,.{decimal_places}f}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
        return formatted
    except (ValueError, TypeError):
        return str(value)
    
def editar_tasa_previsional(request, modelo, nombre):
    # 1. Determinar el Modelo a usar (AFP o Salud)
    if modelo == 'afp':
        Model = AfpConfig
    elif modelo == 'salud':
        Model = SaludConfig
    else:
        return redirect('parametros_remuneraciones')

    # 2. Obtener la instancia
    instance = get_object_or_404(Model, nombre=nombre)

    if request.method == 'POST':
        try:
            # 3. Guardar los cambios (Añadimos limpieza de coma a punto)
            nueva_tasa_str = request.POST.get('tasa', '0').replace(',', '.')
            instance.tasa = float(nueva_tasa_str)
            instance.save()
            
            return redirect('parametros_remuneraciones')
        except ValueError:
            # Si falla, simplemente recarga (podrías agregar mensajes de error después)
            pass 
            
    context = {
        'modelo': modelo,
        'nombre': nombre,
        'tasa_actual': instance.tasa,
    }
    
    return render(request, 'gestion/remuneraciones/editar_tasa.html', context)

def editar_tramos_asignacion(request):
    """
    Vista que permite al usuario editar los 4 tramos de Asignación Familiar simultáneamente.
    """
    
    # Cargar todos los tramos ordenados
    tramos_qs = AsignacionFamiliarConfig.objects.all().order_by('tramo')
    
    if request.method == 'POST':
        try:
            # Iterar sobre los 4 tramos y actualizar sus valores
            for tramo in tramos_qs:
                # Los nombres de los campos serán dinámicos: 'tope_A', 'monto_A', 'tope_B', 'monto_B', etc.
                
                # 1. Obtener y limpiar Renta Tope
                tope_raw = request.POST.get(f'tope_{tramo.tramo}', '0')
                tope_limpio = clean_currency(tope_raw)
                
                # 2. Obtener y limpiar Monto por Carga
                monto_raw = request.POST.get(f'monto_{tramo.tramo}', '0')
                monto_limpio = clean_currency(monto_raw)
                
                # 3. Actualizar y guardar
                tramo.ingreso_tope = int(tope_limpio)
                tramo.monto_por_carga = int(monto_limpio)
                tramo.save()
            
            # Redirigir de vuelta a la página principal de parámetros
            return redirect('parametros_remuneraciones')
            
        except Exception:
            # messages.error(request, "Error: Verifica que los valores de Renta Tope y Monto sean números válidos.")
            pass
            
    context = {
        'tramos': tramos_qs,
    }
    
    # Usaremos una plantilla simple para la edición
    return render(request, 'gestion/remuneraciones/editar_tramos.html', context)

def get_parametros_calculo():
    """Carga todos los parámetros necesarios en un solo diccionario."""
    config_raw = {c.clave: Decimal(str(c.valor)) for c in ConfiguracionGlobal.objects.all().iterator()}
    
    # Valores Imponibles y Tope (simplificado)
    # Utilizamos el valor UF como tope de referencia para simplificar
    tope_imponible_clp = config_raw.get('valor_uf', Decimal('0')) * Decimal('81.6') # 81.6 UF

    return {
        'sueldo_minimo': config_raw.get('sueldo_minimo', Decimal('0')),
        'valor_uf': config_raw.get('valor_uf', Decimal('0')),
        'valor_utm': config_raw.get('valor_utm', Decimal('0')),
        'gratificacion_pct': config_raw.get('gratificacion_legal_pct', Decimal('0')) / 100,
        'seguro_cesantia_pct': config_raw.get('seguro_cesantia_pct', Decimal('0')) / 100,
        'tope_imponible': tope_imponible_clp.quantize(Decimal('1'), rounding=ROUND_HALF_UP),
        'tramos_af': AsignacionFamiliarConfig.objects.all().order_by('ingreso_tope'),
    }

def calcular_sueldo(request, id):
    """
    Muestra el formulario para ingresar variables de cálculo, realiza el cálculo y lo guarda.
    El ID puede ser de Trabajador (si es nuevo cálculo) o de Remuneracion (si es recalcular).
    """
    
    # --- 1. Determinar el Objeto Base y Periodo ---
    try:
        # Intenta cargar el objeto Remuneracion (si viene de Recalcular)
        liquidacion_existente = Remuneracion.objects.select_related('trabajador', 'trabajador__afp', 'trabajador__salud').get(id=id)
        trabajador = liquidacion_existente.trabajador
        periodo_actual = liquidacion_existente.periodo
        
    except Remuneracion.DoesNotExist:
        # Si no existe, es un nuevo cálculo y el ID es de Trabajador
        trabajador = get_object_or_404(Trabajador.objects.select_related('afp', 'salud'), id=id)
        liquidacion_existente = None
        periodo_actual = date.today().strftime('%Y-%m') 

    # --- 2. Cargar Parámetros ---
    p = get_parametros_calculo()
    
    # --- 3. Lógica POST: Calcular y Guardar ---
    if request.method == 'POST':
        
        # Obtener entradas del formulario
        dias_trabajados = int(request.POST.get('dias', 30))
        horas_extras = float(request.POST.get('horas_extras', 0))
        bonos = clean_currency(request.POST.get('bonos', 0)) # Asumimos no imponible por formulario
        anticipo = clean_currency(request.POST.get('anticipo', 0))
        
        # --- CÁLCULOS PRINCIPALES ---
        
        # 1. Sueldo Base Proporcional y Haberes Imponibles
        sueldo_base_dia = Decimal(trabajador.sueldo_base) / Decimal(30)
        sueldo_base_prop = (sueldo_base_dia * Decimal(dias_trabajados)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        
        valor_hora_extra = Decimal(trabajador.valor_hora_extra)
        monto_horas_extras = (Decimal(horas_extras) * valor_hora_extra).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        
        sueldo_imponible = sueldo_base_prop + monto_horas_extras
        
        # 2. Tope Imponible
        monto_imponible_final = min(sueldo_imponible, p['tope_imponible'])
        
        # 3. Gratificación Legal (25% del imponible)
        gratificacion_bruta = (sueldo_imponible * p['gratificacion_pct']).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        
        # 4. Total Haberes
        total_haberes = sueldo_imponible + gratificacion_bruta + Decimal(bonos)
        
        # 5. Descuentos Previsionales (AFP, Salud, Seguro Cesantía)
        monto_afp = (monto_imponible_final * Decimal(trabajador.afp.tasa) / Decimal(100)).quantize(Decimal('1'), rounding=ROUND_HALF_UP) if trabajador.afp else Decimal('0')
        monto_salud = (monto_imponible_final * Decimal(trabajador.salud.tasa) / Decimal(100)).quantize(Decimal('1'), rounding=ROUND_HALF_UP) if trabajador.salud else Decimal('0')
        monto_seguro_cesantia = (monto_imponible_final * p['seguro_cesantia_pct']).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        
        # 6. Asignación Familiar (Haber Adicional, No Imponible)
        monto_asignacion_familiar = Decimal('0')
        if trabajador.tiene_asignacion_familiar and trabajador.cargas_familiares > 0:
            for tramo in p['tramos_af']:
                if sueldo_imponible <= Decimal(tramo.ingreso_tope):
                    monto_asignacion_familiar = Decimal(tramo.monto_por_carga) * Decimal(trabajador.cargas_familiares)
                    break

        # 7. Resumen de Totales
        total_descuentos_legales = monto_afp + monto_salud + monto_seguro_cesantia
        total_descuentos_adicionales = Decimal(anticipo)
        total_descuentos = total_descuentos_legales + total_descuentos_adicionales
        
        sueldo_liquido = total_haberes + monto_asignacion_familiar - total_descuentos
        
        # --- Guardar Liquidación (Remuneracion) ---
        detalle_calculo = {
            'sueldo_base': str(trabajador.sueldo_base),
            'dias_trabajados': dias_trabajados,
            'horas_extras': horas_extras,
            'valor_hora_extra': str(valor_hora_extra),
            'monto_horas_extras': str(monto_horas_extras),
            'monto_bonos': str(bonos),
            'monto_anticipo': str(anticipo),
            'sueldo_imponible': str(sueldo_imponible),
            'gratificacion': str(gratificacion_bruta),
            'asignacion_familiar': str(monto_asignacion_familiar),
            'afp_nombre': trabajador.afp.nombre if trabajador.afp else 'N/A',
            'afp_tasa': float(trabajador.afp.tasa) if trabajador.afp else 0.0,
            'monto_afp': str(monto_afp),
            'salud_nombre': trabajador.salud.nombre if trabajador.salud else 'N/A',
            'salud_tasa': float(trabajador.salud.tasa) if trabajador.salud else 0.0,
            'monto_salud': str(monto_salud),
            'monto_seguro_cesantia': str(monto_seguro_cesantia),
            'total_haberes_calculado': str(total_haberes),
            'total_descuentos_calculado': str(total_descuentos),
            'periodo': periodo_actual,
            'rut': trabajador.rut
        }
        
        if liquidacion_existente:
            # Actualizar
            liquidacion_existente.sueldo_liquido = int(sueldo_liquido)
            liquidacion_existente.total_haberes = int(total_haberes + monto_asignacion_familiar)
            liquidacion_existente.total_descuentos = int(total_descuentos)
            liquidacion_existente.detalle_json = detalle_calculo
            liquidacion_existente.save()
            id_final = liquidacion_existente.id
        else:
            # Crear Nuevo
            nueva_liquidacion = Remuneracion.objects.create(
                trabajador=trabajador,
                periodo=periodo_actual,
                sueldo_liquido=int(sueldo_liquido),
                total_haberes=int(total_haberes + monto_asignacion_familiar), # Incluye Asignación Familiar
                total_descuentos=int(total_descuentos),
                detalle_json=detalle_calculo
            )
            id_final = nueva_liquidacion.id
        
        # Redirigir a la vista de detalle
        return redirect('ver_liquidacion', id=id_final)
        
    # --- 4. Lógica GET: Mostrar Formulario ---
    
    # Datos de liquidación anterior para rellenar el formulario
    if liquidacion_existente:
        # Si existe, pre-cargar el formulario con los valores usados en el cálculo anterior
        detalle = liquidacion_existente.detalle_json
        initial_data = {
            'dias': detalle.get('dias_trabajados', 30),
            'horas_extras': detalle.get('horas_extras', 0),
            'bonos': int(detalle.get('monto_bonos', 0)),
            'anticipo': int(detalle.get('monto_anticipo', 0)),
        }
    else:
        # Valores por defecto para nuevo cálculo
        initial_data = {
            'dias': 30,
            'horas_extras': 0,
            'bonos': 0,
            'anticipo': 0,
        }

    context = {
        'trabajador': trabajador,
        'periodo_str': date(int(periodo_actual[:4]), int(periodo_actual[5:]), 1).strftime('%B %Y').upper(),
        'initial': initial_data
    }
    
    return render(request, 'gestion/remuneraciones/formulario_calculo.html', context)


# ----------------------------------------------------------------------
# VISTA DE DETALLE: VER LIQUIDACIÓN
# ----------------------------------------------------------------------

def ver_liquidacion(request, id):
    """
    Muestra el detalle de una liquidación calculada o guardada.
    El ID debe ser de Remuneracion.
    """
    liquidacion = get_object_or_404(Remuneracion.objects.select_related('trabajador'), id=id)
    detalle = liquidacion.detalle_json
    
    # Reconvertir los campos de Decimal a flotante (para el filtro floatformat)
    detalle_formateado = {}
    for key, value in detalle.items():
        try:
            detalle_formateado[key] = int(value)
        except ValueError:
            detalle_formateado[key] = value
    
    context = {
        'liquidacion': liquidacion,
        't': liquidacion.trabajador,
        'detalle': detalle_formateado,
        'total_haberes_brutos': liquidacion.total_haberes - int(detalle.get('asignacion_familiar', 0)),
        'periodo_str': date(int(detalle_formateado['periodo'][:4]), int(detalle_formateado['periodo'][5:]), 1).strftime('%B %Y').upper(),
    }
    # Por ahora solo muestra la plantilla estática, la ajustaremos en el siguiente paso
    return render(request, 'gestion/remuneraciones/liquidacion_detalle.html', context)