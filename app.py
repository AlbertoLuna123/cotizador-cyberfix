import os
import base64
from flask import Flask, render_template, request, make_response, redirect, url_for, request, jsonify, session
from xhtml2pdf import pisa
from io import BytesIO
from models import db, User, Empresa, Cliente, Cotizacion, CotizacionItem
import firebase_admin
from firebase_admin import credentials, auth
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import timedelta

app = Flask(__name__)
# Flask-Login requiere una clave secreta para encriptar las cookies de sesión
app.config['SECRET_KEY'] = 'una_clave_secreta_muy_segura_para_cyberfix_2026' 

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

# Render proporciona la URL de la base de datos como variable de entorno
db_url = os.environ.get('DATABASE_URL')
# SQLAlchemy requiere que la URL empiece con postgresql:// en lugar de postgres://
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# Si hay db_url, usa PostgreSQL (en Render). Si no, usa SQLite (en tu computadora local)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///cotizador.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

# --- 1. INICIALIZAR FIREBASE ADMIN ---
# Apunta al archivo JSON que descargaste en el paso 1
ruta_firebase = os.path.join(os.path.dirname(__file__), 'firebase-key.json')
cred = credentials.Certificate(ruta_firebase)
firebase_admin.initialize_app(cred)

# --- 2. INICIALIZAR FLASK-LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' 
login_manager.login_message = "Por favor, inicia sesión para acceder."

# Le decimos a Flask cómo buscar a un usuario en la BD por su ID
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.before_request
def actualizar_sesion():
    # Solo aplica si el usuario ya inició sesión
    if current_user.is_authenticated:
        session.permanent = True
        session.modified = True # Esto reinicia el contador de 30 minutos

#----------------------------------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------------------------------
#--------------------------------------- COMIENZAN LAS RUTAS ----------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------------------------------

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/home')
@login_required
def home():
    # Esta es tu verdadera página de inicio privada
    return render_template('index.html')

@app.route('/login')
def login():
    # Renderizamos la página de inicio de sesión
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    id_token = data.get('idToken')
    
    try:
        # 1. Verificamos el token de seguridad
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token.get('email', '')
        
        # Obtenemos el nombre completo que manda Google (ej. "Mario Alberto Luna Lara")
        nombre_completo = decoded_token.get('name', '')

        # 2. Lógica para separar nombre y apellidos
        if nombre_completo:
            # Separamos el texto solo en el primer espacio que encuentre
            partes = nombre_completo.split(' ', 1) 
            nombre_final = partes[0] # Ej. "Mario"
            # Si tiene más palabras, las pone en apellidos, si no, lo deja en blanco
            apellidos_final = partes[1] if len(partes) > 1 else "Sin apellidos"
        else:
            # Si alguien se registra solo con correo y contraseña, no hay nombre de Google
            nombre_final = email.split('@')[0]
            apellidos_final = "Por definir" # Llenamos el dato porque nullable=False

        # 3. Buscamos si el usuario ya existe
        user = User.query.filter_by(uid_auth=uid).first()
        
        # 4. Si es la primera vez que entra, lo registramos con todos tus campos
        if not user:
            user = User(
                uid_auth=uid,
                nombre_user=nombre_final,
                apellidos_user=apellidos_final,
                email_user=email,
                telefono_user=""
            )
            db.session.add(user)
            
            # Intentamos guardar. Si el correo ya existe, fallará aquí.
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback() # <- ¡CRÍTICO! Destraba la base de datos
                error_msg = str(e)
                # Si el error menciona que el correo (email_user) ya está duplicado
                if "UNIQUE constraint failed: user.email_user" in error_msg or "IntegrityError" in error_msg:
                    return jsonify({"status": "error", "message": "Este correo electrónico ya está registrado. Intenta iniciar sesión con tu contraseña u otra cuenta."}), 400
                else:
                    return jsonify({"status": "error", "message": "Ocurrió un error al crear tu cuenta. Intenta de nuevo."}), 500

        login_user(user)
        return jsonify({"status": "success", "redirect": url_for('gestionar_cotizaciones')})
        
    except Exception as e:
        # 1. Imprimimos el error real en tu terminal de VS Code con un ícono para verlo rápido
        print(f"🔴 ERROR CRÍTICO EN LOGIN: {str(e)}")
        
        # 2. Mandamos el texto del error real a la pantalla en lugar de nuestro texto genérico
        return jsonify({"status": "error", "message": f"Detalle técnico: {str(e)}"}), 401

