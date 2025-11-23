from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # ==========================================
    # 1. RUTA RAÍZ
    # ==========================================
    path('', views.home, name='index'),

    # ==========================================
    # 2. RUTAS DE AUTENTICACIÓN
    # ==========================================
    path('accounts/login/', auth_views.LoginView.as_view(template_name='depositos/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # ==========================================
    # 3. DASHBOARD
    # ==========================================
    path('home/', views.home, name='home'),

    # ==========================================
    # 4. MÓDULO FLUJO DE CAJA (Menú y Detalle)
    # ==========================================
    path('total-dia/', views.total_dia, name='total_dia'), # <--- Ahora es el MENÚ
    path('resumen-consolidado/', views.resumen_consolidado, name='resumen_consolidado'), # <--- Nuevo: Dashboard Detalle

    # ==========================================
    # 5. GESTIÓN DE TRABAJADORES
    # ==========================================
    path('trabajadores/', views.gestion_trabajadores, name='gestion_trabajadores'),
    path('trabajadores/agregar/', views.agregar_trabajador, name='agregar_trabajador'),
    path('trabajadores/<int:trabajador_id>/editar/', views.editar_trabajador, name='editar_trabajador'),
    path('trabajadores/<int:trabajador_id>/eliminar/', views.eliminar_trabajador, name='eliminar_trabajador'),

    # ==========================================
    # 6. OPERATIVA LOTES
    # ==========================================
    path('deposito/<str:bodega_nombre>/', views.deposito_bodega, name='deposito_bodega'),
    path('crear-lote/', views.crear_nuevo_lote, name='crear_nuevo_lote'),
    path('lote/<int:lote_id>/', views.editar_lote, name='editar_lote'),
    path('lote/<int:lote_id>/eliminar/', views.eliminar_lote, name='eliminar_lote'),
    path('lote/<int:lote_id>/desbloquear/', views.desbloquear_lote, name='desbloquear_lote'),
    path('lote/<int:lote_id>/renombrar/', views.renombrar_lote, name='renombrar_lote'),

    # ==========================================
    # 7. OPERATIVA APORTES
    # ==========================================
    path('lote/<int:lote_id>/agregar-aporte/', views.agregar_aporte, name='agregar_aporte'),
    path('lote/<int:lote_id>/quitar-aportes/', views.quitar_aportes_seleccion, name='quitar_aportes_seleccion'),

    # ==========================================
    # 8. REPORTES
    # ==========================================
    path('reportes/', views.reportes_mensuales, name='reportes_mensuales'),
    path('lote/<int:lote_id>/pdf/', views.generar_pdf_lote, name='generar_pdf_lote'),
]