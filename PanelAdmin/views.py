from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required 
from django.views.decorators.csrf import csrf_exempt 
from django.db.models import Sum, Q, F, Max, ProtectedError 
from django.utils import timezone
from django.http import HttpResponse, JsonResponse 
from django.template.loader import get_template 
from xhtml2pdf import pisa 
import datetime
import json

from .models import Usuario, Vehiculo, Recorrido, CargaCombustible

# --- DASHBOARD ---
@login_required
def panel_dashboard(request):
    hoy = timezone.now().date()

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

# --- CONDUCTORES ---
@login_required
def panel_conductores(request):
    busqueda = request.GET.get('q')
    conductores = Usuario.objects.filter(~Q(rol__icontains='admin')).exclude(id_usuario=1).order_by('id_usuario')

    if busqueda:
        conductores = conductores.filter(nombre__icontains=busqueda)

    if request.method == "POST":
        accion = request.POST.get('accion')
        
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
                    max_id = Usuario.objects.aggregate(Max('id_usuario'))['id_usuario__max'] or 0
                    nuevo_id = max_id + 1

                    Usuario.objects.create(
                        id_usuario=nuevo_id,
                        nombre=nombre,
                        rut=rut,
                        correo=correo,
                        telefono=telefono,
                        pin_hash=make_password(clave),
                        rol='CONDUCTOR',
                        fecha_creacion=timezone.now()
                    )
                    messages.success(request, f"Conductor {nombre} creado correctamente.")
            except Exception as e:
                messages.error(request, f"Error inesperado: {e}")

        else:
            id_usuario = request.POST.get('id_usuario')
            usuario = get_object_or_404(Usuario, id_usuario=id_usuario)

            if accion == 'deshabilitar':
                # INTEGRIDAD: Si deshabilitas a un conductor, quítale el auto si tiene uno asignado
                Vehiculo.objects.filter(conductor=usuario).update(conductor=None)
                
                usuario.rol = 'DESHABILITADO'
                usuario.save()
                messages.warning(request, "Usuario deshabilitado y desvinculado de vehículos.")
            
            elif accion == 'habilitar':
                usuario.rol = 'CONDUCTOR'
                usuario.save()
                messages.success(request, "Usuario reactivado.")
            
            elif accion == 'actualizar_pass':
                nueva_pass = request.POST.get('new_password')
                if nueva_pass:
                    usuario.pin_hash = make_password(nueva_pass)
                    usuario.save()
                    messages.success(request, "Contraseña actualizada.")
            
            elif accion == 'eliminar':
                # INTEGRIDAD: Antes de borrar al usuario, liberamos cualquier auto que tenga asignado
                # para evitar errores de base de datos o autos con conductores fantasmas.
                Vehiculo.objects.filter(conductor=usuario).update(conductor=None)
                
                usuario.delete()
                messages.error(request, "Usuario eliminado y vehículos liberados.")
            
        return redirect('panel_conductores')

    return render(request, 'PanelAdmin/conductores.html', {'conductores': conductores})

# --- VEHÍCULOS ---
@login_required
def panel_vehiculos(request):
    vehiculos = Vehiculo.objects.select_related('conductor').all().order_by('id_vehiculo') 
    conductores_disponibles = Usuario.objects.filter(rol__icontains='CONDUCTOR').order_by('nombre')

    if request.method == "POST":
        accion = request.POST.get('accion')
        id_vehiculo = request.POST.get('id_vehiculo')
        
        if accion == 'crear':
            # INTEGRIDAD: Normalizamos la patente a Mayúsculas
            patente = request.POST.get('patente').upper().strip()
            modelo = request.POST.get('modelo')
            kilometraje = request.POST.get('kilometraje')
            
            if Vehiculo.objects.filter(patente=patente).exists():
                messages.error(request, f"Error: La patente {patente} ya existe.")
            else:
                Vehiculo.objects.create(
                    patente=patente, modelo=modelo, kilometraje=kilometraje, fecha_creacion=timezone.now()
                )
                messages.success(request, "Vehículo creado.")
        
        elif accion == 'eliminar':
            try:
                vehiculo = Vehiculo.objects.get(id_vehiculo=id_vehiculo)
                vehiculo.delete()
                messages.error(request, "Vehículo eliminado.") 
            except ProtectedError:
                messages.error(request, "No se puede eliminar: tiene historial asociado.")
        
        elif accion == 'asignar': 
            id_conductor = request.POST.get('conductor_asignado')
            vehiculo = get_object_or_404(Vehiculo, id_vehiculo=id_vehiculo)
            
            if id_conductor:
                conductor = get_object_or_404(Usuario, id_usuario=id_conductor)
                
                # INTEGRIDAD: Verificar si este conductor YA tiene otro auto asignado
                # Si es así, se lo quitamos (lo "bajamos" del auto viejo para subirlo al nuevo)
                autos_anteriores = Vehiculo.objects.filter(conductor=conductor).exclude(id_vehiculo=vehiculo.id_vehiculo)
                if autos_anteriores.exists():
                    autos_anteriores.update(conductor=None)
                    messages.warning(request, f"El conductor {conductor.nombre} fue desvinculado de sus otros vehículos.")

                vehiculo.conductor = conductor
            else:
                vehiculo.conductor = None
                
            vehiculo.save()
            messages.success(request, f"Asignación actualizada para {vehiculo.patente}.")
            
        return redirect('panel_vehiculos')

    return render(request, 'PanelAdmin/vehiculos.html', {
        'vehiculos': vehiculos, 'conductores': conductores_disponibles
    })