@app.route('/logout')
def logout():
    logout_user() # Borra la sesión en Flask
    return redirect(url_for('login'))

# --- RUTA PARA EMPRESAS ---
@app.route('/empresas', methods=['GET', 'POST'])
@login_required
def gestionar_empresas():
    if request.method == 'POST':
        nueva_empresa = Empresa(
            id_user=current_user.id_user,
            nombre_comercial_empresa=request.form.get('nombre_comercial'),
            razon_social_empresa=request.form.get('razon_social'),
            rfc_empresa=request.form.get('rfc'),
            cp_empresa=request.form.get('cp'),
            telefono1_empresa=request.form.get('telefono1'),
            telefono2_empresa=request.form.get('telefono2'),
            email_empresa=request.form.get('correo')
        )
        db.session.add(nueva_empresa)
        db.session.commit()
        return redirect(url_for('gestionar_empresas'))
    
    mis_empresas = Empresa.query.filter_by(id_user=current_user.id_user).all()
    return render_template('empresas.html', empresas=mis_empresas)

@app.route('/empresas/editar/<int:id_empresa>', methods=['GET', 'POST'])
@login_required
def editar_empresa(id_empresa):
    # BLINDAJE: Verifica que la empresa le pertenezca al usuario actual
    empresa = Empresa.query.filter_by(id_empresa=id_empresa, id_user=current_user.id_user).first_or_404()
    
    if request.method == 'POST':
        empresa.nombre_comercial_empresa = request.form.get('nombre_comercial')
        empresa.razon_social_empresa = request.form.get('razon_social')
        empresa.rfc_empresa = request.form.get('rfc')
        empresa.cp_empresa = request.form.get('cp')
        empresa.telefono1_empresa = request.form.get('telefono1')
        empresa.telefono2_empresa = request.form.get('telefono2')
        empresa.email_empresa = request.form.get('correo')
        
        db.session.commit()
        return redirect(url_for('gestionar_empresas'))
    
    return render_template('editar_empresa.html', empresa=empresa)

# --- RUTA PARA CLIENTES ---
@app.route('/clientes', methods=['GET', 'POST'])
@login_required
def gestionar_clientes():
    if request.method == 'POST':
        es_sa_booleano = True if request.form.get('es_sa') == 'on' else False
        nuevo_cliente = Cliente(
            id_user=current_user.id_user,
            razon_social_cliente=request.form.get('razon_social'),
            es_sa_cliente=es_sa_booleano,
            nombre_contacto_cliente=request.form.get('contacto'),
            rfc_cliente=request.form.get('rfc'),
            cp_cliente=request.form.get('cp'),
            telefono1_cliente=request.form.get('telefono1'),
            telefono2_cliente=request.form.get('telefono2'),
            email_cliente=request.form.get('correo'),
            direccion_fiscal_cliente=request.form.get('direccion_fiscal'),
            direccion_entrega_cliente=request.form.get('direccion_entrega')
        )
        db.session.add(nuevo_cliente)
        db.session.commit()
        return redirect(url_for('gestionar_clientes'))
    
    mis_clientes = Cliente.query.filter_by(id_user=current_user.id_user).all()
    return render_template('clientes.html', clientes=mis_clientes)

@app.route('/clientes/editar/<int:id_cliente>', methods=['GET', 'POST'])
@login_required
def editar_cliente(id_cliente):
    # BLINDAJE
    cliente = Cliente.query.filter_by(id_cliente=id_cliente, id_user=current_user.id_user).first_or_404()
    
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
        
        db.session.commit()
        return redirect(url_for('gestionar_clientes'))
    
    return render_template('editar_cliente.html', cliente=cliente)

