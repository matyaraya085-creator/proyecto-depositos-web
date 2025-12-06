from django.urls import path
from django.contrib.auth import views as auth_views
# IMPORTANTE: Agregamos 'remuneraciones' a los imports
from gestion.views import core, banco, trabajadores, caja_trabajador, remuneraciones

urlpatterns = [
    # ==========================================
    # 1. CORE (Login y Home)
    # ==========================================
    path('', core.home, name='index'),
    path('home/', core.home, name='home'),
    
    # Rutas de autenticación
    path('accounts/login/', auth_views.LoginView.as_view(template_name='gestion/core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # ==========================================
    # 2. MÓDULO BANCO (Caja, Lotes, Reportes)
    # ==========================================
    path('total-dia/', banco.total_dia, name='total_dia'),
    path('resumen-consolidado/', banco.resumen_consolidado, name='resumen_consolidado'),
    path('deposito/<str:bodega_nombre>/', banco.deposito_bodega, name='deposito_bodega'),
    path('crear-lote/', banco.crear_nuevo_lote, name='crear_nuevo_lote'),
    path('lote/<int:lote_id>/', banco.editar_lote, name='editar_lote'),
    path('lote/<int:lote_id>/eliminar/', banco.eliminar_lote, name='eliminar_lote'),
    path('lote/<int:lote_id>/desbloquear/', banco.desbloquear_lote, name='desbloquear_lote'),
    path('lote/<int:lote_id>/renombrar/', banco.renombrar_lote, name='renombrar_lote'),
    
    # Operativa Aportes
    path('lote/<int:lote_id>/agregar-aporte/', banco.agregar_aporte, name='agregar_aporte'),
    path('lote/<int:lote_id>/quitar-aportes/', banco.quitar_aportes_seleccion, name='quitar_aportes_seleccion'),
    
    # Reportes
    path('reportes/', banco.reportes_mensuales, name='reportes_mensuales'),
    path('lote/<int:lote_id>/pdf/', banco.generar_pdf_lote, name='generar_pdf_lote'),

    # ==========================================
    # 3. GESTIÓN DE TRABAJADORES
    # ==========================================
    # --- NUEVA RUTA DEL MENÚ ---
    path('trabajadores/menu/', caja_trabajador.menu_trabajadores, name='menu_trabajadores'),
    path('trabajadores/rendicion-ejemplo/', caja_trabajador.form_rendicion, name='form_rendicion_ejemplo'),
    path('trabajadores/reporte-mensual/', caja_trabajador.reporte_mensual, name='reporte_mensual_trabajador'),
    
    # Rutas CRUD existentes
    path('trabajadores/', trabajadores.gestion_trabajadores, name='gestion_trabajadores'),
    path('trabajadores/agregar/', trabajadores.agregar_trabajador, name='agregar_trabajador'),
    path('trabajadores/<int:trabajador_id>/editar/', trabajadores.editar_trabajador, name='editar_trabajador'),
    path('trabajadores/<int:trabajador_id>/eliminar/', trabajadores.eliminar_trabajador, name='eliminar_trabajador'),

    # ==========================================
    # 4. MÓDULO REMUNERACIONES (NUEVO)
    # ==========================================
    path('remuneraciones/menu/', remuneraciones.menu_remuneraciones, name='menu_remuneraciones'),
]