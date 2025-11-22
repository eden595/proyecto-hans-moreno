from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import make_password
# Decorador de seguridad
from django.contrib.auth.decorators import login_required 
from django.db.models import Sum, Q, F, Max
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from .models import Usuario, Vehiculo, Recorrido, CargaCombustible
import datetime

# --- DASHBOARD ---
@login_required
def panel_dashboard(request):
    hoy = timezone.now().date()

    # KPIs
    entregas_activas_query = Recorrido.objects.filter(fecha=hoy, hora_fin__isnull=True).select_related('vehiculo', 'conductor')
    count_entregas = entregas_activas_query.count()

    datos_recorridos = Recorrido.objects.filter(kilometraje_fin__isnull=False).aggregate(
        distancia_total=Sum(F('kilometraje_fin') - F('kilometraje_inicio'))
    )
    distancia_total = datos_recorridos['distancia_total'] or 0

    datos_combustible = CargaCombustible.objects.aggregate(
        gasto_total=Sum('costo_total'),
        litros_totales=Sum('litros')
    )
    gasto_total = datos_combustible['gasto_total'] or 0
    litros_totales = datos_combustible['litros_totales'] or 0

    eficiencia = 0
    if litros_totales > 0:
        eficiencia = round(distancia_total / litros_totales, 1)

    # Gráficos
    fechas_grafico = []
    montos_grafico = []
    for i in range(6, -1, -1):
        fecha = hoy - datetime.timedelta(days=i)
        gasto_dia = CargaCombustible.objects.filter(fecha=fecha).aggregate(Sum('costo_total'))['costo_total__sum'] or 0
        fechas_grafico.append(fecha.strftime("%d/%m"))
        montos_grafico.append(gasto_dia)

    contexto = {
        'entregas_count': count_entregas,
        'entregas_lista': entregas_activas_query[:5],
        'distancia_total': distancia_total,
        'costo_combustible': gasto_total,
        'eficiencia': eficiencia,
        'fechas_chart': fechas_grafico,
        'montos_chart': montos_grafico,
    }
    return render(request, 'PanelAdmin/dashboard.html', contexto)

@login_required
def panel_conductores(request):
    # ... (filtros y búsqueda igual que antes) ...
    busqueda = request.GET.get('q')
    conductores = Usuario.objects.filter(~Q(rol__icontains='admin')).exclude(id_usuario=1).order_by('id_usuario')

    if busqueda:
        conductores = conductores.filter(nombre__icontains=busqueda)

    if request.method == "POST":
        accion = request.POST.get('accion')
        
        # --- NUEVA LÓGICA: CREAR USUARIO CON ID ORDENADO ---
        if accion == 'crear':
            try:
                nombre = request.POST.get('nombre')
                rut = request.POST.get('rut')
                correo = request.POST.get('correo')
                telefono = request.POST.get('telefono')
                clave = request.POST.get('password')
                
                if Usuario.objects.filter(rut=rut).exists():
                    messages.error(request, f"Error: El RUT {rut} ya existe.")
                elif Usuario.objects.filter(correo=correo).exists():
                    messages.error(request, f"Error: El correo {correo} ya existe.")
                else:
                    # TRUCO: Buscamos el ID más alto y le sumamos 1
                    max_id = Usuario.objects.aggregate(Max('id_usuario'))['id_usuario__max'] or 0
                    nuevo_id = max_id + 1

                    Usuario.objects.create(
                        id_usuario=nuevo_id, # <--- FORZAMOS EL NÚMERO AQUÍ
                        nombre=nombre,
                        rut=rut,
                        correo=correo,
                        telefono=telefono,
                        pin_hash=make_password(clave),
                        rol='CONDUCTOR', 
                        fecha_creacion=timezone.now()
                    )
                    messages.success(request, f"Conductor {nombre} creado con ID {nuevo_id}.")
            except Exception as e:
                messages.error(request, f"Error: {e}")

        # ... (El resto de las acciones 'deshabilitar', 'habilitar', etc. siguen igual) ...
        else:
            id_usuario = request.POST.get('id_usuario')
            usuario = get_object_or_404(Usuario, id_usuario=id_usuario)

            if accion == 'deshabilitar':
                usuario.rol = 'DESHABILITADO'
                usuario.save()
                messages.warning(request, f"Usuario {usuario.nombre} deshabilitado.")
            
            elif accion == 'habilitar':
                usuario.rol = 'CONDUCTOR'
                usuario.save()
                messages.success(request, f"Usuario {usuario.nombre} reactivado.")

            elif accion == 'actualizar_pass':
                nueva_pass = request.POST.get('new_password')
                if nueva_pass:
                    usuario.pin_hash = make_password(nueva_pass)
                    usuario.save()
                    messages.success(request, "Contraseña actualizada.")

            elif accion == 'eliminar':
                usuario.delete()
                messages.error(request, "Usuario eliminado.")
            
        return redirect('panel_conductores')

    return render(request, 'PanelAdmin/conductores.html', {'conductores': conductores})

# --- VEHÍCULOS ---
@login_required
def panel_vehiculos(request):
    vehiculos = Vehiculo.objects.all()
    conductores_disponibles = Usuario.objects.filter(rol__icontains='Conductor')

    if request.method == "POST":
        id_vehiculo = request.POST.get('id_vehiculo')
        id_conductor = request.POST.get('conductor_asignado')
        vehiculo = get_object_or_404(Vehiculo, id_vehiculo=id_vehiculo)
        
        if id_conductor:
            conductor = get_object_or_404(Usuario, id_usuario=id_conductor)
            vehiculo.conductor = conductor
        else:
            vehiculo.conductor = None
        vehiculo.save()
        messages.success(request, "Asignación actualizada.")
        return redirect('panel_vehiculos')

    return render(request, 'PanelAdmin/vehiculos.html', {
        'vehiculos': vehiculos, 
        'conductores': conductores_disponibles
    })

