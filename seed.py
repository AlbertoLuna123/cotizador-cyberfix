from app import app
from models import db, User, Empresa, Cliente

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
            rfc_empresa="LULM980716AZ5", # RFC de prueba
            cp_empresa="66475",
            telefono1_empresa="8111275499",
            email_empresa="mario.luna@cyberfix.sbs"
        )
        db.session.add(empresa)

        # 3. Crear un par de clientes de prueba vinculados al usuario
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

        # Confirmamos todos los cambios en la base de datos
        db.session.commit()
        print("¡Datos de prueba inyectados correctamente!")

if __name__ == '__main__':
    inyectar_datos()