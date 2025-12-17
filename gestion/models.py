from django.db import models
from datetime import date, datetime
from django.contrib.auth.models import User

# Opciones para bodegas (Usadas en Trabajadores)
BODEGA_CHOICES = [
    ('1221', '1221 (Manuel Peñafiel)'),
    ('1225', '1225 (David Perry)'),
    ('Ambos', 'Ambos'),
]

# Opciones para filtros y depósitos (Usadas en DepositoDiario)
BODEGA_FILTRO_CHOICES = [
    ('Manuel Peñafiel', '1221 (Manuel Peñafiel)'),
    ('David Perry', '1225 (David Perry)'),
]

# ==========================================================
# 1. CONFIGURACIÓN GLOBAL (UF, UTM, Sueldo Mínimo)
# ==========================================================
class ConfiguracionGlobal(models.Model):
    clave = models.CharField(max_length=50, unique=True)
    valor = models.FloatField()
    descripcion = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.descripcion}: {self.valor}"

# ==========================================================
# 2. TABLAS PREVISIONALES (AFP, Salud, Tramos)
# ==========================================================
class AfpConfig(models.Model):
    nombre = models.CharField(max_length=50)
    tasa = models.FloatField(help_text="Porcentaje de descuento (Ej: 11.44)")

    def __str__(self):
        return f"{self.nombre} ({self.tasa}%)"

class SaludConfig(models.Model):
    nombre = models.CharField(max_length=50)
    tasa = models.FloatField(help_text="Porcentaje de descuento (Ej: 7.0)")

    def __str__(self):
        return f"{self.nombre} ({self.tasa}%)"

class AsignacionFamiliarConfig(models.Model):
    tramo = models.CharField(max_length=1) 
    ingreso_tope = models.IntegerField()
    monto_por_carga = models.IntegerField()

    def __str__(self):
        return f"Tramo {self.tramo} - ${self.monto_por_carga}"

# ==========================================================
# 3. TRABAJADOR
# ==========================================================
class Trabajador(models.Model):
    nombre = models.CharField(max_length=255, verbose_name="Nombre Completo")
    rut = models.CharField(max_length=12, unique=True, null=True, verbose_name="RUT")
    
    bodega_asignada = models.CharField(max_length=100, choices=BODEGA_CHOICES, default='Ambos')
    cargo = models.CharField(max_length=100, default="Operario", null=True, blank=True)
    fecha_ingreso = models.DateField(null=True, blank=True)
    
    sueldo_base = models.IntegerField(default=460000, verbose_name="Sueldo Base")
    valor_hora_extra = models.IntegerField(default=0, verbose_name="Valor Hora Extra")
    
    afp = models.ForeignKey(AfpConfig, on_delete=models.SET_NULL, null=True, blank=True)
    salud = models.ForeignKey(SaludConfig, on_delete=models.SET_NULL, null=True, blank=True)
    
    cargas_familiares = models.IntegerField(default=0, verbose_name="N° Cargas")
    tiene_asignacion_familiar = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nombre} ({self.rut})"

# ==========================================================
# 4. REMUNERACIÓN
# ==========================================================
class Remuneracion(models.Model):
    trabajador = models.ForeignKey(Trabajador, on_delete=models.CASCADE)
    periodo = models.CharField(max_length=7) # Formato "2023-10"
    fecha_calculo = models.DateTimeField(auto_now_add=True)
    
    sueldo_liquido = models.IntegerField()
    total_haberes = models.IntegerField()
    total_descuentos = models.IntegerField()
    
    detalle_json = models.JSONField(verbose_name="Detalle Completo JSON")

    class Meta:
        unique_together = ('trabajador', 'periodo')
        ordering = ['-periodo']

    def __str__(self):
        return f"{self.trabajador.nombre} - {self.periodo} - ${self.sueldo_liquido}"

