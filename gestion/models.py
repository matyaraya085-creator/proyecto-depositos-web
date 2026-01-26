from django.db import models
from datetime import date, datetime
from django.contrib.auth.models import User

# Opciones para bodegas (Usadas en Trabajadores)
BODEGA_CHOICES = [
    ('1221', '1221 (Manuel Peñafiel)'),
    ('1225', '1225 (David Perry)'),
    ('Ambos', 'Ambos'),
]

# Opciones estrictas para facturación (Solo las físicas)
BODEGA_FACTURACION_CHOICES = [
    ('1221', '1221 (Manuel Peñafiel)'),
    ('1225', '1225 (David Perry)'),
]

# Opciones para filtros y depósitos (Usadas en DepositoDiario)
BODEGA_FILTRO_CHOICES = [
    ('Manuel Peñafiel', '1221 (Manuel Peñafiel)'),
    ('David Perry', '1225 (David Perry)'),
]

# ==========================================================
# 1. CONFIGURACIÓN GLOBAL
# ==========================================================
class ConfiguracionGlobal(models.Model):
    clave = models.CharField(max_length=50, unique=True)
    valor = models.FloatField()
    descripcion = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.descripcion}: {self.valor}"

# ==========================================================
# 2. TABLAS PREVISIONALES
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
    TIPO_CHOICES = [
        ('INTERNO', 'Interno (Contrato)'),
        ('EXTERNO', 'Externo (Fletero/Apoyo)'),
    ]

    nombre = models.CharField(max_length=255, verbose_name="Nombre Completo")
    rut = models.CharField(max_length=12, unique=True, null=True, verbose_name="RUT")
    
    # --- NUEVOS CAMPOS ---
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='INTERNO', verbose_name="Tipo Trabajador")
    activo = models.BooleanField(default=True, verbose_name="¿Trabaja Actualmente?")
    filtro_trabajador = models.BooleanField(default=False, verbose_name="¿Habilitado en Filtros?")

    bodega_asignada = models.CharField(max_length=100, choices=BODEGA_CHOICES, default='Ambos')
    
    bodega_facturacion = models.CharField(
        max_length=10, 
        choices=BODEGA_FACTURACION_CHOICES, 
        null=True, 
        blank=True,
        verbose_name="Bodega de Facturación"
    )

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
# 4. REMUNERACIÓN (INTERNOS)
# ==========================================================
class Remuneracion(models.Model):
    trabajador = models.ForeignKey(Trabajador, on_delete=models.PROTECT)
    periodo = models.CharField(max_length=7) 
    fecha_calculo = models.DateTimeField(auto_now_add=True)
    
    sueldo_liquido = models.IntegerField()
    total_haberes = models.IntegerField()
    total_descuentos = models.IntegerField()
    
    # Nuevos campos específicos para lógica estricta
    monto_impuesto = models.IntegerField(default=0, verbose_name="Impuesto Único")
    monto_faltante = models.IntegerField(default=0, verbose_name="Faltante Caja")
    monto_anticipo = models.IntegerField(default=0, verbose_name="Anticipos del Mes")

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
    fecha_extintor = models.DateField(null=True, blank=True, verbose_name="Venc. Extintor")
    
    # DATOS KILOMETRAJE
    kilometraje_actual = models.IntegerField(default=0, verbose_name="Último KM Reportado (Base)")
    fecha_reporte_km = models.DateField(default=date.today, verbose_name="Fecha del Reporte KM")
    
    kilometraje_maximo = models.IntegerField(default=0, verbose_name="KM Máximo (Mantención)")
    km_diarios = models.FloatField(default=0.0, verbose_name="Promedio KM Diarios")
    dias_uso_semanal = models.IntegerField(default=5, verbose_name="Días uso semana")

    def __str__(self):
        return f"{self.patente}"
    
    @property
    def kilometraje_estimado(self):
        """
        Calcula el KM actual proyectando el uso diario desde la última fecha de reporte.
        Fórmula: KM Base + (Días transcurridos * KM Promedio Efectivo)
        """
        if not self.fecha_reporte_km:
            return self.kilometraje_actual
            
        dias_pasados = (date.today() - self.fecha_reporte_km).days
        
        if dias_pasados < 0:
            dias_pasados = 0
            
        # Ajustamos el promedio diario según los días reales de uso a la semana
        # Ejemplo: Si se usa 100km diarios pero solo 3 días a la semana:
        # (100 * 3) / 7 = 42.8 km promedio real por día calendario
        factor_uso = self.dias_uso_semanal / 7.0
        km_efectivos_diarios = self.km_diarios * factor_uso
        
        km_ganados = dias_pasados * km_efectivos_diarios
        
        return int(self.kilometraje_actual + km_ganados)

    def get_alertas(self):
        # NOTA: Este método se mantiene por compatibilidad, pero la lógica fuerte
        # de alertas ahora reside en camionetas.py usando el KM Estimado.
        return []