@app.route('/cotizaciones')
@login_required
def gestionar_cotizaciones():
    abiertas = Cotizacion.query.filter_by(estatus_cotizacion='Abierta', id_user=current_user.id_user).order_by(Cotizacion.fecha_emision.desc()).all()
    en_proceso = Cotizacion.query.filter_by(estatus_cotizacion='En proceso', id_user=current_user.id_user).order_by(Cotizacion.fecha_emision.desc()).all()
    declinadas = Cotizacion.query.filter_by(estatus_cotizacion='Declinada', id_user=current_user.id_user).order_by(Cotizacion.fecha_emision.desc()).all()
    pagadas = Cotizacion.query.filter_by(estatus_cotizacion='Pagada', id_user=current_user.id_user).order_by(Cotizacion.fecha_emision.desc()).all()
    
    return render_template('cotizaciones.html', abiertas=abiertas, en_proceso=en_proceso, declinadas=declinadas, pagadas=pagadas)

@app.route('/historial_cotizaciones')
@login_required
def historial_cotizaciones():
    filtro_mes = request.args.get('mes', '')
    filtro_anio = request.args.get('anio', '')

    # BLINDAJE: Historial filtrado por dueño
    historial_completo = Cotizacion.query.filter_by(id_user=current_user.id_user).order_by(Cotizacion.fecha_emision.desc()).all()

    anios_disponibles = sorted(list(set(cot.fecha_emision.year for cot in historial_completo if cot.fecha_emision)), reverse=True)

    historial_filtrado = []
    for cot in historial_completo:
        if cot.fecha_emision:
            if filtro_anio and str(cot.fecha_emision.year) != filtro_anio:
                continue
            if filtro_mes and str(cot.fecha_emision.month) != filtro_mes:
                continue
        historial_filtrado.append(cot)

    meses_es = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    cotizaciones_por_mes = {}
    for cot in historial_filtrado:
        mes_año = f"{meses_es[cot.fecha_emision.month]} {cot.fecha_emision.year}" if cot.fecha_emision else "Sin Fecha"
        if mes_año not in cotizaciones_por_mes:
            cotizaciones_por_mes[mes_año] = []
        cotizaciones_por_mes[mes_año].append(cot)

    kpis = {
        'subtotal': f"{sum(cot.subtotal_cotizacion or 0 for cot in historial_filtrado):,.2f}",
        'iva': f"{sum(cot.iva_cotizacion or 0 for cot in historial_filtrado):,.2f}",
        'retencion': f"{sum(cot.retencion_isr_cotizacion or 0 for cot in historial_filtrado):,.2f}",
        'total': f"{sum(cot.total_cotizacion or 0 for cot in historial_filtrado):,.2f}"
    }

    return render_template('historial_cotizaciones.html', 
                           cotizaciones_por_mes=cotizaciones_por_mes,
                           kpis=kpis,
                           anios_disponibles=anios_disponibles,
                           mes_actual=filtro_mes,
                           anio_actual=filtro_anio)

@app.route('/cotizador')
@login_required
def mostrar_cotizador():
    mis_empresas = Empresa.query.filter_by(id_user=current_user.id_user).all()
    mis_clientes = Cliente.query.filter_by(id_user=current_user.id_user).all()
    
    return render_template('cotizador.html', empresas=mis_empresas, clientes=mis_clientes)