# ==========================================================
# 5. MODELOS CAJA BANCO (Lotes)
# ==========================================================
class DepositoDiario(models.Model):
    fecha = models.DateField()
    bodega_nombre = models.CharField(max_length=100, choices=BODEGA_FILTRO_CHOICES)
    numero_lote = models.IntegerField(default=1)
    nombre_lote = models.CharField(max_length=255, blank=True, default='', verbose_name="Nombre de Lote (Opcional)")
    total_aportes = models.BigIntegerField(default=0)
    total_desglose = models.BigIntegerField(default=0, verbose_name="Total Desglose (Efectivo)")
    diferencia = models.BigIntegerField(default=0)
    total_cheques = models.BigIntegerField(default=0)
    cerrado = models.BooleanField(default=False, verbose_name="¿Lote Cerrado?")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('fecha', 'bodega_nombre', 'numero_lote')

    def __str__(self):
        return f"{self.fecha} - {self.bodega_nombre} (Lote {self.numero_lote})"

class DepositoAporte(models.Model):
    deposito = models.ForeignKey(DepositoDiario, on_delete=models.CASCADE, related_name="aportes")
    trabajador = models.ForeignKey(Trabajador, on_delete=models.PROTECT, verbose_name="Trabajador")
    monto = models.BigIntegerField(default=0)
    descripcion = models.CharField(max_length=255, blank=True, default='')

    def __str__(self):
        return f"Aporte de {self.trabajador.nombre} ({self.monto})"

class DepositoDesglose(models.Model):
    deposito = models.ForeignKey(DepositoDiario, on_delete=models.CASCADE, related_name="desglose")
    denominacion = models.CharField(max_length=50)
    valor_unitario = models.IntegerField()
    cantidad = models.IntegerField(default=0)
    total_denominacion = models.BigIntegerField(default=0)

    def __str__(self):
        return f"{self.cantidad} x {self.denominacion}"

class Vehiculo(models.Model):
    patente = models.CharField(max_length=10, unique=True, verbose_name="Patente")
    fecha_mantencion = models.DateField(null=True, blank=True, verbose_name="Venc. Mantención")
    fecha_permiso = models.DateField(null=True, blank=True, verbose_name="Venc. Permiso Circulación")
    kilometraje_actual = models.IntegerField(default=0, verbose_name="KM Actual")
    kilometraje_maximo = models.IntegerField(default=0, verbose_name="KM Máximo (Mantención)")
    km_diarios = models.FloatField(default=0.0, verbose_name="Promedio KM Diarios")
    dias_uso_semanal = models.IntegerField(default=5, verbose_name="Días uso semana")

    def __str__(self):
        return f"{self.patente}"
    
    def get_alertas(self):
        alertas = []
        hoy = date.today()
        if self.fecha_mantencion and self.fecha_mantencion <= hoy:
            alertas.append("🔴 MANTENCIÓN VENCIDA")
        elif self.fecha_mantencion and (self.fecha_mantencion - hoy).days <= 30:
            dias = (self.fecha_mantencion - hoy).days
            alertas.append(f"🟡 Mantención vence en {dias} días")
        if self.fecha_permiso and self.fecha_permiso <= hoy:
            alertas.append("🔴 PERMISO VENCIDO")
        elif self.fecha_permiso and (self.fecha_permiso - hoy).days <= 30:
            dias = (self.fecha_permiso - hoy).days
            alertas.append(f"🟡 Permiso vence en {dias} días")
        km_restante = self.kilometraje_maximo - self.kilometraje_actual
        if km_restante <= 0:
            alertas.append(f"🔴 KILOMETRAJE EXCEDIDO ({km_restante} km)")
        elif km_restante <= 1000:
            alertas.append(f"🟡 Kilometraje al límite (quedan {km_restante} km)")
        return alertas

