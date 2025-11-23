from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from datetime import date, datetime
import locale
from .models import Trabajador, DepositoDiario, DepositoAporte, DepositoDesglose, BODEGA_FILTRO_CHOICES, BODEGA_CHOICES
from django.db.models import Max, Q, Sum
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors

try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    pass

# --- VISTAS PROTEGIDAS CON LOGIN ---

@login_required
def home(request):
    context = {}
    # CORREGIDO: Apunta a core
    return render(request, 'gestion/core/home.html', context)

@login_required
def gestion_trabajadores(request):
    lista_trabajadores = Trabajador.objects.all().order_by('nombre')
    context = {
        'trabajadores': lista_trabajadores,
    }
    # CORREGIDO: Apunta a trabajadores
    return render(request, 'gestion/trabajadores/gestion_trabajadores.html', context)

# === VISTA DEL MENÚ (4 OPCIONES) ===
@login_required
def total_dia(request):
    """
    Esta vista renderiza EL MENÚ de selección.
    """
    # CORREGIDO: Nombre nuevo 'menu_banco.html'
    return render(request, 'gestion/caja/menu_banco.html')

# === VISTA DEL DASHBOARD CONSOLIDADO (CÁLCULOS) ===
@login_required
def resumen_consolidado(request):
    """
    Esta vista realiza los cálculos y muestra el 'Total Día' (Dashboard).
    """
    fecha_str_seleccionada = request.GET.get('fecha_seleccionada')
    if fecha_str_seleccionada:
        try:
            fecha_seleccionada = date.fromisoformat(fecha_str_seleccionada)
        except ValueError:
            fecha_seleccionada = date.today()
    else:
        fecha_seleccionada = date.today()

    # --- Lógica de Totales por Bodega ---
    totales_bodega = DepositoDiario.objects.filter(
        fecha=fecha_seleccionada
    ).values(
        'bodega_nombre'
    ).annotate(
        total_aportes=Sum('total_aportes'),
        total_desglose=Sum('total_desglose'),
        total_cheques=Sum('total_cheques'),
        total_diferencia=Sum('diferencia')
    ).order_by('bodega_nombre')

    datos_mp = {'aportes': 0, 'desglose_efectivo': 0, 'cheques': 0, 'desglose_total': 0, 'diferencia': 0}
    datos_dp = {'aportes': 0, 'desglose_efectivo': 0, 'cheques': 0, 'desglose_total': 0, 'diferencia': 0}

    for data in totales_bodega:
        total_general_desglose = (data['total_desglose'] or 0) + (data['total_cheques'] or 0)
        
        info = {
            'aportes': data['total_aportes'] or 0,
            'desglose_efectivo': data['total_desglose'] or 0,
            'cheques': data['total_cheques'] or 0,
            'desglose_total': total_general_desglose,
            'diferencia': data['total_diferencia'] or 0
        }

        if data['bodega_nombre'] == 'Manuel Peñafiel':
            datos_mp = info
        elif 'David' in data['bodega_nombre']:
            datos_dp = info

    total_consolidado_data = {
        'aportes': datos_mp['aportes'] + datos_dp['aportes'],
        'desglose_total': datos_mp['desglose_total'] + datos_dp['desglose_total'],
        'diferencia': datos_mp['diferencia'] + datos_dp['diferencia']
    }

    # --- Listas de Trabajadores ---
    aportes_mp_list = DepositoAporte.objects.filter(
        deposito__fecha=fecha_seleccionada,
        deposito__bodega_nombre='Manuel Peñafiel'
    ).values('trabajador__nombre').annotate(total=Sum('monto')).order_by('trabajador__nombre')

    aportes_dp_list = DepositoAporte.objects.filter(
        deposito__fecha=fecha_seleccionada,
        deposito__bodega_nombre='David Perry'
    ).values('trabajador__nombre').annotate(total=Sum('monto')).order_by('trabajador__nombre')

    # --- Desglose Billetes ---
    desglose_query = DepositoDesglose.objects.filter(
        deposito__fecha=fecha_seleccionada
    ).values('valor_unitario').annotate(
        cantidad_total=Sum('cantidad'),
        monto_total=Sum('total_denominacion')
    ).order_by('-valor_unitario')

    denominaciones_std = [20000, 10000, 5000, 2000, 1000, 500, 100, 50, 10]
    desglose_final = []
    mapa_desglose = {d['valor_unitario']: d for d in desglose_query}

    for valor in denominaciones_std:
        data = mapa_desglose.get(valor, {'cantidad_total': 0, 'monto_total': 0})
        desglose_final.append({
            'texto': f"${valor:,}".replace(",", "."),
            'cantidad': data['cantidad_total'],
            'total': data['monto_total']
        })

    total_cheques_dia = datos_mp['cheques'] + datos_dp['cheques']

    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    dia_sem = dias_semana[fecha_seleccionada.weekday()]
    mes_nom = meses[fecha_seleccionada.month]
    fecha_bonita = f"{dia_sem}, {fecha_seleccionada.day} de {mes_nom} de {fecha_seleccionada.year}"

    context = {
        'mp': datos_mp,
        'dp': datos_dp,
        'aportes_mp_list': aportes_mp_list,
        'aportes_dp_list': aportes_dp_list,
        'total': total_consolidado_data,
        'desglose_final': desglose_final,
        'total_cheques_dia': total_cheques_dia,
        'fecha_seleccionada_str': fecha_seleccionada.strftime('%Y-%m-%d'),
        'fecha_bonita': fecha_bonita
    }
    
    # CORREGIDO: Nombre nuevo 'banco_total_dia.html' (según tu imagen)
    return render(request, 'gestion/caja/banco_total_dia.html', context)

