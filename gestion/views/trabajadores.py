from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from gestion.models import Trabajador, BODEGA_CHOICES

# --- GESTIÓN DE TRABAJADORES ---

@login_required
def gestion_trabajadores(request):
    lista_trabajadores = Trabajador.objects.all().order_by('nombre')
    context = {
        'trabajadores': lista_trabajadores,
    }
    return render(request, 'gestion/trabajadores/gestion_trabajadores.html', context)

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