# --- RUTAS ---
@login_required
def panel_rutas(request):
    hoy = timezone.now().date()
    recorridos = Recorrido.objects.filter(fecha=hoy, hora_fin__isnull=True).select_related('vehiculo', 'conductor')
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
            
            # Validaciones básicas
            if litros <= 0 or costo <= 0:
                raise ValueError("Valores deben ser positivos")

            CargaCombustible.objects.create(
                vehiculo=vehiculo_obj, litros=litros, costo_total=costo,
                fecha=datetime.date.today(), hora=datetime.datetime.now().time()
            )
            messages.success(request, "Carga registrada.")
            return redirect('panel_combustible')
        except Exception as e:
            messages.error(request, f"Error al guardar: {e}")

    # KPIs
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

# --- REPORTES Y PDF ---
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
        'recorridos': recorridos, 'total_kms': total_kms, 'total_dinero': total_dinero,
        'total_litros': total_litros, 'usuarios': usuarios,
        'filtros': {'inicio': fecha_inicio, 'fin': fecha_fin, 'user': usuario_id}
    }
    return render(request, 'PanelAdmin/reportes.html', contexto)

@login_required
def generar_pdf_reporte(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    usuario_id = request.GET.get('usuario')
    
    recorridos = Recorrido.objects.all().select_related('conductor', 'vehiculo').order_by('-fecha')
    subtitulo = "Reporte General Histórico"

    if fecha_inicio: recorridos = recorridos.filter(fecha__gte=fecha_inicio); subtitulo = f"Desde {fecha_inicio}"
    if fecha_fin: recorridos = recorridos.filter(fecha__lte=fecha_fin); subtitulo += f" hasta {fecha_fin}"
    if usuario_id: recorridos = recorridos.filter(conductor_id=usuario_id)

    total_kms = sum(r.distancia for r in recorridos if r.distancia)

    contexto = {
        'recorridos': recorridos, 'total_kms': total_kms,
        'fecha_generacion': datetime.datetime.now(), 'subtitulo': subtitulo,
        'usuario_generador': request.user.username,
    }
    template = get_template('PanelAdmin/pdf_template.html')
    html = template.render(contexto)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err: return HttpResponse('Error PDF')
    return response

# --- ELIMINAR ---
@login_required
def eliminar_ruta(request, id):
    if request.user.is_authenticated:
        try:
            Recorrido.objects.get(id_recorrido=id).delete()
            messages.success(request, "Ruta eliminada.")
        except: messages.error(request, "Error al eliminar.")
    return redirect('panel_rutas')

@login_required
def eliminar_combustible(request, id):
    if request.user.is_authenticated:
        try:
            CargaCombustible.objects.get(id_carga=id).delete()
            messages.success(request, "Registro eliminado.")
        except: messages.error(request, "Error al eliminar.")
    return redirect('panel_combustible')

# --- API GPS ---
@csrf_exempt 
def update_gps_location(request):
    if request.method == 'POST':
        try:
            # INTENTO 1: Leer datos como JSON (Estándar para Apps Android)
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                # INTENTO 2: Leer como Formulario Web (Por si acaso)
                data = request.POST
            
            patente_app = data.get('patente')
            latitud_app = data.get('latitud')
            longitud_app = data.get('longitud')
            
            # Validación básica
            if not patente_app:
                return JsonResponse({'status': 'error', 'message': 'Falta la patente'}, status=400)

            # 1. Buscamos el vehículo
            vehiculo = Vehiculo.objects.get(patente=patente_app)
            
            # 2. Actualizamos las coordenadas
            vehiculo.latitud = latitud_app
            vehiculo.longitud = longitud_app
            vehiculo.save()
            
            return JsonResponse({'status': 'success', 'message': 'Ubicación actualizada'}, status=200)
            
        except Vehiculo.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': f'Patente {patente_app} no encontrada'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error interno: {e}'}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)