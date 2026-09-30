# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from odoo import fields


class TestPanaderiaFactura(TransactionCase):
    """Suite de pruebas unitarias para el modelo panaderia.factura (SPEC-4.1.1)."""

    @classmethod
    def setUpClass(cls):
        super(TestPanaderiaFactura, cls).setUpClass()
        # 1. Crear cliente
        cls.cliente_test = cls.env['res.partner'].create({
            'name': 'Cliente Factura Test',
            'email': 'cliente.factura@panaderia.test',
        })

        # 2. Crear categoría y producto para ventas vinculadas
        cls.categoria_pan = cls.env['panaderia.categoria'].create({
            'name': 'Panadería Factura Test',
            'codigo': 'PAN-FAC',
        })
        cls.producto_pan = cls.env['panaderia.producto'].create({
            'name': 'Pan Baguette Test',
            'codigo': 'BAG-001',
            'categoria_id': cls.categoria_pan.id,
            'costo': 0.50,
            'precio_venta': 1.50,
            'cantidad_disponible': 100.0,
        })

    def test_01_invoice_sequence_and_initial_state(self):
        """US1: Asignación correlativa de folio FAC-XXXX y estado inicial pending."""
        factura = self.env['panaderia.factura'].create({
            'cliente_id': self.cliente_test.id,
            'monto_total': 15.00,
            'metodo_pago': 'efectivo',
        })
        self.assertTrue(factura.name.startswith('FAC-'), f"El folio debe iniciar con 'FAC-', obtenido: {factura.name}")
        self.assertEqual(factura.state, 'pending', "El estado inicial de la factura debe ser 'pending'.")
        self.assertEqual(factura.monto_total, 15.00, "El monto total debe ser $15.00.")
        self.assertEqual(factura.metodo_pago, 'efectivo', "El método de pago predeterminado debe ser 'efectivo'.")
        self.assertFalse(factura.fecha_pago, "La fecha de pago debe ser False mientras esté pendiente.")

    def test_02_register_payment_and_timestamp(self):
        """US2: Registro de pago en caja, transición a paid y registro de timestamp."""
        factura = self.env['panaderia.factura'].create({
            'cliente_id': self.cliente_test.id,
            'monto_total': 25.50,
            'metodo_pago': 'tarjeta',
        })
        self.assertEqual(factura.state, 'pending')

        # Ejecutar acción registrar pago
        factura.action_register_payment()

        self.assertEqual(factura.state, 'paid', "El estado debe cambiar a 'paid' tras registrar pago.")
        self.assertTrue(factura.fecha_pago, "La fecha de pago debe haberse registrado.")

    def test_03_cancel_invoice(self):
        """US2: Cancelación de factura en estado pendiente."""
        factura = self.env['panaderia.factura'].create({
            'cliente_id': self.cliente_test.id,
            'monto_total': 10.00,
        })
        factura.action_cancel()
        self.assertEqual(factura.state, 'cancelled', "El estado debe ser 'cancelled'.")

        # Intentar cancelar una factura pagada debe arrojar UserError
        factura_pagada = self.env['panaderia.factura'].create({
            'cliente_id': self.cliente_test.id,
            'monto_total': 12.00,
        })
        factura_pagada.action_register_payment()
        with self.assertRaises(UserError):
            factura_pagada.action_cancel()

    def test_04_bidirectional_navigation(self):
        """US3: Navegación bidireccional entre panaderia.venta y panaderia.factura."""
        # Crear venta
        venta = self.env['panaderia.venta'].create({
            'cliente_id': self.cliente_test.id,
        })
        self.env['panaderia.venta.linea'].create({
            'venta_id': venta.id,
            'producto_id': self.producto_pan.id,
            'cantidad': 10.0,
            'precio_unitario': 1.50,
        })
        venta.action_confirm()

        self.assertTrue(venta.factura_id, "La orden confirmada debe tener factura vinculada.")
        factura = venta.factura_id
        self.assertEqual(factura.venta_id.id, venta.id, "La factura debe referenciar a la venta.")

        # Test acción desde venta hacia factura
        action_factura = venta.action_view_factura()
        self.assertEqual(action_factura.get('res_id'), factura.id)

        # Test acción desde factura hacia venta
        action_venta = factura.action_view_venta()
        self.assertEqual(action_venta.get('res_id'), venta.id)

    def test_05_immutability_on_paid_invoice(self):
        """US4: Bloqueo de modificación de datos financieros tras pasar a paid."""
        factura = self.env['panaderia.factura'].create({
            'cliente_id': self.cliente_test.id,
            'monto_total': 50.00,
        })
        factura.action_register_payment()
        self.assertEqual(factura.state, 'paid')

        # Intentar alterar el monto total debe fallar
        with self.assertRaises(UserError):
            factura.write({'monto_total': 99.99})

        # Intentar alterar el cliente debe fallar
        otro_cliente = self.env['res.partner'].create({'name': 'Otro Cliente Test'})
        with self.assertRaises(UserError):
            factura.write({'cliente_id': otro_cliente.id})

    def test_06_prevent_unlink_paid_invoice(self):
        """US4: Prevención de eliminación de facturas pagadas por auditoría."""
        factura = self.env['panaderia.factura'].create({
            'cliente_id': self.cliente_test.id,
            'monto_total': 30.00,
        })
        factura.action_register_payment()
        with self.assertRaises(UserError):
            factura.unlink()

    def test_07_constraints_validation(self):
        """US4: Validaciones de restricciones @api.constrains."""
        # Monto negativo debe ser rechazado
        with self.assertRaises(ValidationError):
            self.env['panaderia.factura'].create({
                'cliente_id': self.cliente_test.id,
                'monto_total': -5.00,
            })

        # Duplicidad de factura activa para la misma venta
        venta = self.env['panaderia.venta'].create({
            'cliente_id': self.cliente_test.id,
        })
        self.env['panaderia.venta.linea'].create({
            'venta_id': venta.id,
            'producto_id': self.producto_pan.id,
            'cantidad': 2.0,
            'precio_unitario': 1.50,
        })
        venta.action_confirm()

        with self.assertRaises(ValidationError):
            self.env['panaderia.factura'].create({
                'cliente_id': self.cliente_test.id,
                'venta_id': venta.id,
                'monto_total': 3.00,
            })
