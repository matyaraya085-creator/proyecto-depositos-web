from django.db import models
from datetime import date, datetime

# Opciones para bodegas (Lo que ya tenías)
BODEGA_CHOICES = [
    ('1221', '1221 (Manuel Peñafiel)'),
    ('1225', '1225 (David Perry)'),
    ('Ambos', 'Ambos'),
]

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
    tramo = models.CharField(max_length=1) # A, B, C, D
    ingreso_tope = models.IntegerField()
    monto_por_carga = models.IntegerField()

    def __str__(self):
        return f"Tramo {self.tramo} - ${self.monto_por_carga}"

# ==========================================================
# 3. TRABAJADOR (Actualizado con datos de remuneración)
# ==========================================================
class Trabajador(models.Model):
    # Datos Personales
    nombre = models.CharField(max_length=255, verbose_name="Nombre Completo")
    rut = models.CharField(max_length=12, unique=True, null=True, verbose_name="RUT") # Nuevo campo
    
    # Datos Operativos
    bodega_asignada = models.CharField(max_length=100, choices=BODEGA_CHOICES, default='Ambos')
    cargo = models.CharField(max_length=100, default="Operario", null=True, blank=True)
    fecha_ingreso = models.DateField(null=True, blank=True)
    
    # Datos Remuneración
    sueldo_base = models.IntegerField(default=460000, verbose_name="Sueldo Base")
    valor_hora_extra = models.IntegerField(default=0, verbose_name="Valor Hora Extra")
    
    # Relaciones con Configuración (Foreign Keys son mejores que texto plano)
    afp = models.ForeignKey(AfpConfig, on_delete=models.SET_NULL, null=True, blank=True)
    salud = models.ForeignKey(SaludConfig, on_delete=models.SET_NULL, null=True, blank=True)
    
    cargas_familiares = models.IntegerField(default=0, verbose_name="N° Cargas")
    tiene_asignacion_familiar = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nombre} ({self.rut})"

# ==========================================================
# 4. REMUNERACIÓN (Historial de Pagos)
# ==========================================================
class Remuneracion(models.Model):
    trabajador = models.ForeignKey(Trabajador, on_delete=models.CASCADE)
    periodo = models.CharField(max_length=7) # Formato "2023-10"
    fecha_calculo = models.DateTimeField(auto_now_add=True)
    
    # Resumen de montos
    sueldo_liquido = models.IntegerField()
    total_haberes = models.IntegerField()
    total_descuentos = models.IntegerField()
    
    # Guardamos todo el detalle (cálculos intermedios) en un JSON para poder 
    # regenerar la liquidación exacta aunque cambien los parámetros después.
    detalle_json = models.JSONField(verbose_name="Detalle Completo JSON")

    class Meta:
        # Evitar calcular dos veces el mismo sueldo para el mismo mes
        unique_together = ('trabajador', 'periodo')
        ordering = ['-periodo']

    def __str__(self):
        return f"{self.trabajador.nombre} - {self.periodo} - ${self.sueldo_liquido}"

# ==========================================================
# MODELOS ANTERIORES (Caja y Vehículos) - NO TOCAR
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
    updated_at = models.DateTimeField(auto_now=True) # Campo nuevo útil para saber cuándo se cerró

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
# MODELOS DE FLUJO POR TRABAJADOR (Rendición Diaria)
# ==========================================================
class RendicionDiaria(models.Model):
    """Almacena la rendición diaria de caja de un trabajador específico."""
    trabajador = models.ForeignKey(Trabajador, on_delete=models.CASCADE, verbose_name="Trabajador")
    fecha = models.DateField(default=date.today)
    
    # Venta de Valores Rendidos
    # Nota: Usamos BigIntegerField para los montos, como en DepositoDiario
    credito_empresa = models.BigIntegerField(default=0, verbose_name="Crédito Lipigas")
    prepago_vales = models.BigIntegerField(default=0, verbose_name="Vales Prepago")
    transbank = models.BigIntegerField(default=0, verbose_name="Transbank/Tarjeta")
    efectivo_entregado = models.BigIntegerField(default=0, verbose_name="Efectivo Entregado")

    # Venta de Cilindros (Ejemplo: Campos de la venta por tipo de gas)
    gas_5kg_cant = models.IntegerField(default=0)
    gas_11kg_cant = models.IntegerField(default=0)
    gas_45kg_cant = models.IntegerField(default=0)
    cilindros_defectuosos = models.IntegerField(default=0)

    # Resultado del Flujo (Cálculo)
    venta_esperada = models.BigIntegerField(default=0, help_text="Monto total que el trabajador debía rendir (Venta * Precio)")
    balance_flujo = models.BigIntegerField(default=0, help_text="Diferencia: (Rendido - Esperado)")
    
    class Meta:
        # Asegura que solo haya una rendición por trabajador por día
        unique_together = ('trabajador', 'fecha')
        verbose_name = "Rendición Diaria"
        verbose_name_plural = "Rendiciones Diarias"

    def __str__(self):
        return f"Rendición de {self.trabajador.nombre} - {self.fecha}"