@app.route('/generar', methods=['POST'])
@login_required
def generar_pdf():
    if request.method == 'POST':
        logo_base64 = None
        archivo_logo = request.files.get('logotipo')
        if archivo_logo and archivo_logo.filename != '':
            mime_type = archivo_logo.mimetype
            logo_data = base64.b64encode(archivo_logo.read()).decode('utf-8')
            logo_base64 = f"data:{mime_type};base64,{logo_data}"

        empresa = {
            'nombre_comercial': request.form.get('empresa_nombre_comercial'),
            'razon_social': request.form.get('empresa_razon_social'),
            'rfc': request.form.get('empresa_rfc'),
            'cp': request.form.get('empresa_cp'),
            'telefono': request.form.get('empresa_telefono'),
            'correo': request.form.get('empresa_correo')
        }

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

        totales = {
            'subtotal': request.form.get('subtotal'),
            'iva': request.form.get('iva'),
            'aplicar_isr': request.form.get('aplicar_isr'),
            'retencion_isr': request.form.get('retencion_isr'),
            'total': request.form.get('total')
        }
        clausulas = request.form.get('clausulas')

        cliente_id = request.form.get('id_cliente') 
        empresa_id = request.form.get('id_empresa') # <-- CAPTURAMOS LA EMPRESA REAL
        
        if cliente_id and empresa_id:
            try:
                # BLINDAJE: Evita que usen IDs de empresas/clientes de otros usuarios
                empresa_db = Empresa.query.filter_by(id_empresa=empresa_id, id_user=current_user.id_user).first_or_404()
                cliente_db = Cliente.query.filter_by(id_cliente=cliente_id, id_user=current_user.id_user).first_or_404()
                
                letras_emp = empresa_db.nombre_comercial_empresa.replace(" ", "")[:2].upper()
                letras_cli = cliente_db.razon_social_cliente.replace(" ", "")[:2].upper()
                
                cantidad_previas = Cotizacion.query.filter_by(id_cliente=cliente_id).count()
                siguiente_num = cantidad_previas + 1
                
                nuevo_folio = f"{letras_emp}-{letras_cli}-{str(siguiente_num).zfill(4)}"
                cliente['numero_cotizacion'] = nuevo_folio

                nueva_cotizacion = Cotizacion(
                    id_user=current_user.id_user,       
                    id_empresa=empresa_id,    
                    id_cliente=cliente_id,
                    folio_cotizacion=nuevo_folio, 
                    subtotal_cotizacion=totales['subtotal'],
                    iva_cotizacion=totales['iva'],
                    retencion_isr_cotizacion=totales['retencion_isr'] if totales['retencion_isr'] else 0.00,
                    total_cotizacion=totales['total'],
                    aplica_isr_cotizacion=True if totales['aplicar_isr'] else False,
                    clausulas_cotizacion=clausulas
                )
                db.session.add(nueva_cotizacion)
                db.session.flush() 
                
                for art in articulos:
                    if art['item'] or art['descripcion']:
                        nuevo_item = CotizacionItem(
                            id_cotizacion=nueva_cotizacion.id_cotizacion,
                            sku_cotizacion_item=art['item'],
                            descripcion_item_cotizacion=art['descripcion'],
                            cantidad_item_cotizacion=art['cantidad'],
                            costo_unitario_item_cotizacion=art['costo_unitario'],
                            costo_final_item_cotizacion=art['costo_final']
                        )
                        db.session.add(nuevo_item)
                
                db.session.commit()
                
            except Exception as e:
                db.session.rollback() 
                print(f"Error al guardar en BD: {e}")

        html_renderizado = render_template('cotizacion_pdf.html', 
                                           empresa=empresa, 
                                           cliente=cliente, 
                                           articulos=articulos, 
                                           totales=totales, 
                                           clausulas=clausulas,
                                           logo_base64=logo_base64)

        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html_renderizado, dest=pdf_buffer)

        if pisa_status.err:
            return "Hubo un error al generar el PDF", 500

        respuesta = make_response(pdf_buffer.getvalue())
        respuesta.headers['Content-Type'] = 'application/pdf'
        respuesta.headers['Content-Disposition'] = f'inline; filename={cliente["numero_cotizacion"]}.pdf'
        
        return respuesta

