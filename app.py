import os
import base64
from flask import Flask, render_template, request, make_response, redirect, url_for
from xhtml2pdf import pisa
from io import BytesIO

# Importamos nuestra base de datos y los modelos
from models import db, User, Empresa, Cliente, Cotizacion, CotizacionItem

app = Flask(__name__)

# Configuración de la base de datos (Usaremos SQLite localmente por ahora)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cotizador.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializamos la BD con nuestra app
db.init_app(app)

# Creamos las tablas automáticamente si no existen
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

# --- RUTA PARA EMPRESAS ---
@app.route('/empresas', methods=['GET', 'POST'])
def gestionar_empresas():
    usuario_id_actual = 1 # Simulamos al usuario activo
    
    # Si el usuario envió el formulario para guardar una nueva empresa
    if request.method == 'POST':
        nueva_empresa = Empresa(
            id_user=usuario_id_actual,
            nombre_comercial_empresa=request.form.get('nombre_comercial'),
            razon_social_empresa=request.form.get('razon_social'),
            rfc_empresa=request.form.get('rfc'),
            cp_empresa=request.form.get('cp'),                    # <-- NUEVO
            telefono1_empresa=request.form.get('telefono1'),      # <-- ACTUALIZADO
            telefono2_empresa=request.form.get('telefono2'),      # <-- NUEVO
            email_empresa=request.form.get('correo')
        )
        db.session.add(nueva_empresa)
        db.session.commit()
        return redirect(url_for('gestionar_empresas')) # Recarga la página
    
    # Si solo está visitando la página, mostramos la lista
    mis_empresas = Empresa.query.filter_by(id_user=usuario_id_actual).all()
    return render_template('empresas.html', empresas=mis_empresas)

@app.route('/empresas/editar/<int:id_empresa>', methods=['GET', 'POST'])
def editar_empresa(id_empresa):
    # Buscamos la empresa en la base de datos
    empresa = Empresa.query.get_or_404(id_empresa)
    
    # Si el usuario hace clic en "Guardar Cambios"
    if request.method == 'POST':
        empresa.nombre_comercial_empresa = request.form.get('nombre_comercial')
        empresa.razon_social_empresa = request.form.get('razon_social')
        empresa.rfc_empresa = request.form.get('rfc')
        empresa.cp_empresa = request.form.get('cp')
        empresa.telefono1_empresa = request.form.get('telefono1')
        empresa.telefono2_empresa = request.form.get('telefono2')
        empresa.email_empresa = request.form.get('correo')
        
        # Guardamos la actualización
        db.session.commit()
        return redirect(url_for('gestionar_empresas'))
    
    # Si entra por el enlace, mostramos el formulario
    return render_template('editar_empresa.html', empresa=empresa)

# --- RUTA PARA CLIENTES ---
@app.route('/clientes', methods=['GET', 'POST'])
def gestionar_clientes():
    usuario_id_actual = 1 
    
    if request.method == 'POST':
        es_sa_booleano = True if request.form.get('es_sa') == 'on' else False
        nuevo_cliente = Cliente(
            id_user=usuario_id_actual,
            razon_social_cliente=request.form.get('razon_social'),
            es_sa_cliente=es_sa_booleano,
            nombre_contacto_cliente=request.form.get('contacto'),
            rfc_cliente=request.form.get('rfc'),
            cp_cliente=request.form.get('cp'),                    # <-- NUEVO
            telefono1_cliente=request.form.get('telefono1'),      # <-- ACTUALIZADO
            telefono2_cliente=request.form.get('telefono2'),      # <-- NUEVO
            email_cliente=request.form.get('correo'),
            direccion_fiscal_cliente=request.form.get('direccion_fiscal'),  # <-- ACTUALIZADO
            direccion_entrega_cliente=request.form.get('direccion_entrega') # <-- NUEVO
        )
        db.session.add(nuevo_cliente)
        db.session.commit()
        return redirect(url_for('gestionar_clientes'))
    
    mis_clientes = Cliente.query.filter_by(id_user=usuario_id_actual).all()
    return render_template('clientes.html', clientes=mis_clientes)

