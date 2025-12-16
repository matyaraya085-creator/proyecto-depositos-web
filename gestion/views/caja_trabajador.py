from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from gestion.models import Trabajador, RendicionDiaria 
from datetime import date
from django.db.models import Sum 
from gestion.models import Trabajador

# --- Funciones Auxiliares y Listas de Utilidad ---
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["", "ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]

def clean_currency_flow(value):
    """Función auxiliar para limpiar la entrada del formulario (ej. eliminar '$' y comas) y convertir a entero."""
    if isinstance(value, str):
        value = value.replace('$', '').replace('.', '').replace(',', '')
        try:
            return int(value)
        except ValueError:
            return 0
    return int(value) if value is not None else 0

# --- VISTAS DE NAVEGACIÓN Y FORMULARIO ---

@login_required
def menu_trabajadores(request):
    """
    Muestra la lista de trabajadores (agrupados por bodega) en lugar de las tarjetas estáticas.
    """
    # Agrupamos por bodega, excluyendo "Ambos" para el flujo de caja diario
    trabajadores_mp = Trabajador.objects.filter(bodega_asignada='Manuel Peñafiel').order_by('nombre')
    trabajadores_dp = Trabajador.objects.filter(bodega_asignada='David Perry').order_by('nombre')
    
    context = {
        'mp': {'nombre': 'Bodega 1221 (Manuel Peñafiel)', 'trabajadores': trabajadores_mp},
        'dp': {'nombre': 'Bodega 1225 (David Perry)', 'trabajadores': trabajadores_dp},
    }
    return render(request, 'gestion/caja_trabajador/menu_trabajador.html', context)

@login_required
@login_required
def form_rendicion(request, trabajador_id): # 🚨 Ahora recibe el ID
    """
    Renderiza el formulario de rendición diaria y maneja la lógica POST para guardar.
    """
    
    # --- 1. Obtener Trabajador ---
    trabajador = get_object_or_404(Trabajador, id=trabajador_id) 

    gas_types = [
        # ... (definición de gas_types) ...
    ]
    
    # --- Lógica POST: Recibir y Guardar ---
    if request.method == 'POST':
        # 🚨 Usamos el objeto trabajador obtenido del URL 🚨
        
        # 1. Obtener Valores de Rendición
        credito_empresa = clean_currency_flow(request.POST.get('credito_empresa'))
        # ... (otras variables de rendición) ...
        prepago_vales = clean_currency_flow(request.POST.get('prepago_vales'))
        transbank = clean_currency_flow(request.POST.get('transbank'))
        efectivo_entregado = clean_currency_flow(request.POST.get('efectivo'))
        venta_esperada = clean_currency_flow(request.POST.get('venta_esperada_mock', 100000)) # Mock
        
        total_rendido = credito_empresa + prepago_vales + transbank + efectivo_entregado
        balance = total_rendido - venta_esperada
        
        try:
            # Crea o actualiza el registro de Rendición Diaria para el trabajador correcto
            RendicionDiaria.objects.update_or_create(
                trabajador=trabajador, # 🚨 Usamos el objeto trabajador
                fecha=date.today(),
                defaults={
                    'credito_empresa': credito_empresa,
                    'prepago_vales': prepago_vales,
                    'transbank': transbank,
                    'efectivo_entregado': efectivo_entregado,
                    'venta_esperada': venta_esperada,
                    'balance_flujo': balance,
                    'gas_5kg_cant': clean_currency_flow(request.POST.get('cantidad_gas-5kg')),
                    'cilindros_defectuosos': clean_currency_flow(request.POST.get('cant_defectuosos')),
                }
            )
            return redirect('menu_trabajadores')

        except Exception as e:
            # Manejo de error de guardado
            pass 


    # --- Lógica GET: Mostrar Formulario ---
    context = {
        'gas_types': gas_types,
        'trabajador_ejemplo': trabajador.nombre, # 🚨 Ahora es dinámico
    }

    return render(request, 'gestion/caja_trabajador/form_rendicion.html', context)
@login_required
def reporte_mensual(request):
    """
    Vista para el reporte mensual acumulado, consultando RendicionDiaria.
    """
    
    # --- 1. Obtener filtros y Parsear Fecha ---
    trabajador_id_sel = request.GET.get('trabajador_id')
    fecha_seleccionada = request.GET.get('fecha_seleccionada', date.today().strftime('%Y-%m'))
    
    try:
        year, month = map(int, fecha_seleccionada.split('-'))
    except ValueError:
        year, month = date.today().year, date.today().month

    # 2. Obtener lista de todos los trabajadores para el filtro (dropdown)
    trabajadores = Trabajador.objects.all().order_by('nombre')
    
    # 3. Obtener el objeto del trabajador seleccionado
    trabajador_seleccionado = None
    report_data = None
    
    if trabajador_id_sel:
        try:
            trabajador_seleccionado = Trabajador.objects.get(id=trabajador_id_sel)
        except Trabajador.DoesNotExist:
            pass
    
    # --- 4. Consultar y Procesar Datos Reales ---
    if trabajador_seleccionado:
        # Consulta las rendiciones para el trabajador y el mes/año seleccionado
        rendiciones_qs = RendicionDiaria.objects.filter(
            trabajador=trabajador_seleccionado,
            fecha__year=year,
            fecha__month=month
        ).order_by('fecha')

        # 🚨 LA INDENTACIÓN COMIENZA CORRECTAMENTE AQUÍ 🚨
        if rendiciones_qs.exists(): 
            
            # Cálculo de Totales (Usando Sum de Django ORM)
            totales = rendiciones_qs.aggregate(
                total_balance=Sum('balance_flujo'),
                total_kilos_vendidos=Sum('gas_5kg_cant'), 
            )

            # --- Construir el Reporte Final (Formato para el template) ---
            
            detalle_dias = []
            for r in rendiciones_qs:
                rendicion_date = r.fecha
                balance = r.balance_flujo
                
                if balance < 0:
                    status_text = 'FALTANTE'
                    status = 'danger'
                elif balance > 0:
                    status_text = 'SOBRANTE'
                    status = 'success'
                else:
                    status_text = 'CERRADO'
                    status = 'success'
                    
                # Simulación del Total Kg: Cantidad de 5kg * 5kg/unidad
                total_kg_simulado = (r.gas_5kg_cant or 0) * 5 

                detalle_dias.append({
                    'day_num': rendicion_date.day,
                    'day_name': DIAS_SEMANA[rendicion_date.weekday()],
                    'month': MESES[rendicion_date.month],
                    'kg': total_kg_simulado,
                    'balance': balance,
                    'status': status,
                    'status_text': status_text,
                })
                
            report_data = {
                'total_kilos': (totales['total_kilos_vendidos'] or 0) * 5, 
                'balance': totales['total_balance'] or 0,
                'detalle_dias': detalle_dias,
            }


    context = {
        'trabajadores': trabajadores,
        'fecha_seleccionada': fecha_seleccionada,
        'trabajador_seleccionado': trabajador_seleccionado,
        'report_data': report_data,
    }
    return render(request, 'gestion/caja_trabajador/reporte_mensual.html', context)