# ==========================================================
# 6. MÓDULO DE FLUJO POR TRABAJADOR (RENDICIÓN)
# ==========================================================
class RendicionDiaria(models.Model):
    trabajador = models.ForeignKey(Trabajador, on_delete=models.PROTECT, verbose_name="Trabajador")
    fecha = models.DateField(default=date.today)
    bodega = models.CharField(max_length=10, default='1221', verbose_name="Bodega del Turno")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cerrado = models.BooleanField(default=False, verbose_name="¿Rendición Cerrada?")

    # --- 1. DETALLE DE CILINDROS ---
    gas_5kg = models.IntegerField(default=0, verbose_name="Lipigas 5kg")
    gas_11kg = models.IntegerField(default=0, verbose_name="Lipigas 11kg")
    gas_15kg = models.IntegerField(default=0, verbose_name="Lipigas 15kg")
    gas_45kg = models.IntegerField(default=0, verbose_name="Lipigas 45kg")
    
    gasc_5kg = models.IntegerField(default=0, verbose_name="Cat 5kg (05 Cat)")
    gasc_15kg = models.IntegerField(default=0, verbose_name="Cat 15kg (15 Cat)")
    gas_ultra_15kg = models.IntegerField(default=0, verbose_name="Ultra 15kg")

    cilindros_defectuosos = models.IntegerField(default=0)
    total_kilos = models.FloatField(default=0.0, help_text="Suma de Kilos Vendidos")

    # --- 2. RENDICIÓN DE VALORES (CAJA) ---
    total_venta = models.BigIntegerField(default=0, verbose_name="Total Venta (Guía)")

    monto_credito = models.BigIntegerField(default=0, verbose_name="Crédito Empresa") 
    monto_vales = models.BigIntegerField(default=0, verbose_name="Vales/Prepago")
    monto_transbank = models.BigIntegerField(default=0, verbose_name="Transbank")
    
    # --- GASTOS Y ANTICIPOS ---
    gasto_total = models.IntegerField(default=0, verbose_name="Total Gastos")
    detalle_gastos = models.TextField(default='[]', verbose_name="JSON Detalle Gastos")
    monto_anticipo = models.IntegerField(default=0, verbose_name="Anticipo")

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
# 7. CONFIGURACIÓN DE COMISIONES
# ==========================================================
class TarifaComision(models.Model):
    nombre = models.CharField(max_length=100, default="Tarifa Estándar")
    
    tarifa_5kg = models.IntegerField(default=0, verbose_name="Tarifa 5kg")
    tarifa_11kg = models.IntegerField(default=0, verbose_name="Tarifa 11kg")
    tarifa_15kg = models.IntegerField(default=0, verbose_name="Tarifa 15kg")
    tarifa_45kg = models.IntegerField(default=0, verbose_name="Tarifa 45kg")
    
    tarifa_cat_5kg = models.IntegerField(default=0, verbose_name="Tarifa Cat 5kg")
    tarifa_cat_15kg = models.IntegerField(default=0, verbose_name="Tarifa Cat 15kg")
    tarifa_ultra_15kg = models.IntegerField(default=0, verbose_name="Tarifa Ultra 15kg")

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} (Actua.: {self.updated_at.strftime('%d/%m/%Y')})"

# ==========================================================
# 8. CONTROL DE CIERRE DIARIO
# ==========================================================
class CierreDiario(models.Model):
    fecha = models.DateField()
    bodega = models.CharField(max_length=10, choices=BODEGA_CHOICES)
    cerrado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('fecha', 'bodega')
        verbose_name = "Cierre Diario Global"

    def __str__(self):
        return f"Cierre {self.bodega} - {self.fecha}"
    
