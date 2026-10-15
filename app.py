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
        items = request.form.getlist('items[]')
        descripciones = request.form.getlist('descripciones[]')
        costos_unitarios = request.form.getlist('costos_unitarios[]')
        cantidades = request.form.getlist('cantidades[]')
        costos_finales = request.form.getlist('costos_finales[]')

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

if __name__ == '__main__':
    app.run(debug=True)