@login_required
def deposito_bodega(request, bodega_nombre):
    fecha_str_seleccionada = request.GET.get('fecha_seleccionada')
    
    if fecha_str_seleccionada:
        try:
            fecha_seleccionada = date.fromisoformat(fecha_str_seleccionada)
        except ValueError:
            fecha_seleccionada = date.today()
    else:
        fecha_seleccionada = date.today()
    
    lotes_del_dia = DepositoDiario.objects.filter(
        fecha=fecha_seleccionada, 
        bodega_nombre=bodega_nombre
    ).order_by('numero_lote')
    
    context = {
        'bodega_nombre': bodega_nombre,
        'lotes_del_dia': lotes_del_dia,
        'fecha_seleccionada_str': fecha_seleccionada.strftime('%Y-%m-%d'),
    }
    # CORREGIDO: Nombre nuevo 'banco_lotes.html'
    return render(request, 'gestion/caja/banco_lotes.html', context)

@login_required
def reportes_mensuales(request):
    bodegas_opciones = ["TODAS (Consolidado)"] + [choice[0] for choice in BODEGA_FILTRO_CHOICES]
    meses_opciones = [
        ("1", "Enero"), ("2", "Febrero"), ("3", "Marzo"), ("4", "Abril"),
        ("5", "Mayo"), ("6", "Junio"), ("7", "Julio"), ("8", "Agosto"),
        ("9", "Septiembre"), ("10", "Octubre"), ("11", "Noviembre"), ("12", "Diciembre")
    ]
    años_opciones = list(range(2025, date.today().year + 2))
    
    today = date.today()
    bodega_sel = request.GET.get('bodega', 'TODAS (Consolidado)')
    mes_sel = request.GET.get('mes', str(today.month))
    año_sel = request.GET.get('año', str(today.year))

    queryset = DepositoDiario.objects.filter(
        fecha__year=int(año_sel),
        fecha__month=int(mes_sel)
    )
    
    if bodega_sel != 'TODAS (Consolidado)':
        queryset = queryset.filter(bodega_nombre=bodega_sel)
        
    reporte_data = queryset.order_by('fecha', 'bodega_nombre', 'numero_lote')
    
    totales = reporte_data.aggregate(
        total_aportes=Sum('total_aportes'),
        total_desglose=Sum('total_desglose'),
        total_cheques=Sum('total_cheques'),
        total_diferencia=Sum('diferencia')
    )
    
    total_desglose_general = (totales['total_desglose'] or 0) + (totales['total_cheques'] or 0)
    total_aportes_general = (totales['total_aportes'] or 0)
    diferencia_real_total = total_aportes_general - total_desglose_general

    context = {
        'reporte_data': reporte_data,
        'total_aportes': total_aportes_general,
        'total_desglose_general': total_desglose_general,
        'diferencia_real_total': diferencia_real_total,
        'bodegas_opciones': bodegas_opciones,
        'meses_opciones': meses_opciones,
        'años_opciones': años_opciones,
        'bodega_sel': bodega_sel,
        'mes_sel': mes_sel,
        'año_sel': int(año_sel),
    }
    # CORREGIDO: Nombre nuevo 'banco_mensual.html'
    return render(request, 'gestion/caja/banco_mensual.html', context)

