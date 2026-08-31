from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Instanciamos la base de datos
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    
    id_user = db.Column(db.Integer, primary_key=True)
    uid_auth = db.Column(db.String(128), unique=True, nullable=True) # Se llenará con Firebase
    nombre_user = db.Column(db.String(100), nullable=False)
    apellidos_user = db.Column(db.String(100), nullable=False)
    email_user = db.Column(db.String(150), unique=True, nullable=False)
    telefono_user = db.Column(db.String(20)) # Corregido de te_user
    fecha_registro_user = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones (Esto te permite acceder a user.empresas o user.clientes fácilmente)
    empresas = db.relationship('Empresa', backref='propietario', lazy=True)
    clientes = db.relationship('Cliente', backref='propietario', lazy=True)
    cotizaciones = db.relationship('Cotizacion', backref='creador', lazy=True)

class Empresa(db.Model):
    __tablename__ = 'empresa'
    
    id_empresa = db.Column(db.Integer, primary_key=True)
    id_user = db.Column(db.Integer, db.ForeignKey('user.id_user'), nullable=False)
    
    nombre_comercial_empresa = db.Column(db.String(150), nullable=False)
    razon_social_empresa = db.Column(db.String(150))
    rfc_empresa = db.Column(db.String(20))
    cp_empresa = db.Column(db.String(10))
    telefono1_empresa = db.Column(db.String(20))
    telefono2_empresa = db.Column(db.String(20))
    email_empresa = db.Column(db.String(150))
    logo_empresa = db.Column(db.Text) # Text para URLs largas o strings Base64
    fecha_registro_empresa = db.Column(db.DateTime, default=datetime.utcnow)
    
    cotizaciones = db.relationship('Cotizacion', backref='empresa_emisora', lazy=True)

class Cliente(db.Model):
    __tablename__ = 'cliente'
    
    id_cliente = db.Column(db.Integer, primary_key=True)
    id_user = db.Column(db.Integer, db.ForeignKey('user.id_user'), nullable=False)
    
    razon_social_cliente = db.Column(db.String(150), nullable=False)
    es_sa_cliente = db.Column(db.Boolean, default=False)
    nombre_contacto_cliente = db.Column(db.String(100))
    rfc_cliente = db.Column(db.String(20))
    email_cliente = db.Column(db.String(150))
    cp_cliente = db.Column(db.String(10))
    direccion_fiscal_cliente = db.Column(db.Text) # Corregido de direccion_discal_cliente
    telefono1_cliente = db.Column(db.String(20))
    telefono2_cliente = db.Column(db.String(20))
    direccion_entrega_cliente = db.Column(db.Text)
    fecha_registro_cliente = db.Column(db.DateTime, default=datetime.utcnow)
    
    cotizaciones = db.relationship('Cotizacion', backref='cliente_receptor', lazy=True)

class Cotizacion(db.Model):
    __tablename__ = 'cotizacion'
    
    id_cotizacion = db.Column(db.Integer, primary_key=True)
    id_user = db.Column(db.Integer, db.ForeignKey('user.id_user'), nullable=False)
    id_empresa = db.Column(db.Integer, db.ForeignKey('empresa.id_empresa'), nullable=False)
    id_cliente = db.Column(db.Integer, db.ForeignKey('cliente.id_cliente'), nullable=False)
    
    folio_cotizacion = db.Column(db.String(50), nullable=False)
    fecha_emision = db.Column(db.DateTime, default=datetime.utcnow)
    clausulas_cotizacion = db.Column(db.Text)
    aplica_isr_cotizacion = db.Column(db.Boolean, default=False)
    
    subtotal_cotizacion = db.Column(db.Numeric(10, 2), default=0.00)
    iva_cotizacion = db.Column(db.Numeric(10, 2), default=0.00)
    retencion_isr_cotizacion = db.Column(db.Numeric(10, 2), default=0.00)
    total_cotizacion = db.Column(db.Numeric(10, 2), default=0.00)
    fecha_registro_cotizacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relación de uno a muchos con los renglones (items)
    items = db.relationship('CotizacionItem', backref='cotizacion_padre', cascade="all, delete-orphan", lazy=True)

class CotizacionItem(db.Model):
    __tablename__ = 'cotizacion__item' # Respetando los dos guiones bajos de tu diagrama
    
    id_cotizacion_item = db.Column(db.Integer, primary_key=True)
    id_cotizacion = db.Column(db.Integer, db.ForeignKey('cotizacion.id_cotizacion'), nullable=False)
    
    orden_cotizacion_item = db.Column(db.Integer)
    sku_cotizacion_item = db.Column(db.String(100))
    descripcion_item_cotizacion = db.Column(db.Text, nullable=False)
    costo_unitario_item_cotizacion = db.Column(db.Numeric(10, 2), nullable=False)
    cantidad_item_cotizacion = db.Column(db.Integer, nullable=False)
    costo_final_item_cotizacion = db.Column(db.Numeric(10, 2), nullable=False)