# ==========================================================
# 6. MÓDULO DE FLUJO POR TRABAJADOR (RENDICIÓN)
# ==========================================================
class RendicionDiaria(models.Model):
    """
    Almacena la rendición diaria de un trabajador.
    """
    trabajador = models.ForeignKey(Trabajador, on_delete=models.CASCADE, verbose_name="Trabajador")
    fecha = models.DateField(default=date.today)
    
    # Bodega donde se hizo el turno
    bodega = models.CharField(max_length=10, default='1221', verbose_name="Bodega del Turno")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Bloqueo de registro (Cierre de caja)
    cerrado = models.BooleanField(default=False, verbose_name="¿Rendición Cerrada?")

    # --- 1. DETALLE DE CILINDROS (MODIFICADO POR SOLICITUD) ---
    # Línea Normal
    gas_5kg = models.IntegerField(default=0, verbose_name="Lipigas 5kg")
    gas_11kg = models.IntegerField(default=0, verbose_name="Lipigas 11kg")
    gas_15kg = models.IntegerField(default=0, verbose_name="Lipigas 15kg")
    gas_45kg = models.IntegerField(default=0, verbose_name="Lipigas 45kg")
    
    # Línea Especial (Nuevos)
    gasc_5kg = models.IntegerField(default=0, verbose_name="Cat 5kg (05 Cat)")
    gasc_15kg = models.IntegerField(default=0, verbose_name="Cat 15kg (15 Cat)")
    gas_ultra_15kg = models.IntegerField(default=0, verbose_name="Ultra 15kg")

    cilindros_defectuosos = models.IntegerField(default=0)

    # DATO CRÍTICO (Suma total)
    total_kilos = models.FloatField(default=0.0, help_text="Suma de Kilos Vendidos")

    # --- 2. RENDICIÓN DE VALORES (CAJA) ---
    total_venta = models.BigIntegerField(default=0, verbose_name="Total Venta (Guía)")

    monto_credito = models.BigIntegerField(default=0, verbose_name="Crédito Empresa") # (Ignorado en cálculo, pero guardado)
    monto_vales = models.BigIntegerField(default=0, verbose_name="Vales/Prepago")
    monto_transbank = models.BigIntegerField(default=0, verbose_name="Transbank")

    # Efectivo
    efectivo_entregado = models.BigIntegerField(default=0, verbose_name="Efectivo Real")
    
    # DATOS CALCULADOS
    efectivo_esperado = models.BigIntegerField(default=0, help_text="Venta - Descuentos")
    diferencia = models.BigIntegerField(default=0, help_text="Real - Esperado")

    class Meta:
        ordering = ['-fecha', 'created_at'] 
        verbose_name = "Rendición Diaria"
        verbose_name_plural = "Rendiciones Diarias"

    def __str__(self):
        return f"{self.fecha} | {self.trabajador.nombre} | Bodega {self.bodega}"
    
# ==========================================================
# 7. CONFIGURACIÓN DE COMISIONES (NUEVO)
# ==========================================================
class TarifaComision(models.Model):
    """
    Define cuánto se paga al chofer por cada unidad vendida.
    Solo debería haber 1 registro activo, o se usa el último modificado.
    """
    nombre = models.CharField(max_length=100, default="Tarifa Estándar")
    
    # Tarifas Normales
    tarifa_5kg = models.IntegerField(default=0, verbose_name="Tarifa 5kg")
    tarifa_11kg = models.IntegerField(default=0, verbose_name="Tarifa 11kg")
    tarifa_15kg = models.IntegerField(default=0, verbose_name="Tarifa 15kg")
    tarifa_45kg = models.IntegerField(default=0, verbose_name="Tarifa 45kg")
    
    # Tarifas Especiales
    tarifa_cat_5kg = models.IntegerField(default=0, verbose_name="Tarifa Cat 5kg")
    tarifa_cat_15kg = models.IntegerField(default=0, verbose_name="Tarifa Cat 15kg")
    tarifa_ultra_15kg = models.IntegerField(default=0, verbose_name="Tarifa Ultra 15kg")

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} (Actua.: {self.updated_at.strftime('%d/%m/%Y')})"

# ==========================================================
# 8. CONTROL DE CIERRE DIARIO (NUEVO)
# ==========================================================
class CierreDiario(models.Model):
    """
    Si existe un registro para fecha/bodega, el día está BLOQUEADO globalmente.
    """
    fecha = models.DateField()
    bodega = models.CharField(max_length=10, choices=BODEGA_CHOICES)
    cerrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('fecha', 'bodega') # Solo un cierre por bodega/día
        verbose_name = "Cierre Diario Global"

    def __str__(self):
        return f"Cierre {self.bodega} - {self.fecha}"