@app.route('/clientes/editar/<int:id_cliente>', methods=['GET', 'POST'])
def editar_cliente(id_cliente):
    # Buscamos al cliente en la base de datos por su ID
    cliente = Cliente.query.get_or_404(id_cliente)
    
    # Si el usuario hace clic en "Guardar Cambios"
    if request.method == 'POST':
        cliente.razon_social_cliente = request.form.get('razon_social')
        cliente.es_sa_cliente = True if request.form.get('es_sa') == 'on' else False
        cliente.nombre_contacto_cliente = request.form.get('contacto')
        cliente.rfc_cliente = request.form.get('rfc')
        cliente.cp_cliente = request.form.get('cp')
        cliente.telefono1_cliente = request.form.get('telefono1')
        cliente.telefono2_cliente = request.form.get('telefono2')
        cliente.email_cliente = request.form.get('correo')
        cliente.direccion_fiscal_cliente = request.form.get('direccion_fiscal')
        cliente.direccion_entrega_cliente = request.form.get('direccion_entrega')
        
        # Guardamos la actualización
        db.session.commit()
        return redirect(url_for('gestionar_clientes'))
    
    # Si solo está entrando a la página, mostramos el formulario
    return render_template('editar_cliente.html', cliente=cliente)

@app.route('/cotizaciones')
def gestionar_cotizaciones():
    # 1. Traemos las Abiertas
    abiertas = Cotizacion.query.filter_by(estatus_cotizacion='Abierta').order_by(Cotizacion.fecha_emision.desc()).all()
    
    # 2. Traemos las que están En Proceso
    en_proceso = Cotizacion.query.filter_by(estatus_cotizacion='En proceso').order_by(Cotizacion.fecha_emision.desc()).all()
    
    # 3. Traemos las Declinadas
    declinadas = Cotizacion.query.filter_by(estatus_cotizacion='Declinada').order_by(Cotizacion.fecha_emision.desc()).all()
    
    # 4. Traemos las Pagadas
    pagadas = Cotizacion.query.filter_by(estatus_cotizacion='Pagada').order_by(Cotizacion.fecha_emision.desc()).all()
    
    # Enviamos las 4 listas a la página HTML
    return render_template('cotizaciones.html', 
                           abiertas=abiertas, 
                           en_proceso=en_proceso, 
                           declinadas=declinadas,
                           pagadas=pagadas)

@app.route('/cotizador')
def mostrar_cotizador():
    # Simulamos que el usuario logueado es el ID 1
    usuario_id_actual = 1
    
    # Consultamos la base de datos
    mis_empresas = Empresa.query.filter_by(id_user=usuario_id_actual).all()
    mis_clientes = Cliente.query.filter_by(id_user=usuario_id_actual).all()
    
    # Enviamos los datos al HTML
    return render_template('cotizador.html', empresas=mis_empresas, clientes=mis_clientes)

