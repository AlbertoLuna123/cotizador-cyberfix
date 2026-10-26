from app import app
# Asegúrate de agregar 'Cotizacion' a tus importaciones
from models import db, User, Empresa, Cliente, Cotizacion 
from datetime import datetime # Importamos datetime para manipular las fechas

def inyectar_datos():
    with app.app_context():
        # 1. Crear el usuario principal
        usuario = User(
            uid_auth="test_firebase_uid_123",
            nombre_user="Mario Alberto",
            apellidos_user="Luna Lara",
            email_user="maluna.fime@gmail.com",
            telefono_user="8111275499"
        )
        db.session.add(usuario)
        db.session.commit() # Guardamos para que se genere su ID

        # 2. Crear una empresa vinculada a ese usuario
        empresa = Empresa(
            id_user=usuario.id_user,
            nombre_comercial_empresa="CyberFix Monterrey",
            razon_social_empresa="Mario Luna Lara",
            rfc_empresa="LULM980716AZ5",
            cp_empresa="66475",
            telefono1_empresa="8111275499",
            email_empresa="mario.luna@cyberfix.sbs"
        )
        db.session.add(empresa)
        db.session.commit() # Guardamos para generar el ID de empresa

        # 3. Crear clientes de prueba
        cliente1 = Cliente(
            id_user=usuario.id_user,
            razon_social_cliente="Alejandro Adrian Luna Valdez",
            es_sa_cliente=False,
            nombre_contacto_cliente="Alejandro Luna",
            rfc_cliente="LUVA561007RI8",
            email_cliente="contacto@pluseventos.com",
            direccion_fiscal_cliente="Rio Conchos 646, Casa Blanca",
            telefono1_cliente="8183205070"
        )
        db.session.add(cliente1)

        cliente2 = Cliente(
            id_user=usuario.id_user,
            razon_social_cliente="Estación Fiesta",
            es_sa_cliente=False,
            nombre_contacto_cliente="Administración",
            direccion_fiscal_cliente="Monterrey, Nuevo León"
        )
        db.session.add(cliente2)
        db.session.commit() # Guardamos para generar los IDs de los clientes

        # 4. CREAR COTIZACIONES DE PRUEBA (OCTUBRE Y NOVIEMBRE)
        
        # Cotización de Octubre
        cotizacion_oct = Cotizacion(
            id_user=usuario.id_user,
            id_empresa=empresa.id_empresa,
            id_cliente=cliente1.id_cliente,
            folio_cotizacion="CY-AL-0008",
            fecha_emision=datetime(2026, 10, 15), # Fecha forzada a Octubre
            estatus_cotizacion="Abierta",
            subtotal_cotizacion=5000.00,
            iva_cotizacion=800.00,
            retencion_isr_cotizacion=0.00,
            total_cotizacion=5800.00
        )
        db.session.add(cotizacion_oct)

        # Cotización de Noviembre
        cotizacion_nov = Cotizacion(
            id_user=usuario.id_user,
            id_empresa=empresa.id_empresa,
            id_cliente=cliente2.id_cliente,
            folio_cotizacion="CY-ES-0009",
            fecha_emision=datetime(2026, 11, 5), # Fecha forzada a Noviembre
            estatus_cotizacion="En Proceso",
            subtotal_cotizacion=8000.00,
            iva_cotizacion=1280.00,
            retencion_isr_cotizacion=0.00,
            total_cotizacion=9280.00
        )
        db.session.add(cotizacion_nov)

        # Confirmamos todos los cambios finales
        db.session.commit()
        print("¡Datos de prueba inyectados correctamente!")

if __name__ == '__main__':
    inyectar_datos()