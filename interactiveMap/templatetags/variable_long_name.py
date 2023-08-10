from django import template

register = template.Library()

@register.filter(name="long_name")
def long_name(var):
    """Returns the full name of the meteorological variable, given the short name string."""
    if var == 'temp':
        return 'Temperature'
    elif var == 'rel_hum':
        return 'Relative Humidity'
    elif var == 'spec_hum':
        return 'Specific Humidity'
    elif var == 'tcc':
        return 'Total Cloud Cover'
    elif var == 'u_wind':
        return 'U-Component of Wind'
    elif var == 'v_wind':
        return 'V-Component of Wind'
    elif var == 'gust':
        return 'Wind Speed (Gust)'
    elif var == 'pwat':
        return 'Precipitable Water'
    else:
        return 'Wrong value'