@app.route('/generar', methods=['POST'])
def generar_pdf():
    if request.method == 'POST':
        
        # --- NUEVO: Procesar el Logotipo ---
        logo_base64 = None
        archivo_logo = request.files.get('logotipo')
        if archivo_logo and archivo_logo.filename != '':
            # Leemos la imagen y la convertimos a código base64
            mime_type = archivo_logo.mimetype
            logo_data = base64.b64encode(archivo_logo.read()).decode('utf-8')
            # Creamos la cadena que el HTML puede leer como imagen
            logo_base64 = f"data:{mime_type};base64,{logo_data}"

        # 1. Recolectar datos de la Empresa
        empresa = {
            'nombre_comercial': request.form.get('empresa_nombre_comercial'),
            'razon_social': request.form.get('empresa_razon_social'),
            'rfc': request.form.get('empresa_rfc'),
            'cp': request.form.get('empresa_cp'),
            'telefono': request.form.get('empresa_telefono'),
            'correo': request.form.get('empresa_correo')
        }

        # 2. Recolectar datos del Cliente
        cliente = {
            'numero_cotizacion': request.form.get('numero_cotizacion', 'COT-000'),
            'nombre': request.form.get('cliente_nombre'),
            'atencion': request.form.get('cliente_atencion'),
            'rfc': request.form.get('cliente_rfc'),
            'correo': request.form.get('cliente_correo'),
            'direccion': request.form.get('cliente_direccion'),
            'telefono1': request.form.get('cliente_telefono1'),
            'telefono2': request.form.get('cliente_telefono2'),
            'entrega': request.form.get('cliente_direccion_entrega', 'Por definir')
        }

        # 3. Recolectar Artículos
        items = request.form.getlist('item')
        descripciones = request.form.getlist('descripcion')
        costos_unitarios = request.form.getlist('costo_unitario')
        cantidades = request.form.getlist('cantidad')
        costos_finales = request.form.getlist('costo_final')

        articulos = []
        for i in range(len(items)):
            articulos.append({
                'no_item': i + 1,
                'item': items[i],
                'descripcion': descripciones[i],
                'costo_unitario': costos_unitarios[i],
                'cantidad': cantidades[i],
                'costo_final': costos_finales[i]
            })

        # 4. Totales y Cláusulas
        totales = {
            'subtotal': request.form.get('subtotal'),
            'iva': request.form.get('iva'),
            'aplicar_isr': request.form.get('aplicar_isr'),
            'retencion_isr': request.form.get('retencion_isr'),
            'total': request.form.get('total')
        }
        clausulas = request.form.get('clausulas')


        # ---------------------------------------------------------
        # 4. GUARDAR EN LA BASE DE DATOS
        # ---------------------------------------------------------
        # (Asegúrate de que el select de tu formulario HTML tenga el name="id_cliente")
        cliente_id = request.form.get('id_cliente') 
        
        # Si el usuario seleccionó un cliente de la lista, guardamos la cotización
        if cliente_id:
            try:
                # 4.1 Crear el registro principal de la Cotización
                # --- NUEVA LÓGICA DE FOLIO DINÁMICO ---
                # 1. Traemos la información de la Empresa y el Cliente
                empresa_db = Empresa.query.get(1) # Temporal: Empresa 1
                cliente_db = Cliente.query.get(cliente_id)
                
                # 2. Extraemos las primeras 2 letras, quitamos espacios y pasamos a mayúsculas
                # Nota: Ajusta 'nombre_comercial_empresa' si en tu modelo se llama diferente
                letras_emp = empresa_db.nombre_comercial_empresa.replace(" ", "")[:2].upper()
                letras_cli = cliente_db.razon_social_cliente.replace(" ", "")[:2].upper()
                
                # 3. Contamos cuántas cotizaciones existen ya para ESTE cliente
                cantidad_previas = Cotizacion.query.filter_by(id_cliente=cliente_id).count()
                siguiente_num = cantidad_previas + 1
                
                # 4. Construimos el folio (zfill(4) rellena con ceros a la izquierda, ej: 0001)
                nuevo_folio = f"{letras_emp}-{letras_cli}-{str(siguiente_num).zfill(4)}"
                
                # 5. Sobrescribimos el dato en el diccionario que va hacia el PDF para que se imprima correctamente
                cliente['numero_cotizacion'] = nuevo_folio
                # --------------------------------------

                # 4.1 Crear el registro principal de la Cotización
                nueva_cotizacion = Cotizacion(
                    id_user=1,       
                    id_empresa=1,    
                    id_cliente=cliente_id,
                    
                    # Le pasamos nuestra nueva variable generada
                    folio_cotizacion=nuevo_folio, 
                    
                    subtotal_cotizacion=totales['subtotal'],
                    iva_cotizacion=totales['iva'],
                    retencion_isr_cotizacion=totales['retencion_isr'] if totales['retencion_isr'] else 0.00,
                    total_cotizacion=totales['total'],
                    aplica_isr_cotizacion=True if totales['aplicar_isr'] else False,
                    clausulas_cotizacion=clausulas
                )
                db.session.add(nueva_cotizacion)
                db.session.flush() # Hacemos un flush para que la BD le asigne un ID a 'nueva_cotizacion' sin cerrar la transacción
                
                # 4.2 Crear los registros de los Artículos (Items)
                for art in articulos:
                    # Validamos que el artículo no esté vacío
                    if art['item'] or art['descripcion']:
                        nuevo_item = CotizacionItem(
                            id_cotizacion=nueva_cotizacion.id_cotizacion,
                            # Asegúrate de que estos nombres coincidan con tu models.py
                            sku_cotizacion_item=art['item'],
                            descripcion_item_cotizacion=art['descripcion'],
                            cantidad_item_cotizacion=art['cantidad'],
                            costo_unitario_item_cotizacion=art['costo_unitario'],
                            costo_final_item_cotizacion=art['costo_final']
                        )
                        db.session.add(nuevo_item)
                
                # 4.3 Guardar todo definitivamente
                db.session.commit()
                print(f"Cotización {cliente['numero_cotizacion']} guardada con éxito en BD.")
                
            except Exception as e:
                db.session.rollback() # Si algo falla, deshacemos los cambios por seguridad
                print(f"Error al guardar en BD: {e}")
        # ---------------------------------------------------------

        # 5. Renderizar el HTML (Agregamos logo_base64 al render_template)
        html_renderizado = render_template('cotizacion_pdf.html', 
                                           empresa=empresa, 
                                           cliente=cliente, 
                                           articulos=articulos, 
                                           totales=totales, 
                                           clausulas=clausulas,
                                           logo_base64=logo_base64)

        # 6. Convertir a PDF con xhtml2pdf
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html_renderizado, dest=pdf_buffer)

        if pisa_status.err:
            return "Hubo un error al generar el PDF", 500

        # 7. Retornar el PDF al navegador
        respuesta = make_response(pdf_buffer.getvalue())
        respuesta.headers['Content-Type'] = 'application/pdf'
        respuesta.headers['Content-Disposition'] = f'inline; filename={cliente["numero_cotizacion"]}.pdf'
        
        return respuesta