@login_required
def crear_nuevo_lote(request):
    if request.method == 'POST':
        bodega = request.POST.get('bodega_nombre')
        fecha_str = request.POST.get('fecha_seleccionada')
        nombre_lote = request.POST.get('nombre_lote', '')
        
        fecha_obj = date.fromisoformat(fecha_str)

        resultado = DepositoDiario.objects.filter(
            fecha=fecha_obj, 
            bodega_nombre=bodega
        ).aggregate(max_lote=Max('numero_lote'))
        
        nuevo_numero = (resultado['max_lote'] or 0) + 1
        
        DepositoDiario.objects.create(
            fecha=fecha_obj,
            bodega_nombre=bodega,
            numero_lote=nuevo_numero,
            nombre_lote=nombre_lote
        )

        url_redireccion = f"{reverse('deposito_bodega', args=[bodega])}?fecha_seleccionada={fecha_str}"
        return redirect(url_redireccion)
    
    return redirect('total_dia')

@login_required
def editar_lote(request, lote_id):
    lote = get_object_or_404(DepositoDiario, id=lote_id)
    puede_editar = not lote.cerrado

    denominaciones = [
        {"texto": "$20.000", "valor": 20000}, {"texto": "$10.000", "valor": 10000},
        {"texto": "$5.000", "valor": 5000}, {"texto": "$2.000", "valor": 2000},
        {"texto": "$1.000", "valor": 1000}, {"texto": "$500", "valor": 500},
        {"texto": "$100", "valor": 100}, {"texto": "$50", "valor": 50},
        {"texto": "$10", "valor": 10},
    ]

    if request.method == 'POST':
        accion = request.POST.get('accion')
        
        if accion == 'reabrir_lote' and request.user.is_superuser:
            lote.cerrado = False
            lote.save() 
            return redirect('editar_lote', lote_id=lote.id)

        if not puede_editar:
            return redirect('editar_lote', lote_id=lote.id)

        total_desglose_efectivo = 0
        lote.desglose.all().delete() 
        
        for d in denominaciones:
            cantidad_str = request.POST.get(f"cant_{d['valor']}")
            cantidad = int(cantidad_str) if cantidad_str else 0
            
            if cantidad > 0:
                total_denominacion = cantidad * d['valor']
                total_desglose_efectivo += total_denominacion
                
                DepositoDesglose.objects.create(
                    deposito=lote,
                    denominacion=d['texto'],
                    valor_unitario=d['valor'],
                    cantidad=cantidad,
                    total_denominacion=total_denominacion
                )
        
        cheque_str = request.POST.get('cant_cheque', '0')
        cheque_monto = int(cheque_str) if cheque_str else 0
        
        lote.total_desglose = total_desglose_efectivo
        lote.total_cheques = cheque_monto
        
        total_desglose_general = total_desglose_efectivo + cheque_monto
        lote.diferencia = lote.total_aportes - total_desglose_general
        
        if accion == 'cerrar_lote':
            lote.cerrado = True
        
        lote.save() 
        return redirect('editar_lote', lote_id=lote.id)

    aportes = lote.aportes.all().order_by('trabajador__nombre')
    desglose_guardado = {d.valor_unitario: d.cantidad for d in lote.desglose.all()}
    
    desglose_para_plantilla = []
    for d in denominaciones:
        cantidad_guardada = desglose_guardado.get(d['valor'], 0)
        desglose_para_plantilla.append({
            "texto": d['texto'],
            "valor": d['valor'],
            "cantidad": cantidad_guardada,
            "total_formateado": f"${cantidad_guardada * d['valor']:,}".replace(",", ".")
        })

    context = {
        'lote': lote,
        'aportes': aportes,
        'denominaciones': desglose_para_plantilla,
        'cheque_guardado': lote.total_cheques,
        'lote_esta_cerrado': lote.cerrado,
        'puede_editar': puede_editar
    }
    # CORREGIDO: Nombre nuevo 'banco_lotes_editor.html'
    return render(request, 'gestion/caja/banco_lotes_editor.html', context)

