from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

# =========================================================================
# IMPORTACIONES DE VISTAS
# =========================================================================

# 1. CORE
from gestion.views import core, trabajadores

# 2. SUB-MÓDULOS
from gestion.views.caja_trabajador import caja_trabajador as view_caja
from gestion.views.camionetas import camionetas as view_camionetas
from gestion.views.caja_banco import caja_banco as view_banco 
from gestion.views.clientes_credito import clientes_credito as view_clientes 

# 3. MÓDULO REMUNERACIONES
from gestion.views.remuneraciones import (
    remuneraciones_internos as internos,
    remuneraciones_externos as externos,
    remuneraciones_historial as historial
)

urlpatterns = [
    # ==========================================
    # 1. CORE
    # ==========================================
    path('', core.home, name='index'),
    path('home/', core.home, name='home'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='gestion/core/login.html'), name='login'),
    path('logout/', core.cerrar_sesion, name='logout'),

    # ==========================================
    # 2. MÓDULO BANCO
    # ==========================================
    path('total-dia/', view_banco.total_dia, name='total_dia'),
    path('resumen-consolidado/', view_banco.resumen_consolidado, name='resumen_consolidado'),
    path('deposito/<str:bodega_nombre>/', view_banco.deposito_bodega, name='deposito_bodega'),
    path('crear-lote/', view_banco.crear_nuevo_lote, name='crear_nuevo_lote'),
    
    path('lote/<int:lote_id>/', view_banco.editar_lote, name='editar_lote'),
    path('lote/<int:lote_id>/eliminar/', view_banco.eliminar_lote, name='eliminar_lote'),
    path('lote/<int:lote_id>/desbloquear/', view_banco.desbloquear_lote, name='desbloquear_lote'),
    path('lote/<int:lote_id>/renombrar/', view_banco.renombrar_lote, name='renombrar_lote'),
    path('lote/<int:lote_id>/pdf/', view_banco.generar_pdf_lote, name='generar_pdf_lote'),
    path('lote/<int:lote_id>/auto_save/', view_banco.api_auto_guardar_arqueo, name='api_auto_guardar_arqueo'),
    
    path('lote/<int:lote_id>/excel/', view_banco.exportar_lote_excel, name='exportar_lote_excel'),

    path('lote/<int:lote_id>/agregar-aporte/', view_banco.agregar_aporte, name='agregar_aporte'),
    path('lote/<int:lote_id>/quitar-aportes/', view_banco.quitar_aportes_seleccion, name='quitar_aportes_seleccion'),
    path('aporte/editar/<int:aporte_id>/', view_banco.editar_aporte, name='editar_aporte'),

    path('reportes/', view_banco.reportes_mensuales, name='reportes_mensuales'),
    path('reportes/exportar/', view_banco.exportar_mensual_excel, name='exportar_mensual_excel'),

    # ==========================================
    # 3. GESTIÓN DE TRABAJADORES
    # ==========================================
    path('trabajadores/menu/', view_caja.menu_trabajadores, name='menu_trabajadores'),
    path('trabajadores/dashboard/', view_caja.dashboard_bodega, name='dashboard_bodega'),
    path('trabajadores/rendicion/crear/', view_caja.crear_rendicion_vacia, name='crear_rendicion_vacia'),
    path('trabajadores/rendicion/<int:rendicion_id>/editar/', view_caja.form_rendicion_editar, name='form_rendicion_editar'),
    path('trabajadores/rendicion/<int:rendicion_id>/auto_save/', view_caja.api_auto_guardar_rendicion, name='api_auto_guardar_rendicion'),
    path('trabajadores/rendicion/<int:rendicion_id>/cerrar/', view_caja.cerrar_rendicion, name='cerrar_rendicion'),
    path('trabajadores/rendicion/<int:rendicion_id>/abrir/', view_caja.abrir_rendicion, name='abrir_rendicion'),
    path('trabajadores/rendicion/<int:rendicion_id>/eliminar/', view_caja.eliminar_rendicion, name='eliminar_rendicion'),
    path('trabajadores/reporte-mensual/', view_caja.reporte_mensual, name='reporte_mensual_trabajador'),
    path('trabajadores/reporte-mensual/pdf/', view_caja.exportar_pdf_mensual, name='exportar_pdf_mensual'),
    
    path('trabajadores/configurar-tarifas/', view_caja.configurar_comisiones, name='configurar_comisiones'),
    path('trabajadores/estadisticas/', view_caja.estadisticas_globales, name='estadisticas_globales'), 
    
    # ==========================================
    # 4. CRUD TRABAJADORES
    # ==========================================
    path('trabajadores/', trabajadores.gestion_trabajadores, name='gestion_trabajadores'),
    path('trabajadores/agregar/', trabajadores.agregar_trabajador, name='agregar_trabajador'),
    path('trabajadores/<int:trabajador_id>/editar/', trabajadores.editar_trabajador, name='editar_trabajador'),
    path('trabajadores/<int:trabajador_id>/eliminar/', trabajadores.eliminar_trabajador, name='eliminar_trabajador'),
    path('trabajadores/<int:trabajador_id>/restaurar/', trabajadores.restaurar_trabajador, name='restaurar_trabajador'),

    # ==========================================
    # 5. MÓDULO REMUNERACIONES (INTERNOS)
    # ==========================================
    path('remuneraciones/menu/', historial.menu_remuneraciones, name='menu_remuneraciones'),
    path('remuneraciones/historial/', historial.historial, name='historial_remuneraciones'),
    
    path('remuneraciones/nomina/', internos.nomina_mensual, name='nomina_mensual'),
    path('remuneraciones/calcular/<int:id>/', internos.calcular_sueldo, name='calcular_sueldo'),
    path('remuneraciones/liquidacion/<int:id>/', internos.ver_liquidacion, name='ver_liquidacion'),
    
    path('remuneraciones/exportar-individual/<int:id>/', internos.exportar_liquidacion_excel, name='exportar_liquidacion_excel'),
    path('remuneraciones/exportar-global/', internos.exportar_excel_global, name='exportar_excel_global'),

    path('remuneraciones/parametros/', internos.parametros, name='parametros_remuneraciones'),
    path('remuneraciones/indicador/actualizar/', internos.actualizar_indicador_singular, name='actualizar_indicador_singular'),
    path('remuneraciones/entidad/crear/', internos.crear_entidad_previsional, name='crear_entidad_previsional'),
    path('remuneraciones/entidad/<str:tipo>/<int:id>/editar/', internos.editar_entidad_previsional, name='editar_entidad_previsional'),
    path('remuneraciones/entidad/<str:tipo>/<int:id>/eliminar/', internos.eliminar_entidad_previsional, name='eliminar_entidad_previsional'),
    path('remuneraciones/tramos/editar/', internos.editar_tramos_asignacion, name='editar_tramos_asignacion'),
    
    # EXTERNOS
    path('remuneraciones/externos/', externos.nomina_externos, name='nomina_externos'),
    path('remuneraciones/externos/calcular/<int:trabajador_id>/', externos.calcular_remuneracion_externa, name='calcular_remuneracion_externa'),
    path('remuneraciones/externos/detalle/<int:remu_id>/', externos.detalle_remuneracion_externa, name='detalle_remuneracion_externa'),
    path('remuneraciones/externos/exportar/', externos.exportar_excel_externos, name='exportar_excel_externos'),

    # ==========================================
    # 6. MÓDULO FLOTA
    # ==========================================
    path('flota/menu/', view_camionetas.menu_camionetas, name='menu_camionetas'),
    path('flota/agregar/', view_camionetas.agregar_vehiculo, name='agregar_vehiculo'),
    path('flota/<str:patente>/editar/', view_camionetas.editar_vehiculo, name='editar_vehiculo'),
    path('flota/<str:patente>/eliminar/', view_camionetas.eliminar_vehiculo, name='eliminar_vehiculo'),

    # ==========================================
    # 7. CLIENTES CRÉDITO (NUEVO)
    # ==========================================
    path('clientes/', view_clientes.menu_clientes, name='menu_clientes'),
    path('clientes/<int:cliente_id>/', view_clientes.detalle_cliente, name='detalle_cliente'),
]

# ESTO SOLUCIONA EL ERROR 404 DE LAS IMÁGENES
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)