# --- RUTAS ---
@login_required
def panel_rutas(request):
    hoy = timezone.now().date()
    recorridos = Recorrido.objects.filter(
        fecha=hoy, 
        hora_fin__isnull=True
    ).select_related('vehiculo', 'conductor')
    return render(request, 'PanelAdmin/rutas.html', {'recorridos': recorridos})

# --- COMBUSTIBLE ---
@login_required
def panel_combustible(request):
    vehiculos = Vehiculo.objects.all()
    ultimas_cargas = CargaCombustible.objects.select_related('vehiculo').order_by('-fecha', '-hora')[:5]

    if request.method == "POST":
        try:
            id_vehiculo = request.POST.get('vehiculo')
            litros = float(request.POST.get('litros'))
            costo = int(request.POST.get('costo'))
            vehiculo_obj = get_object_or_404(Vehiculo, id_vehiculo=id_vehiculo)
            
            CargaCombustible.objects.create(
                vehiculo=vehiculo_obj,
                litros=litros,
                costo_total=costo,
                fecha=datetime.date.today(),
                hora=datetime.datetime.now().time()
            )
            messages.success(request, "Carga registrada.")
            return redirect('panel_combustible')
        except Exception:
            messages.error(request, "Error al guardar.")

    total_gasto = CargaCombustible.objects.aggregate(Sum('costo_total'))['costo_total__sum'] or 0
    total_litros = CargaCombustible.objects.aggregate(Sum('litros'))['litros__sum'] or 0
    total_registros = CargaCombustible.objects.count()
    promedio = round(total_gasto / total_litros, 1) if total_litros > 0 else 0

    contexto = {
        'vehiculos': vehiculos,
        'ultimas_cargas': ultimas_cargas,
        'kpis': {'gasto': total_gasto, 'litros': total_litros, 'promedio': promedio, 'registros': total_registros}
    }
    return render(request, 'PanelAdmin/combustible.html', contexto)

# --- REPORTES ---
@login_required
def panel_reportes(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    usuario_id = request.GET.get('usuario')
    
    recorridos = Recorrido.objects.all().select_related('conductor', 'vehiculo').order_by('-fecha')
    cargas = CargaCombustible.objects.all().select_related('vehiculo')

    if fecha_inicio:
        recorridos = recorridos.filter(fecha__gte=fecha_inicio)
        cargas = cargas.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        recorridos = recorridos.filter(fecha__lte=fecha_fin)
        cargas = cargas.filter(fecha__lte=fecha_fin)
    if usuario_id:
        recorridos = recorridos.filter(conductor_id=usuario_id)
        vehiculos_ids = recorridos.values_list('vehiculo_id', flat=True)
        cargas = cargas.filter(vehiculo_id__in=vehiculos_ids)

    total_kms = sum(r.distancia for r in recorridos if r.distancia)
    total_dinero = cargas.aggregate(Sum('costo_total'))['costo_total__sum'] or 0
    total_litros = cargas.aggregate(Sum('litros'))['litros__sum'] or 0
    usuarios = Usuario.objects.filter(~Q(rol__icontains='admin'))

    contexto = {
        'recorridos': recorridos,
        'total_kms': total_kms,
        'total_dinero': total_dinero,
        'total_litros': total_litros,
        'usuarios': usuarios,
        'filtros': {'inicio': fecha_inicio, 'fin': fecha_fin, 'user': usuario_id}
    }
    return render(request, 'PanelAdmin/reportes.html', contexto)

# --- PDF ---
@login_required
def generar_pdf_reporte(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    usuario_id = request.GET.get('usuario')
    
    recorridos = Recorrido.objects.all().select_related('conductor', 'vehiculo').order_by('-fecha')
    subtitulo = "Reporte General Histórico"

    if fecha_inicio:
        recorridos = recorridos.filter(fecha__gte=fecha_inicio)
        subtitulo = f"Desde {fecha_inicio}"
    if fecha_fin:
        recorridos = recorridos.filter(fecha__lte=fecha_fin)
        subtitulo += f" hasta {fecha_fin}"
    if usuario_id:
        recorridos = recorridos.filter(conductor_id=usuario_id)
        try:
            conductor = Usuario.objects.get(id_usuario=usuario_id)
            subtitulo += f" - Conductor: {conductor.nombre}"
        except: pass

    total_kms = sum(r.distancia for r in recorridos if r.distancia)

    contexto = {
        'recorridos': recorridos,
        'total_kms': total_kms,
        'fecha_generacion': datetime.datetime.now(),
        'subtitulo': subtitulo,
        'usuario_generador': request.user.username,
    }

    template_path = 'PanelAdmin/pdf_template.html'
    template = get_template(template_path)
    html = template.render(contexto)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_flota.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar PDF')
    return response

# --- ELIMINAR (Seguros) ---
@login_required
def eliminar_ruta(request, id):
    if request.user.is_authenticated:
        try:
            ruta = Recorrido.objects.get(id_recorrido=id)
            ruta.delete()
            messages.success(request, "Ruta eliminada.")
        except Recorrido.DoesNotExist:
            messages.error(request, "Ruta no existe.")
    return redirect('panel_rutas')

@login_required
def eliminar_combustible(request, id):
    if request.user.is_authenticated:
        try:
            carga = CargaCombustible.objects.get(id_carga=id)
            carga.delete()
            messages.success(request, "Registro eliminado.")
        except CargaCombustible.DoesNotExist:
            messages.error(request, "Registro no existe.")
    return redirect('panel_combustible')