@login_required
def agregar_aporte(request, lote_id):
    lote = get_object_or_404(DepositoDiario, id=lote_id)
    
    if lote.cerrado:
        return redirect('editar_lote', lote_id=lote.id)
    
    if request.method == 'POST':
        trabajador_id = request.POST.get('trabajador')
        monto = request.POST.get('monto')
        descripcion = request.POST.get('descripcion', '')
        
        if not trabajador_id or not monto:
            pass 
        else:
            trabajador = get_object_or_404(Trabajador, id=trabajador_id)
            monto_int = int(monto) 

            DepositoAporte.objects.create(
                deposito=lote,
                trabajador=trabajador,
                monto=monto_int,
                descripcion=descripcion
            )
            
            lote.total_aportes += monto_int
            total_desglose_general = lote.total_desglose + lote.total_cheques
            lote.diferencia = lote.total_aportes - total_desglose_general
            lote.save()
            
            return redirect('editar_lote', lote_id=lote.id)

    if lote.bodega_nombre == 'Manuel Peñafiel':
        filtro_bodega = '1221 (Manuel Peñafiel)'
    else:
        filtro_bodega = '1225 (David Perry)'
        
    trabajadores_disponibles = Trabajador.objects.filter(
        Q(bodega_asignada=filtro_bodega) | Q(bodega_asignada='Ambos')
    ).order_by('nombre')
    
    context = {
        'lote': lote,
        'trabajadores': trabajadores_disponibles,
    }
    # Apunta a 'agregar_aporte.html' que no se renombró (Correcto)
    return render(request, 'gestion/caja/agregar_aporte.html', context)

@login_required
def quitar_aportes_seleccion(request, lote_id):
    lote = get_object_or_404(DepositoDiario, id=lote_id)
    
    if lote.cerrado:
        return redirect('editar_lote', lote_id=lote.id)

    if request.method == 'POST':
        lista_ids_aportes = request.POST.getlist('aporte_ids')
        
        if lista_ids_aportes:
            aportes_a_borrar = DepositoAporte.objects.filter(id__in=lista_ids_aportes, deposito=lote)
            total_restando = aportes_a_borrar.aggregate(total=Sum('monto'))['total'] or 0
            
            lote.total_aportes -= total_restando
            total_desglose_general = lote.total_desglose + lote.total_cheques
            lote.diferencia = lote.total_aportes - total_desglose_general
            
            lote.save()
            aportes_a_borrar.delete()

        return redirect('editar_lote', lote_id=lote.id)
    
    return redirect('total_dia')

@login_required 
def desbloquear_lote(request, lote_id):
    lote = get_object_or_404(DepositoDiario, id=lote_id)

    if not request.user.is_superuser:
        return redirect('home')
        
    lote.cerrado = False
    lote.save()
    return redirect('editar_lote', lote_id=lote.id)