@app.route('/ver_pdf/<int:id_cotizacion>')
def ver_pdf(id_cotizacion):
    # 1. Traer datos de la BD
    cotizacion = Cotizacion.query.get_or_404(id_cotizacion)
    items_db = CotizacionItem.query.filter_by(id_cotizacion=id_cotizacion).all()
    
    # Traemos las entidades relacionadas (Por ahora usando empresa 1)
    empresa_db = Empresa.query.get(cotizacion.id_empresa)
    cliente_db = Cliente.query.get(cotizacion.id_cliente)

    # 2. Reconstruir los diccionarios exactos que espera tu plantilla de PDF
    empresa_dict = {
        'nombre_comercial': empresa_db.nombre_comercial_empresa,
        'razon_social': empresa_db.razon_social_empresa,
        'rfc': empresa_db.rfc_empresa,
        'telefono': empresa_db.telefono1_empresa,
        'correo': empresa_db.email_empresa
    }

    cliente_dict = {
        'numero_cotizacion': cotizacion.folio_cotizacion,
        'nombre': cliente_db.razon_social_cliente,
        'atencion': cliente_db.nombre_contacto_cliente,
        'rfc': cliente_db.rfc_cliente,
        'correo': cliente_db.email_cliente,
        'direccion': cliente_db.direccion_fiscal_cliente,
        'telefono1': cliente_db.telefono1_cliente,
        'entrega': cliente_db.direccion_entrega_cliente
    }

    articulos_list = []
    for i, item in enumerate(items_db, 1):
        articulos_list.append({
            'no_item': i,
            'item': item.sku_cotizacion_item, 
            'descripcion': item.descripcion_item_cotizacion,
            'costo_unitario': item.costo_unitario_item_cotizacion,
            'cantidad': item.cantidad_item_cotizacion,
            'costo_final': item.costo_final_item_cotizacion
        })
        # Eliminamos la línea "subtotal += ..." que sumaba manualmente

    # Tomamos los valores directamente de tu modelo Cotizacion en la base de datos
    totales_dict = {
        'subtotal': cotizacion.subtotal_cotizacion,
        'iva': cotizacion.iva_cotizacion,
        'retencion_isr': cotizacion.retencion_isr_cotizacion,
        'total': cotizacion.total_cotizacion,
        'aplicar_isr': 'si' if cotizacion.aplica_isr_cotizacion else 'no'
    }

    # 3. Procesar HTML y PDF
    html_procesado = render_template('cotizacion_pdf.html', 
                                     empresa=empresa_dict, 
                                     cliente=cliente_dict, 
                                     articulos=articulos_list, 
                                     totales=totales_dict,
                                     clausulas=cotizacion.clausulas_cotizacion,
                                     fecha_entrega=cotizacion.fecha_emision.strftime('%d/%m/%Y'))
    
    pdf_stream = BytesIO()
    pisa.CreatePDF(BytesIO(html_procesado.encode('utf-8')), dest=pdf_stream)
    pdf_stream.seek(0)

    # 4. Devolverlo como vista "inline" (sin descargar)
    response = make_response(pdf_stream.read())
    response.headers['Content-Type'] = 'application/pdf'
    # "inline" le dice al navegador que lo abra en la ventana, no que lo descargue
    response.headers['Content-Disposition'] = f'inline; filename={cotizacion.folio_cotizacion}.pdf'
    
    return response

