from datetime import date
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum
from gestion.models import Remuneracion

def menu_remuneraciones(request):
    """Menú principal."""
    return render(request, 'gestion/remuneraciones/remuneraciones_menu.html')

def historial(request):
    """Historial de liquidaciones (Internos)."""
    fecha_get = request.GET.get('fecha')
    hoy = timezone.now()
    
    if fecha_get:
        try:
            anio, mes = map(int, fecha_get.split('-'))
            fecha_sel = date(anio, mes, 1)
        except ValueError: fecha_sel = hoy.date()
    else: fecha_sel = hoy.date()
        
    periodo_val = fecha_sel.strftime('%Y-%m')
    
    liquidaciones = Remuneracion.objects.filter(periodo=periodo_val).select_related('trabajador').order_by('trabajador__nombre')
    
    context = {
        'liquidaciones': liquidaciones,
        'periodo_str': fecha_sel.strftime('%B %Y').title(),
        'periodo_value': periodo_val,
        'total_pagado': liquidaciones.aggregate(Sum('sueldo_liquido'))['sueldo_liquido__sum'] or 0,
        'total_registros': liquidaciones.count(),
    }
    return render(request, 'gestion/remuneraciones/remuneraciones_historial/remuneraciones_historial.html', context)