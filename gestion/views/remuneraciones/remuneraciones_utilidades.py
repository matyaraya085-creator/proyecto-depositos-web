from decimal import Decimal, ROUND_HALF_UP
from gestion.models import ConfiguracionGlobal, AsignacionFamiliarConfig

def clean_currency(value):
    """Limpia cadenas de texto de símbolos de moneda, puntos de miles y comas."""
    if isinstance(value, str):
        value = value.replace('$', '').replace('.', '').replace(',', '.')
        try:
            return float(value)
        except ValueError:
            return 0.0
    return float(value) if value is not None else 0.0

def format_currency_cl(value, decimal_places=0):
    """Formatea un número a string con punto de miles y coma decimal."""
    if value is None: return ""
    try:
        if decimal_places == 0:
            formatted = f"{int(value):,}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
        else:
            formatted = f"{value:,.{decimal_places}f}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
        return formatted
    except (ValueError, TypeError):
        return str(value)

def get_parametros_calculo():
    """Carga todos los parámetros necesarios en un solo diccionario."""
    config_raw = {c.clave: Decimal(str(c.valor)) for c in ConfiguracionGlobal.objects.all().iterator()}
    
    valor_uf = config_raw.get('valor_uf', Decimal('36500')) 
    tope_imponible_clp = valor_uf * Decimal('81.6')
    
    sueldo_minimo = config_raw.get('sueldo_minimo', Decimal('460000'))
    tope_gratificacion = (sueldo_minimo * Decimal('4.75')) / Decimal('12')

    return {
        'sueldo_minimo': sueldo_minimo,
        'valor_uf': valor_uf,
        'valor_utm': config_raw.get('valor_utm', Decimal('64000')),
        'gratificacion_pct': config_raw.get('gratificacion_legal_pct', Decimal('25')) / 100,
        'tope_gratificacion': tope_gratificacion,
        'seguro_cesantia_pct': config_raw.get('seguro_cesantia_pct', Decimal('0.6')) / 100,
        'tope_imponible': tope_imponible_clp.quantize(Decimal('1'), rounding=ROUND_HALF_UP),
        'tramos_af': AsignacionFamiliarConfig.objects.all().order_by('ingreso_tope'),
    }