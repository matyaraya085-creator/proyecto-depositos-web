from django.urls import path
from django.contrib.auth import views as auth_views
from gestion.views import core, banco, trabajadores, caja_trabajador, remuneraciones, flota_camionetas
from . import views

urlpatterns = [
    # ==========================================
    # 1. CORE (Login, Home y Logout personalizado)
    # ==========================================
    path('', core.home, name='index'),
    path('home/', core.home, name='home'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='gestion/core/login.html'), name='login'),
    
    # Logout personalizado
    path('logout/', core.cerrar_sesion, name='logout'),

    # ==========================================
    # 2. MÓDULO BANCO
    # ==========================================
    path('total-dia/', banco.total_dia, name='total_dia'),
    path('resumen-consolidado/', banco.resumen_consolidado, name='resumen_consolidado'),
    path('deposito/<str:bodega_nombre>/', banco.deposito_bodega, name='deposito_bodega'),
    path('crear-lote/', banco.crear_nuevo_lote, name='crear_nuevo_lote'),
    path('lote/<int:lote_id>/', banco.editar_lote, name='editar_lote'),
    path('lote/<int:lote_id>/eliminar/', banco.eliminar_lote, name='eliminar_lote'),
    path('lote/<int:lote_id>/desbloquear/', banco.desbloquear_lote, name='desbloquear_lote'),
    path('lote/<int:lote_id>/renombrar/', banco.renombrar_lote, name='renombrar_lote'),
    path('lote/<int:lote_id>/agregar-aporte/', banco.agregar_aporte, name='agregar_aporte'),
    path('lote/<int:lote_id>/quitar-aportes/', banco.quitar_aportes_seleccion, name='quitar_aportes_seleccion'),
    path('reportes/', banco.reportes_mensuales, name='reportes_mensuales'),
    path('lote/<int:lote_id>/pdf/', banco.generar_pdf_lote, name='generar_pdf_lote'),

    # ==========================================
    # 3. GESTIÓN DE TRABAJADORES (FLUJO DE CAJA)
    # ==========================================
    # Menú principal
    path('trabajadores/menu/', caja_trabajador.menu_trabajadores, name='menu_trabajadores'),
    
    # Dashboard y Acciones
    path('trabajadores/dashboard/', caja_trabajador.dashboard_bodega, name='dashboard_bodega'),
    path('trabajadores/rendicion/crear/', caja_trabajador.crear_rendicion_vacia, name='crear_rendicion_vacia'),
    path('trabajadores/rendicion/<int:rendicion_id>/editar/', caja_trabajador.form_rendicion_editar, name='form_rendicion_editar'),
    path('trabajadores/rendicion/<int:rendicion_id>/cerrar/', caja_trabajador.cerrar_rendicion, name='cerrar_rendicion'),
    path('trabajadores/rendicion/<int:rendicion_id>/abrir/', caja_trabajador.abrir_rendicion, name='abrir_rendicion'),
    path('trabajadores/rendicion/<int:rendicion_id>/eliminar/', caja_trabajador.eliminar_rendicion, name='eliminar_rendicion'),

    # REPORTES Y CONFIGURACIÓN (Aquí faltaba la línea de estadísticas)
    path('trabajadores/reporte-mensual/', caja_trabajador.reporte_mensual, name='reporte_mensual_trabajador'),
    path('trabajadores/configurar-tarifas/', caja_trabajador.configurar_comisiones, name='configurar_comisiones'),
    path('trabajadores/estadisticas/', caja_trabajador.estadisticas_globales, name='estadisticas_globales'), 
    
    # CRUD de trabajadores
    path('trabajadores/', trabajadores.gestion_trabajadores, name='gestion_trabajadores'),
    path('trabajadores/agregar/', trabajadores.agregar_trabajador, name='agregar_trabajador'),
    path('trabajadores/<int:trabajador_id>/editar/', trabajadores.editar_trabajador, name='editar_trabajador'),
    path('trabajadores/<int:trabajador_id>/eliminar/', trabajadores.eliminar_trabajador, name='eliminar_trabajador'),

    # ==========================================
    # 4. MÓDULO REMUNERACIONES
    # ==========================================
    path('remuneraciones/menu/', remuneraciones.menu_remuneraciones, name='menu_remuneraciones'),
    path('remuneraciones/nomina/', remuneraciones.nomina_mensual, name='nomina_mensual'),
    path('remuneraciones/calcular/<int:id>/', remuneraciones.calcular_sueldo, name='calcular_sueldo'),
    path('remuneraciones/liquidacion/<int:id>/', remuneraciones.ver_liquidacion, name='ver_liquidacion'),
    path('remuneraciones/parametros/', remuneraciones.parametros, name='parametros_remuneraciones'),
    path('remuneraciones/historial/', remuneraciones.historial, name='historial_remuneraciones'),
    path('remuneraciones/inicializar-db/', remuneraciones.inicializar_parametros_remuneraciones, name='inicializar_parametros'),
    path('remuneraciones/guardar-indicadores/', remuneraciones.guardar_indicadores, name='guardar_indicadores'),
    path('remuneraciones/tasa/<str:modelo>/<str:nombre>/editar/', remuneraciones.editar_tasa_previsional, name='editar_tasa_previsional'),
    path('remuneraciones/tramos/editar/', remuneraciones.editar_tramos_asignacion, name='editar_tramos_asignacion'),

    # ==========================================
    # 5. MÓDULO FLOTA (CAMIONETAS)
    # ==========================================
    path('flota/menu/', flota_camionetas.menu_camionetas, name='menu_camionetas'),
    path('flota/agregar/', flota_camionetas.agregar_vehiculo, name='agregar_vehiculo'),
    path('flota/<str:patente>/editar/', flota_camionetas.editar_vehiculo, name='editar_vehiculo'),
    path('flota/<str:patente>/eliminar/', flota_camionetas.eliminar_vehiculo, name='eliminar_vehiculo'),
]