@login_required
def generar_pdf_lote(request, lote_id):
    lote = get_object_or_404(DepositoDiario, id=lote_id)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="resumen_lote_{lote.id}.pdf"'
    
    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    
    y = height - (1 * inch)
    x = 1 * inch
    
    p.setFont("Helvetica-Bold", 18)
    p.drawString(x, y, "Resumen de Cierre de Lote")
    y -= 30
    
    p.setFont("Helvetica", 12)
    p.drawString(x, y, f"Bodega: {lote.bodega_nombre}")
    y -= 20
    p.drawString(x, y, f"Fecha: {lote.fecha.strftime('%d-%m-%Y')}")
    y -= 20
    p.drawString(x, y, f"Lote: {lote.nombre_lote or 'Lote ' + str(lote.numero_lote)}")
    y -= 40
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(x, y, "Detalle de Aportes")
    y -= 25
    
    p.setFont("Helvetica", 10)
    aportes = lote.aportes.all()
    for aporte in aportes:
        monto_str = f"${aporte.monto:,}".replace(",", ".")
        p.drawString(x + 10, y, f"{aporte.trabajador.nombre}: {monto_str}")
        y -= 15
    
    p.setFont("Helvetica-Bold", 12)
    p.drawString(x, y - 10, f"Total Aportes: ${lote.total_aportes:,}".replace(",", "."))
    y -= 50
    
    p.setFont("Helvetica-Bold", 14)
    p.drawString(x, y, "Resumen Final")
    y -= 25
    p.drawString(x + 10, y, f"Total Desglose: ${lote.total_desglose + lote.total_cheques:,}".replace(",", "."))
    y -= 20
    p.drawString(x + 10, y, f"DIFERENCIA: ${lote.diferencia:,}".replace(",", "."))

    p.showPage()
    p.save()
    
    return response

@login_required
def agregar_trabajador(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        bodega = request.POST.get('bodega')
        
        if nombre and bodega:
            try:
                Trabajador.objects.create(
                    nombre=nombre,
                    bodega_asignada=bodega
                )
                return redirect('gestion_trabajadores')
            except Exception as e:
                pass 
        
    context = {
        'bodega_opciones': BODEGA_CHOICES
    }
    # Apunta a carpeta trabajadores
    return render(request, 'gestion/trabajadores/agregar_trabajador.html', context)

@login_required
def editar_trabajador(request, trabajador_id):
    trabajador = get_object_or_404(Trabajador, id=trabajador_id)
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        bodega = request.POST.get('bodega')
        
        if nombre and bodega:
            try:
                trabajador.nombre = nombre
                trabajador.bodega_asignada = bodega
                trabajador.save()
                return redirect('gestion_trabajadores')
            except Exception as e:
                pass 
        
    context = {
        'bodega_opciones': BODEGA_CHOICES,
        'trabajador': trabajador,
    }
    # Apunta a carpeta trabajadores
    return render(request, 'gestion/trabajadores/editar_trabajador.html', context)

@login_required
def eliminar_trabajador(request, trabajador_id):
    if request.method == 'POST':
        trabajador = get_object_or_404(Trabajador, id=trabajador_id)
        try:
            trabajador.delete()
        except Exception as e:
            pass 
        return redirect('gestion_trabajadores')
    
    return redirect('gestion_trabajadores')

@login_required
def eliminar_lote(request, lote_id):
    if not request.user.is_superuser:
        return redirect('home')

    if request.method == 'POST':
        lote = get_object_or_404(DepositoDiario, id=lote_id)
        
        bodega_nombre = lote.bodega_nombre
        fecha_str = lote.fecha.strftime('%Y-%m-%d')
        
        lote.delete()
        
        url_redireccion = f"{reverse('deposito_bodega', args=[bodega_nombre])}?fecha_seleccionada={fecha_str}"
        return redirect(url_redireccion)
    
    return redirect('total_dia')

@login_required
def renombrar_lote(request, lote_id):
    if request.method == 'POST':
        lote = get_object_or_404(DepositoDiario, id=lote_id)
        nuevo_nombre = request.POST.get('nuevo_nombre')
        
        if not request.user.is_superuser and lote.cerrado:
            return redirect('deposito_bodega', bodega_nombre=lote.bodega_nombre)

        lote.nombre_lote = nuevo_nombre
        lote.save()
        
        return redirect('editar_lote', lote_id=lote.id)
    
    return redirect('home')