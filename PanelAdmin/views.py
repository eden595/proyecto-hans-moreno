from django.shortcuts import render
from .models import Recorrido   
from .models import Vehiculo
def panel_dashboard(request):
    return render(request, 'PanelAdmin/dashboard.html')


def panel_rutas(request):
    recorridos = Recorrido.objects.select_related('vehiculo', 'conductor').all()

    contexto = {
        'recorridos': recorridos,
    }
    return render(request, 'PanelAdmin/rutas.html', contexto)


def panel_vehiculos(request):
    vehiculos = Vehiculo.objects.all()
    return render(request, 'PanelAdmin/vehiculos.html', {'vehiculos': vehiculos})


def panel_combustible(request):
    return render(request, 'PanelAdmin/combustible.html')


def panel_reportes(request):
    return render(request, 'PanelAdmin/reportes.html')
