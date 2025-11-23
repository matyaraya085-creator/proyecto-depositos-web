from django.db import models

# Opciones para los campos de "bodega"
# Así nos aseguramos de que los datos sean consistentes
BODEGA_CHOICES = [
    ('Manuel Peñafiel', '1221 (Manuel Peñafiel)'),
    ('David Perry', '1225 (David Perry)'),
    ('Ambos', 'Ambos'),
]

BODEGA_FILTRO_CHOICES = [
    ('Manuel Peñafiel', '1221 (Manuel Peñafiel)'),
    ('David Perry', '1225 (David Perry)'),
]

class Trabajador(models.Model):
    """
    Traducción de tu tabla 'trabajadores'.
    El 'id' (PRIMARY KEY) lo crea Django automáticamente.
    """
    nombre = models.CharField(max_length=255, unique=True, verbose_name="Nombre Completo")
    bodega_asignada = models.CharField(max_length=100, choices=BODEGA_CHOICES, default='Ambos')

    def __str__(self):
        # Esto es para que en el panel de admin se vea el nombre
        return self.nombre

class DepositoDiario(models.Model):
    """
    Traducción de tu tabla 'gestion_diarios'.
    """
    fecha = models.DateField()
    bodega_nombre = models.CharField(max_length=100, choices=BODEGA_FILTRO_CHOICES)
    numero_lote = models.IntegerField(default=1)
    nombre_lote = models.CharField(max_length=255, blank=True, default='', verbose_name="Nombre de Lote (Opcional)")
    
    # Usamos BigIntegerField para guardar los montos en pesos (enteros)
    total_aportes = models.BigIntegerField(default=0)
    total_desglose = models.BigIntegerField(default=0, verbose_name="Total Desglose (Efectivo)")
    diferencia = models.BigIntegerField(default=0)
    total_cheques = models.BigIntegerField(default=0)
    
    cerrado = models.BooleanField(default=False, verbose_name="¿Lote Cerrado?")

    class Meta:
        # Esto reemplaza tu restricción UNIQUE(fecha, bodega_nombre, numero_lote)
        unique_together = ('fecha', 'bodega_nombre', 'numero_lote')

    def __str__(self):
        return f"{self.fecha} - {self.bodega_nombre} (Lote {self.numero_lote})"

class DepositoAporte(models.Model):
    """
    Traducción de 'gestion_aportes'.
    Usamos una ForeignKey para conectar con DepositoDiario.
    """
    # Esta es la "llave foránea". Si se borra el depósito, se borran sus aportes.
    deposito = models.ForeignKey(DepositoDiario, on_delete=models.CASCADE, related_name="aportes")
    
    # Es MUCHO mejor usar una llave foránea al trabajador
    # que solo guardar el nombre como texto.
    trabajador = models.ForeignKey(Trabajador, on_delete=models.PROTECT, verbose_name="Trabajador")
    
    monto = models.BigIntegerField(default=0)
    descripcion = models.CharField(max_length=255, blank=True, default='')

    def __str__(self):
        return f"Aporte de {self.trabajador.nombre} ({self.monto})"

class DepositoDesglose(models.Model):
    """
    Traducción de 'gestion_desglose'.
    """
    deposito = models.ForeignKey(DepositoDiario, on_delete=models.CASCADE, related_name="desglose")
    denominacion = models.CharField(max_length=50)
    valor_unitario = models.IntegerField()
    cantidad = models.IntegerField(default=0)
    total_denominacion = models.BigIntegerField(default=0)

    def __str__(self):
        return f"{self.cantidad} x {self.denominacion}"