# ==========================================================
# 9. CONFIGURACIÓN DE PLANTILLAS
# ==========================================================
class PlantillaLiquidacion(models.Model):
    nombre = models.CharField(max_length=100, default="Plantilla Oficial")
    archivo = models.FileField(upload_to='plantillas/remuneraciones/')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Plantilla actualizada al {self.updated_at}"
    
# ==========================================================
# 10. REMUNERACIONES EXTERNOS (SIN PRÉSTAMO)
# ==========================================================
class RemuneracionExterna(models.Model):
    trabajador = models.ForeignKey('Trabajador', on_delete=models.CASCADE, related_name='remuneraciones_externas')
    mes = models.IntegerField()
    anio = models.IntegerField()
    fecha_emision = models.DateField(auto_now_add=True)
    
    # Encabezado
    nro_factura = models.CharField(max_length=50, verbose_name="Número de Factura", blank=True, null=True)
    
    # --- INGRESOS ---
    pago_cilindros = models.IntegerField(default=0, verbose_name="Pago por Cilindros")
    asistencia_tecnica = models.IntegerField(default=0, verbose_name="Asistencia Técnica")
    
    # Impuestos
    subtotal_neto = models.IntegerField(default=0)
    iva = models.IntegerField(default=0)
    total_bruto = models.IntegerField(default=0) # Neto + IVA (Total Ingresos)
    
    # --- DESCUENTOS ---
    # 1. Anticipos
    anticipo_base = models.IntegerField(default=0, verbose_name="Anticipo DB (Rendiciones)")
    anticipo_extra = models.IntegerField(default=0, verbose_name="Anticipo Manual Extra")
    
    # 2. Faltantes
    faltante_base = models.IntegerField(default=0, verbose_name="Faltante DB (Rendiciones)")
    faltante_extra = models.IntegerField(default=0, verbose_name="Faltante Manual Extra")
    
    # 3. Otros Descuentos (Lista Dinámica)
    json_otros_descuentos = models.TextField(default='[]', verbose_name="JSON Lista Descuentos")
    total_otros_descuentos = models.IntegerField(default=0)
    
    # --- FINAL ---
    total_descuentos = models.IntegerField(default=0)
    monto_total_pagar = models.IntegerField(default=0) # Puede ser negativo (Deuda)
    
    # Metadata
    json_detalle_cilindros = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Remuneración Externa"
        unique_together = ('trabajador', 'mes', 'anio')

    def __str__(self):
        return f"Factura {self.nro_factura} - {self.trabajador.nombre} ({self.mes}/{self.anio})"

# ==========================================================
# 11. CLIENTES CRÉDITO Y FACTURAS
# ==========================================================
class ClienteCredito(models.Model):
    nombre_razon_social = models.CharField(max_length=255, verbose_name="Razón Social / Nombre")
    apodo = models.CharField(max_length=100, blank=True, null=True, verbose_name="Apodo / Contacto")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre_razon_social} ({self.apodo or 'Sin apodo'})"

class FacturaCredito(models.Model):
    cliente = models.ForeignKey(ClienteCredito, on_delete=models.CASCADE, related_name="facturas")
    
    # DATOS DE LA FACTURA (OPCIONALES AL INICIO)
    numero_factura = models.CharField(max_length=100, verbose_name="N° Factura", null=True, blank=True)
    valor = models.IntegerField(verbose_name="Monto Total", default=0, null=True, blank=True)
    
    # Set null para permitir quitar fletero si es necesario
    fletero = models.ForeignKey('Trabajador', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Fletero Responsable")
    
    # FECHA DE EMISIÓN (CUANDO SE GENERA LA DEUDA)
    fecha_pago = models.DateField(verbose_name="Fecha Emisión") 
    
    # PAGO (SIN EVIDENCIA VISUAL)
    fecha_real_pago = models.DateField(verbose_name="Fecha Real de Pago", null=True, blank=True)
    pagado = models.BooleanField(default=False, verbose_name="¿Pagado?")
    
    # NUEVO: NOTA DE PAGO
    nota_pago = models.TextField(verbose_name="Nota de Pago", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_pago']

    def __str__(self):
        return f"Fac: {self.numero_factura or 'S/N'} - ${self.valor or 0}"