# -*- coding: utf-8 -*-
import uuid
import re
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestFacturaDTE(TransactionCase):

    def setUp(self):
        super(TestFacturaDTE, self).setUp()
        self.Partner = self.env['res.partner']
        self.Producto = self.env['panaderia.producto']
        self.Categoria = self.env['panaderia.categoria']
        self.Venta = self.env['panaderia.venta']
        self.Factura = self.env['panaderia.factura']

        self.categoria = self.Categoria.create({
            'name': 'Pasteles de Prueba DTE',
            'codigo': 'PASTEST'
        })
        self.producto = self.Producto.create({
            'name': 'Pastel Fiesta Chocolate',
            'categoria_id': self.categoria.id,
            'costo': 5.0,
            'precio_venta': 15.50,
            'cantidad_disponible': 10.0,
            'stock_minimo': 2.0
        })
        self.cliente = self.Partner.create({
            'name': 'Juan Pérez Ramos',
            'dui': '06202964-6',
            'nit': '06140803841010',
            'email': 'juan.perez@email.com',
            'street': 'Colonia San Benito, Calle La Reforma #140, San Salvador'
        })

    def test_01_creacion_factura_asigna_identificadores_dte(self):
        """Verifica que al crear una factura se generen automáticamente los datos oficiales DTE."""
        factura = self.Factura.create({
            'cliente_id': self.cliente.id,
            'monto_total': 79.00,
            'state': 'pending'
        })

        # 1. Código de Generación (UUID v4)
        self.assertTrue(factura.codigo_generacion, "Debe generar código de generación DTE")
        uuid_obj = uuid.UUID(factura.codigo_generacion)
        self.assertEqual(str(uuid_obj).upper(), factura.codigo_generacion, "El UUID debe estar en formato canónico mayúsculas")

        # 2. Número de Control MH
        self.assertTrue(factura.numero_control, "Debe generar número de control")
        self.assertTrue(factura.numero_control.startswith("DTE-01-M001P001-"), "Debe tener prefijo oficial DTE-01-M001P001-")

        # 3. Sello de Recepción
        self.assertTrue(factura.sello_recepcion, "Debe generar sello de recepción fiscal")
        self.assertEqual(len(factura.sello_recepcion), 40, "El sello de recepción simulado debe tener 40 caracteres")

        # 4. Total en Letras
        self.assertEqual(factura.monto_letras, "SETENTA Y NUEVE CON 00/100", "Debe convertir 79.00 exactamente a palabras")

        # 5. Código QR
        self.assertTrue(factura.qr_data, "Debe generar contenido para el código QR")
        self.assertIn("https://admin.factura.gob.sv/consultaPublica", factura.qr_data)
        self.assertIn(factura.codigo_generacion, factura.qr_data)

    def test_02_conversion_monto_letras_decimales(self):
        """Verifica la precisión de la conversión a letras con centavos."""
        factura = self.Factura.create({
            'cliente_id': self.cliente.id,
            'monto_total': 15.50,
            'state': 'pending'
        })
        self.assertEqual(factura.monto_letras, "QUINCE CON 50/100")

    def test_03_accion_imprimir_reporte_factura_dte(self):
        """Verifica que la acción action_print_factura_dte devuelva el reporte QWeb configurado."""
        factura = self.Factura.create({
            'cliente_id': self.cliente.id,
            'monto_total': 31.00,
            'state': 'pending'
        })
        action = factura.action_print_factura_dte()
        self.assertIsInstance(action, dict)
        self.assertEqual(action.get('type'), 'ir.actions.report')
        self.assertEqual(action.get('report_name'), 'panaderia.reporte_factura_dte')

    def test_04_flujo_venta_a_factura_dte(self):
        """Verifica que al confirmar una venta, la factura creada cuente con datos DTE listos para PDF."""
        venta = self.Venta.create({
            'cliente_id': self.cliente.id,
            'linea_ids': [(0, 0, {
                'producto_id': self.producto.id,
                'cantidad': 2.0,
                'precio_unitario': 15.50
            })]
        })
        venta.action_confirm()

        self.assertEqual(venta.state, 'confirmed')
        self.assertTrue(venta.factura_id, "La orden de venta debe tener factura asociada")
        factura = venta.factura_id
        self.assertEqual(factura.monto_total, 31.00)
        self.assertTrue(factura.codigo_generacion)
        self.assertEqual(len(factura.linea_ids), 1, "La factura debe tener acceso a las líneas de venta")
        self.assertEqual(factura.linea_ids[0].producto_id.name, 'Pastel Fiesta Chocolate')
