from django.contrib import admin
from .models import Trabajador, DepositoDiario, DepositoAporte, DepositoDesglose

# --- REGISTRO DE MODELOS ---
# Esto le dice a Django: "Quiero ver estos modelos en el panel de admin"

@admin.register(Trabajador)
class TrabajadorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'bodega_asignada')
    search_fields = ('nombre',)
    list_filter = ('bodega_asignada',)

@admin.register(DepositoDiario)
class DepositoDiarioAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'bodega_nombre', 'numero_lote', 'nombre_lote', 'total_aportes', 'diferencia', 'cerrado')
    search_fields = ('nombre_lote',)
    list_filter = ('fecha', 'bodega_nombre', 'cerrado')
    
# Opcional: Registrar los otros modelos para verlos (aunque no es necesario editarlos directamente)
admin.site.register(DepositoAporte)
admin.site.register(DepositoDesglose)