@app.route('/ver_pdf/<int:id_cotizacion>')
@login_required
def ver_pdf(id_cotizacion):
    # BLINDAJE: Solo puede ver sus propios PDFs
    cotizacion = Cotizacion.query.filter_by(id_cotizacion=id_cotizacion, id_user=current_user.id_user).first_or_404()
    items_db = CotizacionItem.query.filter_by(id_cotizacion=id_cotizacion).all()
    
    empresa_db = db.session.get(Empresa, cotizacion.id_empresa)
    cliente_db = db.session.get(Cliente, cotizacion.id_cliente)

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

    totales_dict = {
        'subtotal': cotizacion.subtotal_cotizacion,
        'iva': cotizacion.iva_cotizacion,
        'retencion_isr': cotizacion.retencion_isr_cotizacion,
        'total': cotizacion.total_cotizacion,
        'aplicar_isr': 'si' if cotizacion.aplica_isr_cotizacion else 'no'
    }

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

    response = make_response(pdf_stream.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename={cotizacion.folio_cotizacion}.pdf'
    
    return response

@app.route('/cambiar_estatus/<int:id_cotizacion>/<estatus>')
@login_required
def cambiar_estatus(id_cotizacion, estatus):
    estatus_validos = ['Abierta', 'En proceso', 'Declinada', 'Pagada']
    
    if estatus in estatus_validos:
        # BLINDAJE
        cotizacion = Cotizacion.query.filter_by(id_cotizacion=id_cotizacion, id_user=current_user.id_user).first_or_404()
        cotizacion.estatus_cotizacion = estatus
        db.session.commit()
    
    return redirect(url_for('gestionar_cotizaciones'))

@app.route('/editar_cotizacion/<int:id_cotizacion>')
@login_required
def editar_cotizacion(id_cotizacion):
    # BLINDAJE
    cotizacion = Cotizacion.query.filter_by(id_cotizacion=id_cotizacion, id_user=current_user.id_user).first_or_404()
    articulos = CotizacionItem.query.filter_by(id_cotizacion=id_cotizacion).all()
    
    # BLINDAJE: Solo muestra clientes y empresas de este usuario
    clientes = Cliente.query.filter_by(id_user=current_user.id_user).all()
    empresas = Empresa.query.filter_by(id_user=current_user.id_user).all()
    
    return render_template('cotizador.html', 
                           clientes=clientes, 
                           empresas=empresas,
                           cotizacion_editar=cotizacion, 
                           articulos_editar=articulos)

@app.route('/actualizar_cotizacion/<int:id_cotizacion>', methods=['POST'])
@login_required
def actualizar_cotizacion(id_cotizacion):
    try:
        # BLINDAJE
        cotizacion = Cotizacion.query.filter_by(id_cotizacion=id_cotizacion, id_user=current_user.id_user).first_or_404()
        
        cotizacion.id_cliente = request.form.get('id_cliente')
        cotizacion.id_empresa = request.form.get('id_empresa')
        cotizacion.clausulas_cotizacion = request.form.get('clausulas')
        
        cotizacion.subtotal_cotizacion = request.form.get('subtotal')
        cotizacion.iva_cotizacion = request.form.get('iva')
        cotizacion.retencion_isr_cotizacion = request.form.get('retencion_isr') or 0.00
        cotizacion.total_cotizacion = request.form.get('total')
        cotizacion.aplica_isr_cotizacion = True if request.form.get('aplicar_isr') else False

        CotizacionItem.query.filter_by(id_cotizacion=id_cotizacion).delete()
        
        items = request.form.getlist('item')
        descripciones = request.form.getlist('descripcion')
        costos_unitarios = request.form.getlist('costo_unitario')
        cantidades = request.form.getlist('cantidad')
        costos_finales = request.form.getlist('costo_final')
        
        for i in range(len(descripciones)):
            if descripciones[i].strip() != "":
                nuevo_item = CotizacionItem(
                    id_cotizacion=cotizacion.id_cotizacion,
                    sku_cotizacion_item=items[i], 
                    descripcion_item_cotizacion=descripciones[i],
                    costo_unitario_item_cotizacion=costos_unitarios[i],
                    cantidad_item_cotizacion=cantidades[i],
                    costo_final_item_cotizacion=costos_finales[i]
                )
                db.session.add(nuevo_item)
                
        db.session.commit()
        return redirect(url_for('gestionar_cotizaciones'))
        
    except Exception as e:
        db.session.rollback() 
        return f"Ocurrió un error al actualizar: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)