@app.route('/cambiar_estatus/<int:id_cotizacion>/<estatus>')
def cambiar_estatus(id_cotizacion, estatus):
    # Validamos por seguridad que el estatus sea uno de los permitidos
    estatus_validos = ['Abierta', 'En proceso', 'Declinada', 'Pagada']
    
    if estatus in estatus_validos:
        cotizacion = Cotizacion.query.get_or_404(id_cotizacion)
        cotizacion.estatus_cotizacion = estatus
        db.session.commit()
    
    # Recargamos la página para que la cotización aparezca en su nueva pestaña
    return redirect(url_for('gestionar_cotizaciones'))

@app.route('/editar_cotizacion/<int:id_cotizacion>')
def editar_cotizacion(id_cotizacion):
    # 1. Buscamos la cotización y sus artículos en la base de datos
    cotizacion = Cotizacion.query.get_or_404(id_cotizacion)
    articulos = CotizacionItem.query.filter_by(id_cotizacion=id_cotizacion).all()
    
    # 2. Traemos la lista de clientes (necesaria para el <select> de la página)
    clientes = Cliente.query.all()
    empresas = Empresa.query.all()
    
    # 3. Renderizamos el MISMO formulario de creación, pero le enviamos los datos guardados
    return render_template('cotizador.html', 
                           clientes=clientes, 
                           empresas=empresas,
                           cotizacion_editar=cotizacion, 
                           articulos_editar=articulos)

@app.route('/actualizar_cotizacion/<int:id_cotizacion>', methods=['POST'])
def actualizar_cotizacion(id_cotizacion):
    try:
        # 1. Traemos la cotización existente de la base de datos
        cotizacion = Cotizacion.query.get_or_404(id_cotizacion)
        
        # 2. Actualizamos los datos principales (Cliente, Empresa, Cláusulas y Totales)
        cotizacion.id_cliente = request.form.get('id_cliente')
        cotizacion.id_empresa = request.form.get('id_empresa')
        cotizacion.clausulas_cotizacion = request.form.get('clausulas')
        
        cotizacion.subtotal_cotizacion = request.form.get('subtotal')
        cotizacion.iva_cotizacion = request.form.get('iva')
        # Si no hay retención, aseguramos que guarde 0.00
        cotizacion.retencion_isr_cotizacion = request.form.get('retencion_isr') or 0.00
        cotizacion.total_cotizacion = request.form.get('total')
        cotizacion.aplica_isr_cotizacion = True if request.form.get('aplicar_isr') else False

        # 3. ELIMINAMOS los artículos anteriores de esta cotización
        CotizacionItem.query.filter_by(id_cotizacion=id_cotizacion).delete()
        
        # 4. Recolectamos las listas de artículos que vienen del formulario editado
        items = request.form.getlist('item')
        descripciones = request.form.getlist('descripcion')
        costos_unitarios = request.form.getlist('costo_unitario')
        cantidades = request.form.getlist('cantidad')
        costos_finales = request.form.getlist('costo_final')
        
        # 5. Insertamos los artículos como si fueran nuevos
        for i in range(len(descripciones)):
            if descripciones[i].strip() != "":  # Solo guardamos si la descripción no está vacía
                nuevo_item = CotizacionItem(
                    id_cotizacion=cotizacion.id_cotizacion,
                    sku_cotizacion_item=items[i], 
                    descripcion_item_cotizacion=descripciones[i],
                    costo_unitario_item_cotizacion=costos_unitarios[i],
                    cantidad_item_cotizacion=cantidades[i],
                    costo_final_item_cotizacion=costos_finales[i]
                )
                db.session.add(nuevo_item)
                
        # 6. Guardamos todos los cambios (el UPDATE y los nuevos INSERTS)
        db.session.commit()
        
        # 7. Redirigimos al visualizador de PDF para que se muestre en la pestaña nueva
        return redirect(url_for('gestionar_cotizaciones'))
        
    except Exception as e:
        db.session.rollback() # Si algo falla, deshacemos los cambios por seguridad
        return f"Ocurrió un error al actualizar: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)