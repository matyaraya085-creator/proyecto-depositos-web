from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from gestion.models import Trabajador, BODEGA_CHOICES, AfpConfig, SaludConfig

# --- GESTIÓN DE TRABAJADORES ---

@login_required
def gestion_trabajadores(request):
    """
    Vista principal. Muestra la lista y carga los datos necesarios 
    para los modales (AFPs y Salud).
    """
    lista_trabajadores = Trabajador.objects.all().order_by('nombre')
    
    # IMPORTANTE: Cargamos estas listas para usarlas en el modal de edición rápida
    # que está incrustado en el HTML principal.
    lista_afps = AfpConfig.objects.all()
    lista_salud = SaludConfig.objects.all()

    context = {
        'trabajadores': lista_trabajadores,
        'afps': lista_afps,       # Para el select del modal
        'saluds': lista_salud,    # Para el select del modal
    }
    return render(request, 'gestion/trabajadores/gestion_trabajadores.html', context)

@login_required
def agregar_trabajador(request):
    """
    Crea el trabajador básico (Paso 1).
    Los detalles financieros se agregan después con 'editar'.
    """
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        bodega = request.POST.get('bodega')
        
        if nombre and bodega:
            try:
                Trabajador.objects.create(
                    nombre=nombre,
                    bodega_asignada=bodega
                )
                messages.success(request, f"Trabajador {nombre} creado. Ahora completa sus datos.")
                return redirect('gestion_trabajadores')
            except Exception as e:
                messages.error(request, f"Error al crear: {e}")
        
    return redirect('gestion_trabajadores')

@login_required
def editar_trabajador(request, trabajador_id):
    """
    Procesa el formulario del MODAL COMPLETO (Paso 2).
    Guarda RUT, Sueldos, Previsión, etc.
    """
    trabajador = get_object_or_404(Trabajador, id=trabajador_id)
    
    if request.method == 'POST':
        try:
            # 1. Datos Personales y Operativos
            trabajador.nombre = request.POST.get('nombre')
            trabajador.rut = request.POST.get('rut')
            trabajador.cargo = request.POST.get('cargo')
            trabajador.bodega_asignada = request.POST.get('bodega')
            
            # Fecha (manejar vacío)
            fecha_ing = request.POST.get('fecha_ingreso')
            if fecha_ing:
                trabajador.fecha_ingreso = fecha_ing

            # 2. Datos Económicos (Convertir a entero o 0 si está vacío)
            s_base = request.POST.get('sueldo_base')
            trabajador.sueldo_base = int(s_base) if s_base else 0
            
            h_extra = request.POST.get('valor_hora_extra')
            trabajador.valor_hora_extra = int(h_extra) if h_extra else 0

            # 3. Relaciones (Foreign Keys)
            afp_id = request.POST.get('afp')
            salud_id = request.POST.get('salud')

            # Si viene un ID, lo asignamos, si no, lo dejamos nulo
            if afp_id:
                trabajador.afp_id = afp_id
            else:
                trabajador.afp = None

            if salud_id:
                trabajador.salud_id = salud_id
            else:
                trabajador.salud = None
            
            # 4. Datos Familiares
            asignacion = request.POST.get('tiene_asignacion')
            trabajador.tiene_asignacion_familiar = True if asignacion == 'SI' else False
            
            cargas = request.POST.get('cargas')
            trabajador.cargas_familiares = int(cargas) if cargas else 0

            # Guardar todo
            trabajador.save()
            messages.success(request, f"Ficha de {trabajador.nombre} actualizada correctamente.")

        except Exception as e:
            messages.error(request, f"Error al actualizar: {e}")
            
        return redirect('gestion_trabajadores')
        
    # Si por alguna razón entran por GET a editar (no debería pasar con el modal),
    # redirigimos a la lista principal.
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