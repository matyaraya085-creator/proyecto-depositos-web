from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date, datetime
from django.db.models import Sum

# Importamos modelos
from gestion.models import ClienteCredito, FacturaCredito, Trabajador

@login_required
def menu_clientes(request):
    if request.method == 'POST':
        accion = request.POST.get('accion')

        # 1. CREAR NUEVO CLIENTE
        if accion == 'crear_cliente':
            nombre = request.POST.get('nombre')
            apodo = request.POST.get('apodo')
            if nombre:
                ClienteCredito.objects.create(nombre_razon_social=nombre, apodo=apodo)
                messages.success(request, "Cliente creado exitosamente.")
                return redirect('menu_clientes')

        # 2. EDITAR CLIENTE EXISTENTE
        elif accion == 'editar_cliente':
            cliente_id = request.POST.get('cliente_id')
            cliente = get_object_or_404(ClienteCredito, id=cliente_id)
            
            cliente.nombre_razon_social = request.POST.get('nombre')
            cliente.apodo = request.POST.get('apodo')
            cliente.save()
            
            messages.success(request, "Datos de la empresa actualizados.")
            return redirect('menu_clientes')

        # 3. ELIMINAR CLIENTE (CON VALIDACIÓN DE SUPERUSUARIO)
        elif accion == 'eliminar_cliente':
            # CAMBIO 3: Validación de seguridad en Backend
            if not request.user.is_superuser:
                messages.error(request, "⛔ Acceso denegado: Solo superusuarios pueden eliminar empresas.")
                return redirect('menu_clientes')

            cliente_id = request.POST.get('cliente_id')
            cliente = get_object_or_404(ClienteCredito, id=cliente_id)
            
            if cliente.facturas.exists():
                messages.error(request, "⚠️ No se puede eliminar: Esta empresa tiene facturas registradas.")
            else:
                cliente.delete()
                messages.success(request, "Empresa eliminada del sistema.")
            return redirect('menu_clientes')

    clientes = ClienteCredito.objects.all().order_by('-created_at')
    context = {'clientes': clientes}
    return render(request, 'gestion/clientes_credito/clientes_menu.html', context)

