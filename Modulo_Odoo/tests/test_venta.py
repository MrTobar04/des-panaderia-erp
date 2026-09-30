# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError


class TestPanaderiaVenta(TransactionCase):
    """Suite de pruebas unitarias para el modelo panaderia.venta y panaderia.venta.linea."""

    @classmethod
    def setUpClass(cls):
        super(TestPanaderiaVenta, cls).setUpClass()
        # 1. Crear categoría
        cls.categoria_pan = cls.env['panaderia.categoria'].create({
            'name': 'Pan Tradicional',
            'codigo': 'PAN-TEST',
        })
        cls.categoria_pasteles = cls.env['panaderia.categoria'].create({
            'name': 'Pasteles',
            'codigo': 'PAS-TEST',
        })

        # 2. Crear cliente
        cls.cliente_mostrador = cls.env['res.partner'].create({
            'name': 'Cliente Mostrador Test',
            'email': 'mostrador@panaderia.test',
        })

        # 3. Crear productos de prueba con existencias iniciales
        cls.prod_pan_frances = cls.env['panaderia.producto'].create({
            'name': 'Pan Francés Test',
            'codigo': 'PFR-001',
            'categoria_id': cls.categoria_pan.id,
            'costo': 0.05,
            'precio_venta': 0.10,
            'cantidad_disponible': 50.0,
        })
        cls.prod_selva_negra = cls.env['panaderia.producto'].create({
            'name': 'Pastel Selva Negra Test',
            'codigo': 'SEL-001',
            'categoria_id': cls.categoria_pasteles.id,
            'costo': 7.00,
            'precio_venta': 15.00,
            'cantidad_disponible': 5.0,
        })

    def test_01_create_sale_and_subtotals(self):
        """Escenario 1: Creación de venta en mostrador y cálculo reactivo de subtotales y total."""
        venta = self.env['panaderia.venta'].create({
            'cliente_id': self.cliente_mostrador.id,
        })
        self.assertEqual(venta.state, 'draft', "El estado inicial de la orden debe ser 'draft'.")
        self.assertEqual(venta.name, 'Nuevo', "El folio inicial debe ser 'Nuevo'.")

        # Agregar Línea 1: 10 Pan Francés
        linea1 = self.env['panaderia.venta.linea'].create({
            'venta_id': venta.id,
            'producto_id': self.prod_pan_frances.id,
            'cantidad': 10.0,
            'precio_unitario': self.prod_pan_frances.precio_venta,
        })
        self.assertAlmostEqual(linea1.subtotal, 1.00, places=2, msg="Subtotal de 10 unidades a $0.10 debe ser $1.00.")

        # Agregar Línea 2: 1 Pastel Selva Negra
        linea2 = self.env['panaderia.venta.linea'].create({
            'venta_id': venta.id,
            'producto_id': self.prod_selva_negra.id,
            'cantidad': 1.0,
            'precio_unitario': self.prod_selva_negra.precio_venta,
        })
        self.assertAlmostEqual(linea2.subtotal, 15.00, places=2, msg="Subtotal de 1 pastel a $15.00 debe ser $15.00.")

        # Comprobar total general
        self.assertAlmostEqual(venta.total, 16.00, places=2, msg="Total de la venta debe ser 1.00 + 15.00 = 16.00.")

    def test_02_invalid_line_values_raise_error(self):
        """Validación de cantidades y precios en las líneas de venta."""
        venta = self.env['panaderia.venta'].create({
            'cliente_id': self.cliente_mostrador.id,
        })
        # Cantidad <= 0
        with self.assertRaises(ValidationError):
            self.env['panaderia.venta.linea'].create({
                'venta_id': venta.id,
                'producto_id': self.prod_pan_frances.id,
                'cantidad': 0.0,
                'precio_unitario': 0.10,
            })
        # Precio negativo
        with self.assertRaises(ValidationError):
            self.env['panaderia.venta.linea'].create({
                'venta_id': venta.id,
                'producto_id': self.prod_pan_frances.id,
                'cantidad': 5.0,
                'precio_unitario': -1.0,
            })

    def test_03_action_confirm_sequence_and_stock(self):
        """Escenario 2: Confirmación de venta, asignación de folio VEN-XXXX, decremento de stock y factura."""
        stock_inicial_pan = self.prod_pan_frances.cantidad_disponible
        stock_inicial_pastel = self.prod_selva_negra.cantidad_disponible

        venta = self.env['panaderia.venta'].create({
            'cliente_id': self.cliente_mostrador.id,
            'linea_ids': [
                (0, 0, {
                    'producto_id': self.prod_pan_frances.id,
                    'cantidad': 10.0,
                    'precio_unitario': 0.10,
                }),
                (0, 0, {
                    'producto_id': self.prod_selva_negra.id,
                    'cantidad': 1.0,
                    'precio_unitario': 15.00,
                })
            ]
        })

        # Ejecutar confirmación
        venta.action_confirm()

        # Verificaciones
        self.assertEqual(venta.state, 'confirmed', "El estado de la venta debe pasar a 'confirmed'.")
        self.assertTrue(venta.name.startswith('VEN-'), f"El folio debe ser correlativo con prefijo VEN-, recibido: {venta.name}")
        self.assertAlmostEqual(
            self.prod_pan_frances.cantidad_disponible,
            stock_inicial_pan - 10.0,
            places=2,
            msg="El stock de Pan Francés debe decrementarse en 10 unidades (de 50 a 40)."
        )
        self.assertAlmostEqual(
            self.prod_selva_negra.cantidad_disponible,
            stock_inicial_pastel - 1.0,
            places=2,
            msg="El stock de Pastel Selva Negra debe decrementarse en 1 unidad (de 5 a 4)."
        )
        self.assertTrue(venta.factura_id, "Se debe haber generado y vinculado una factura.")
        self.assertEqual(venta.factura_id.state, 'pending', "La factura generada debe estar en estado 'pending'.")
        self.assertAlmostEqual(venta.factura_id.monto_total, 16.00, places=2, msg="La factura debe tener monto de $16.00.")

    def test_04_insufficient_stock_raises_validation_error(self):
        """Validación de stock insuficiente al confirmar la venta."""
        # Producto con stock disponible = 5
        venta = self.env['panaderia.venta'].create({
            'cliente_id': self.cliente_mostrador.id,
            'linea_ids': [
                (0, 0, {
                    'producto_id': self.prod_selva_negra.id,
                    'cantidad': 100.0,  # Excede los 5 disponibles
                    'precio_unitario': 15.00,
                })
            ]
        })

        with self.assertRaises(ValidationError):
            venta.action_confirm()

        # El estado debe mantenerse en borrador y el stock sin tocar
        self.assertEqual(venta.state, 'draft', "La venta debe seguir en borrador tras fallar stock.")

    def test_05_immutability_on_confirmed_order(self):
        """Escenario 3: Bloqueo de edición y eliminación en órdenes confirmadas."""
        venta = self.env['panaderia.venta'].create({
            'cliente_id': self.cliente_mostrador.id,
            'linea_ids': [
                (0, 0, {
                    'producto_id': self.prod_pan_frances.id,
                    'cantidad': 5.0,
                    'precio_unitario': 0.10,
                })
            ]
        })
        venta.action_confirm()

        # Intentar modificar el cliente vía write()
        with self.assertRaises(UserError):
            otro_cliente = self.env['res.partner'].create({'name': 'Otro Cliente'})
            venta.write({'cliente_id': otro_cliente.id})

        # Intentar eliminar la orden confirmada vía unlink()
        with self.assertRaises(UserError):
            venta.unlink()

    def test_06_action_cancel_and_stock_reversion(self):
        """Cancelación de venta confirmada y reversión de stock."""
        stock_antes = self.prod_pan_frances.cantidad_disponible
        venta = self.env['panaderia.venta'].create({
            'cliente_id': self.cliente_mostrador.id,
            'linea_ids': [
                (0, 0, {
                    'producto_id': self.prod_pan_frances.id,
                    'cantidad': 8.0,
                    'precio_unitario': 0.10,
                })
            ]
        })
        venta.action_confirm()
        self.assertAlmostEqual(self.prod_pan_frances.cantidad_disponible, stock_antes - 8.0, places=2)

        # Cancelar venta
        venta.action_cancel()
        self.assertEqual(venta.state, 'cancelled', "El estado debe ser 'cancelled'.")
        self.assertAlmostEqual(
            self.prod_pan_frances.cantidad_disponible,
            stock_antes,
            places=2,
            msg="El stock debe haberse revertido sumando las 8 unidades."
        )
        if venta.factura_id:
            self.assertEqual(venta.factura_id.state, 'cancelled', "La factura vinculada debe cancelarse.")

        # Volver a borrador
        venta.action_draft()
        self.assertEqual(venta.state, 'draft', "La venta debe poder volver a borrador.")
