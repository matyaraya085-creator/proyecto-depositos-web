from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from gestion.models import Trabajador, BODEGA_CHOICES, AfpConfig, SaludConfig
from django.db import IntegrityError

# --- GESTIÓN DE TRABAJADORES ---

@login_required
def gestion_trabajadores(request):
    """
    Vista principal con DOS TABLAS: Activos e Inactivos.
    ORDEN: Primero Internos ('I' > 'E' en desc), luego alfabético.
    """
    # Tabla Superior: Activos
    trabajadores_activos = Trabajador.objects.filter(activo=True).order_by('-tipo', 'nombre')
    
    # Tabla Inferior: Inactivos (Archivados)
    trabajadores_inactivos = Trabajador.objects.filter(activo=False).order_by('nombre')
    
    lista_afps = AfpConfig.objects.all()
    lista_salud = SaludConfig.objects.all()

    context = {
        'trabajadores_activos': trabajadores_activos,
        'trabajadores_inactivos': trabajadores_inactivos,
        'afps': lista_afps,       
        'saluds': lista_salud,    
    }
    return render(request, 'gestion/trabajadores/gestion_trabajadores.html', context)

@login_required
def agregar_trabajador(request):
    """
    Crea el trabajador básico.
    LOGICA BODEGA FACTURACION: 
    - Si es 'Ambos', toma la elegida manualmente.
    - Si es 1221 o 1225, la asigna igual para mantener coherencia.
    """
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        bodega = request.POST.get('bodega')
        bodega_fac_input = request.POST.get('bodega_facturacion')
        tipo = request.POST.get('tipo') 
        
        # Lógica de asignación automática de facturación
        bodega_facturacion_final = None
        if bodega == 'Ambos':
            bodega_facturacion_final = bodega_fac_input
        else:
            bodega_facturacion_final = bodega # Si trabaja solo en 1221, factura en 1221

        if nombre and bodega:
            try:
                Trabajador.objects.create(
                    nombre=nombre,
                    bodega_asignada=bodega,
                    bodega_facturacion=bodega_facturacion_final,
                    tipo=tipo, 
                    activo=True, 
                    filtro_trabajador=True 
                )
                messages.success(request, f"Trabajador {nombre} creado.")
                return redirect('gestion_trabajadores')
            except Exception as e:
                messages.error(request, f"Error al crear: {e}")
        
    return redirect('gestion_trabajadores')

@login_required
def editar_trabajador(request, trabajador_id):
    """
    Procesa el formulario del MODAL COMPLETO.
    AGREGADO: Lógica para bodega_facturacion.
    """
    trabajador = get_object_or_404(Trabajador, id=trabajador_id)
    
    if request.method == 'POST':
        try:
            # 1. Datos de Configuración (Switches)
            val_activo = request.POST.get('activo')
            val_filtro = request.POST.get('filtro_trabajador')
            
            estaba_activo = True if val_activo == 'SI' else False
            estaba_filtro = True if val_filtro == 'SI' else False

            # Seguridad: Si se archiva, se apaga filtro
            if not estaba_activo:
                trabajador.activo = False
                trabajador.filtro_trabajador = False
            else:
                trabajador.activo = True
                trabajador.filtro_trabajador = estaba_filtro

            # 2. Datos Personales
            trabajador.nombre = request.POST.get('nombre')
            trabajador.tipo = request.POST.get('tipo') 
            trabajador.cargo = request.POST.get('cargo')
            
            # --- LOGICA BODEGA & FACTURACION ---
            bodega_seleccionada = request.POST.get('bodega')
            bodega_fac_input = request.POST.get('bodega_facturacion')

            trabajador.bodega_asignada = bodega_seleccionada
            
            if bodega_seleccionada == 'Ambos':
                trabajador.bodega_facturacion = bodega_fac_input
            else:
                trabajador.bodega_facturacion = bodega_seleccionada

            # --- MANEJO INTELIGENTE DEL RUT ---
            rut_input = request.POST.get('rut', '').strip()
            if rut_input:
                trabajador.rut = rut_input
            else:
                trabajador.rut = None

            # --- MANEJO INTELIGENTE DE FECHA ---
            fecha_ing = request.POST.get('fecha_ingreso')
            if fecha_ing:
                trabajador.fecha_ingreso = fecha_ing
            else:
                trabajador.fecha_ingreso = None

            # 3. Datos Económicos
            s_base = request.POST.get('sueldo_base', '')
            trabajador.sueldo_base = int(s_base) if s_base.strip() else 0
            
            h_extra = request.POST.get('valor_hora_extra', '')
            trabajador.valor_hora_extra = int(h_extra) if h_extra.strip() else 0

            # 4. Relaciones (Foreign Keys)
            afp_id = request.POST.get('afp')
            salud_id = request.POST.get('salud')

            trabajador.afp_id = afp_id if afp_id else None
            trabajador.salud_id = salud_id if salud_id else None
            
            # 5. Datos Familiares
            asignacion = request.POST.get('tiene_asignacion')
            trabajador.tiene_asignacion_familiar = True if asignacion == 'SI' else False
            
            cargas = request.POST.get('cargas', '')
            trabajador.cargas_familiares = int(cargas) if cargas.strip() else 0

            # Guardar todo
            trabajador.save()
            
            if not trabajador.activo:
                messages.warning(request, f"{trabajador.nombre} ha sido ARCHIVADO y quitado de los filtros.")
            else:
                messages.success(request, f"Datos de {trabajador.nombre} actualizados.")

        except IntegrityError:
            messages.error(request, "Error: El RUT ingresado ya pertenece a otro trabajador.")
        except Exception as e:
            messages.error(request, f"Error al guardar: {e}")
            
        return redirect('gestion_trabajadores')
        
    return redirect('gestion_trabajadores')

@login_required
def restaurar_trabajador(request, trabajador_id):
    """
    Restaura un trabajador inactivo (Archivado) a Activo.
    """
    trabajador = get_object_or_404(Trabajador, id=trabajador_id)
    try:
        trabajador.activo = True
        trabajador.save()
        messages.success(request, f"{trabajador.nombre} ha sido restaurado a la lista activa. (Revisa si necesitas activar su filtro)")
    except Exception as e:
        messages.error(request, f"Error al restaurar: {e}")
    
    return redirect('gestion_trabajadores')

@login_required
def eliminar_trabajador(request, trabajador_id):
    if request.method == 'POST':
        trabajador = get_object_or_404(Trabajador, id=trabajador_id)
        try:
            trabajador.delete()
            messages.success(request, "Trabajador eliminado exitosamente.")
        except Exception as e:
            messages.error(request, "No se puede eliminar porque tiene registros asociados.")
    
    return redirect('gestion_trabajadores')