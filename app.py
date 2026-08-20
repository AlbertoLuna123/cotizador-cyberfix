import os
import base64 # <-- Importamos base64 para procesar la imagen
from flask import Flask, render_template, request, make_response
from xhtml2pdf import pisa
from io import BytesIO

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

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
            'entrega': request.form.get('cliente_entrega')
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
                                           logo_base64=logo_base64) # <-- Pasamos la imagen

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