@login_required
def detalle_cliente(request, cliente_id):
    cliente = get_object_or_404(ClienteCredito, id=cliente_id)
    
    # FILTRO DE FECHA
    fecha_get = request.GET.get('fecha_seleccionada')
    hoy = date.today()

    if fecha_get:
        try:
            fecha_obj = datetime.strptime(fecha_get, '%Y-%m').date()
            mes = fecha_obj.month
            anio = fecha_obj.year
            fecha_seleccionada = fecha_get
        except ValueError:
            mes = hoy.month
            anio = hoy.year
            fecha_seleccionada = hoy.strftime('%Y-%m')
    else:
        mes = hoy.month
        anio = hoy.year
        fecha_seleccionada = hoy.strftime('%Y-%m')

    if request.method == 'POST':
        accion = request.POST.get('accion')

        # CASO A: CREAR NUEVA FACTURA
        if accion == 'crear_registro':
            fecha_pago = request.POST.get('fecha_pago')
            numero = request.POST.get('numero_factura')
            valor_str = request.POST.get('valor') 
            valor = int(valor_str) if valor_str else 0
            
            fletero_id = request.POST.get('fletero')
            fletero = Trabajador.objects.get(id=fletero_id) if fletero_id else None

            es_pagado = request.POST.get('es_pagado') == 'on'
            
            fecha_real_pago = request.POST.get('fecha_real_pago')
            nota_pago = request.POST.get('nota_pago') 

            if es_pagado and not fecha_real_pago:
                fecha_real_pago = date.today() 

            if fecha_pago:
                FacturaCredito.objects.create(
                    cliente=cliente,
                    numero_factura=numero,
                    valor=valor,
                    fletero=fletero,
                    fecha_pago=fecha_pago,
                    fecha_real_pago=fecha_real_pago if es_pagado else None,
                    pagado=es_pagado,
                    nota_pago=nota_pago if es_pagado else ''
                )
                messages.success(request, "Factura registrada.")
                return redirect(f"{request.path}?fecha_seleccionada={fecha_seleccionada}")

        # CASO B: EDITAR REGISTRO
        elif accion == 'editar_registro':
            factura_id = request.POST.get('factura_id')
            factura = get_object_or_404(FacturaCredito, id=factura_id)
            
            factura.numero_factura = request.POST.get('numero_factura')
            valor_str = request.POST.get('valor')
            factura.valor = int(valor_str) if valor_str else 0
            factura.fecha_pago = request.POST.get('fecha_pago')
            
            fletero_id = request.POST.get('fletero')
            factura.fletero = Trabajador.objects.get(id=fletero_id) if fletero_id else None

            factura.pagado = request.POST.get('es_pagado') == 'on'
            
            # Lógica Pago
            fecha_real = request.POST.get('fecha_real_pago')
            nota_pago = request.POST.get('nota_pago') 

            if factura.pagado:
                if fecha_real:
                    factura.fecha_real_pago = fecha_real
                elif not factura.fecha_real_pago:
                    factura.fecha_real_pago = date.today()
                
                if nota_pago is not None: 
                    factura.nota_pago = nota_pago
            else:
                factura.fecha_real_pago = None
            
            factura.save()
            messages.success(request, "Factura actualizada.")
            return redirect(f"{request.path}?fecha_seleccionada={fecha_seleccionada}")

        # CASO C: SALDAR FACTURA
        elif accion == 'saldar_factura':
            factura_id = request.POST.get('factura_id')
            factura = get_object_or_404(FacturaCredito, id=factura_id)
            
            fecha_real = request.POST.get('fecha_real_pago') or date.today()
            nota_pago = request.POST.get('nota_pago') 
            
            factura.pagado = True
            factura.fecha_real_pago = fecha_real
            if nota_pago:
                factura.nota_pago = nota_pago
            
            factura.save()
            messages.success(request, "Deuda saldada correctamente.")
            return redirect(f"{request.path}?fecha_seleccionada={fecha_seleccionada}")

        # CASO D: ELIMINAR REGISTRO
        elif accion == 'eliminar_registro':
            factura_id = request.POST.get('factura_id')
            factura = get_object_or_404(FacturaCredito, id=factura_id)
            factura.delete()
            messages.warning(request, "Factura eliminada del sistema.")
            return redirect(f"{request.path}?fecha_seleccionada={fecha_seleccionada}")

    # OBTENER DATOS
    facturas = FacturaCredito.objects.filter(
        cliente=cliente,
        fecha_pago__month=mes,
        fecha_pago__year=anio
    ).order_by('fecha_pago', 'created_at')

    deuda_total_mes = facturas.aggregate(Sum('valor'))['valor__sum'] or 0
    saldado_mes = facturas.filter(pagado=True).aggregate(Sum('valor'))['valor__sum'] or 0
    deuda_pendiente = deuda_total_mes - saldado_mes

    if deuda_total_mes == 0:
        estado_texto = "Sin Movimientos"
        estado_bg = "secondary"
    elif deuda_pendiente == 0:
        estado_texto = "Deuda Saldada"
        estado_bg = "success"
    else:
        estado_texto = "Deudor"
        estado_bg = "danger"

    fleteros = Trabajador.objects.filter(activo=True)

    context = {
        'cliente': cliente,
        'facturas': facturas,
        'fleteros': fleteros,
        'fecha_seleccionada': fecha_seleccionada,
        'deuda_total_mes': deuda_total_mes,
        'saldado_mes': saldado_mes,
        'deuda_pendiente': deuda_pendiente,
        'estado_texto': estado_texto,
        'estado_bg': estado_bg,
    }
    return render(request, 'gestion/clientes_credito/clientes_detalle.html', context)