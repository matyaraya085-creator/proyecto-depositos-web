from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from gestion.models import Vehiculo
from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError

def agregar_vehiculo(request):
    """
    Función de vista para manejar la adición de un nuevo vehículo.
    Implementación FINAL de la lógica de guardado.
    """
    if request.method == 'POST':
        try:
            # 1. Obtener datos del formulario (POST)
            patente = request.POST.get('patente', '').upper()
            
            # 2. Crear y guardar el nuevo objeto Vehiculo
            Vehiculo.objects.create(
                patente=patente,
                fecha_mantencion=request.POST.get('fecha_mantencion'),
                
                # El formulario usa 'fecha_circulacion', el modelo usa 'fecha_permiso'
                fecha_permiso=request.POST.get('fecha_circulacion'), 
                
                # El formulario usa 'kilometraje', el modelo usa 'kilometraje_actual'
                kilometraje_actual=int(request.POST.get('kilometraje') or 0), 
                kilometraje_maximo=int(request.POST.get('kilometraje_maximo') or 0),
                
                # Coincide con el modelo
                km_diarios=float(request.POST.get('km_diarios') or 0.0),
                dias_uso_semanal=int(request.POST.get('dias_semana') or 5)
            )
            
            # Si se guarda con éxito, redirige a la lista
            return redirect('menu_camionetas') 

        except IntegrityError:
            # messages.error(request, f"La patente {patente} ya existe.")
            pass
        except ValueError:
            # messages.error(request, "Error de formato en números o fechas.")
            pass
        except Exception:
            # messages.error(request, "Ocurrió un error inesperado al guardar.")
            pass
            
        # En caso de error, siempre redirige para evitar el POST/GET loop
        return redirect('menu_camionetas') 
    
    return redirect('menu_camionetas')

def calcular_estado(vehiculo):
    """
    Replica la lógica de tu script Python para definir el estado y alertas.
    Retorna: (color_bootstrap, lista_de_mensajes)
    """
    hoy = date.today()
    mensajes = []
    color = "success" # Verde por defecto (Todo ok)
    
    # 1. Análisis de Mantención
    if vehiculo.fecha_mantencion:
        dias_mant = (vehiculo.fecha_mantencion - hoy).days
        if dias_mant <= 0:
            mensajes.append("🔴 MANTENCIÓN VENCIDA")
            color = "danger"
        elif dias_mant <= 30:
            mensajes.append(f"🟡 Mantención en {dias_mant} días")
            if color != "danger": color = "warning"

    # 2. Análisis de Permiso de Circulación
    if vehiculo.fecha_permiso:
        dias_perm = (vehiculo.fecha_permiso - hoy).days
        if dias_perm <= 0:
            mensajes.append("🔴 PERMISO VENCIDO")
            color = "danger"
        elif dias_perm <= 30:
            mensajes.append(f"🟡 Permiso vence en {dias_perm} días")
            if color != "danger": color = "warning"

    # 3. Análisis de Kilometraje
    # (Asumimos que kilometraje_maximo es el próximo cambio de aceite/revisión)
    if vehiculo.kilometraje_maximo > 0:
        km_restante = vehiculo.kilometraje_maximo - vehiculo.kilometraje_actual
        if km_restante <= 0:
            mensajes.append(f"🔴 KILOMETRAJE EXCEDIDO ({km_restante} km)")
            color = "danger"
        elif km_restante <= 1000: # Alerta a los 1000km antes
            mensajes.append(f"🟡 Cambio de aceite en {km_restante} km")
            if color != "danger": color = "warning"

    if not mensajes:
        mensajes.append("🟢 Todo en orden")

    return color, mensajes

def menu_camionetas(request):
    """
    Vista principal: Muestra la tabla de control con semáforos.
    """
    vehiculos_query = Vehiculo.objects.all()
    lista_vehiculos = []

    for v in vehiculos_query:
        # Calculamos estado para cada camioneta
        color, alertas = calcular_estado(v)
        
        # Creamos un diccionario con todo lo necesario para el HTML
        lista_vehiculos.append({
            'patente': v.patente,
            'fecha_mantencion': v.fecha_mantencion,
            'fecha_permiso': v.fecha_permiso,
            'km_actual': v.kilometraje_actual,
            'km_max': v.kilometraje_maximo,
            'color': color,
            'alertas': alertas,
            'id': v.id # Para editar/borrar futuro
        })

    context = {
        'vehiculos': lista_vehiculos,
        'hoy': date.today()
    }
    return render(request, 'gestion/camionetas/menu_camionetas.html', context)

def inventario_flota(request):
    # Por ahora redirigimos al menú que ya tiene el inventario
    return menu_camionetas(request)

def editar_vehiculo(request, patente):
    """
    Gestiona la edición de un vehículo existente.
    El modal de la plantilla envía todos los datos por POST a esta función.
    """
    # 1. Intentar obtener el vehículo o lanzar 404 si no existe
    vehiculo = get_object_or_404(Vehiculo, patente=patente)

    if request.method == 'POST':
        try:
            # 2. Actualizar campos con los nuevos datos del formulario
            # Los nombres de los campos deben coincidir con los atributos 'name' del modal
            
            # Nota: La patente no se cambia aquí, solo se usa como clave para la búsqueda.
            
            vehiculo.fecha_mantencion = request.POST.get('fecha_mantencion')
            vehiculo.fecha_permiso = request.POST.get('fecha_circulacion')
            
            # Se usan int() y float() para asegurar el tipo de dato
            vehiculo.kilometraje_actual = int(request.POST.get('kilometraje') or 0)
            vehiculo.kilometraje_maximo = int(request.POST.get('kilometraje_maximo') or 0)
            
            vehiculo.km_diarios = float(request.POST.get('km_diarios') or 0.0)
            vehiculo.dias_uso_semanal = int(request.POST.get('dias_semana') or 5)
            
            # 3. Guardar los cambios en la base de datos
            vehiculo.save()
            
            # Opcional: messages.success(request, f"Vehículo {patente} actualizado con éxito.")

        except ValueError:
            # messages.error(request, "Error: Revisa que los campos numéricos sean válidos.")
            pass
        except Exception:
            # messages.error(request, "Ocurrió un error inesperado al actualizar.")
            pass
            
        # Redirigir siempre a la tabla principal después de la operación (POST)
        return redirect('menu_camionetas')
        
    # Si alguien intenta acceder directamente con GET a esta URL, redirigir
    return redirect('menu_camionetas')

def eliminar_vehiculo(request, patente):
    """
    Elimina un vehículo de la base de datos dado su patente (Primary Key).
    """
    if request.method == 'POST':
        try:
            # get_object_or_404 busca el vehículo y si no lo encuentra, lanza un error 404
            vehiculo = get_object_or_404(Vehiculo, patente=patente)
            
            # Ejecuta la eliminación
            vehiculo.delete()
            
            # Opcional: messages.success(request, f"Vehículo {patente} eliminado con éxito.")
            
        except Exception as e:
            # Opcional: messages.error(request, f"Error al intentar eliminar el vehículo {patente}: {e}")
            pass
            
        # Redirigir siempre a la tabla principal después de la operación
        return redirect('menu_camionetas')
        
    # Si alguien intenta acceder directamente con GET, lo redirigimos
    return redirect('menu_camionetas')