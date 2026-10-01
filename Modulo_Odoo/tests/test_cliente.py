# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo import fields


class TestPanaderiaCliente(TransactionCase):
    """Suite de pruebas unitarias para la extensión de res.partner (Clientes de Panadería)."""

    @classmethod
    def setUpClass(cls):
        super(TestPanaderiaCliente, cls).setUpClass()
        # 1. Crear categoría de prueba
        cls.categoria_pan = cls.env['panaderia.categoria'].create({
            'name': 'Pan Tradicional Test',
            'codigo': 'PAN-CLI-TEST',
        })

        # 2. Crear productos de prueba con existencias
        cls.prod_baguette = cls.env['panaderia.producto'].create({
            'name': 'Baguette Rústico Test',
            'codigo': 'BAG-001',
            'categoria_id': cls.categoria_pan.id,
            'costo': 0.50,
            'precio_venta': 1.25,
            'cantidad_disponible': 100.0,
        })
        cls.prod_croissant = cls.env['panaderia.producto'].create({
            'name': 'Croissant de Mantequilla Test',
            'codigo': 'CRO-001',
            'categoria_id': cls.categoria_pan.id,
            'costo': 0.40,
            'precio_venta': 0.75,
            'cantidad_disponible': 100.0,
        })

    def test_01_cliente_defaults_and_fields(self):
        """Escenario 1: Creación de cliente de panadería con valores por defecto y preferencias."""
        cliente = self.env['res.partner'].create({
            'name': 'Carlos Mendoza Test',
            'phone': '7123-4567',
            'notas_preferencias': 'Prefiere pan integral caliente por las tardes.',
        })

        self.assertTrue(cliente.es_cliente_panaderia, "Por defecto, es_cliente_panaderia debe ser True.")
        self.assertEqual(
            cliente.fecha_registro_panaderia,
            fields.Date.context_today(cliente),
            "La fecha de registro debe inicializarse con la fecha actual."
        )
        self.assertEqual(
            cliente.total_compras_panaderia,
            0.0,
            "El total de compras inicial debe ser 0.00."
        )
        self.assertEqual(
            cliente.ventas_panaderia_count,
            0,
            "El contador de ventas inicial debe ser 0."
        )
        self.assertIn("pan integral", cliente.notas_preferencias)

    def test_02_seed_data_validation(self):
        """Escenario 2: Validación de datos semilla precargados (Cliente Mostrador y Carlos Mendoza)."""
        mostrador = (
            self.env.ref('panaderia.res_partner_cliente_mostrador', raise_if_not_found=False)
            or self.env.ref('Modulo_Odoo.res_partner_cliente_mostrador', raise_if_not_found=False)
        )
        if mostrador:
            self.assertTrue(mostrador.es_cliente_panaderia, "El cliente mostrador debe ser cliente de panadería.")
            self.assertEqual(mostrador.name, "Cliente General / Mostrador")
            self.assertTrue(mostrador.email, "Debe tener correo configurado.")

        carlos = (
            self.env.ref('panaderia.res_partner_carlos_mendoza', raise_if_not_found=False)
            or self.env.ref('Modulo_Odoo.res_partner_carlos_mendoza', raise_if_not_found=False)
        )
        if carlos:
            self.assertTrue(carlos.es_cliente_panaderia)
            self.assertEqual(carlos.phone, "7123-4567")

    def test_03_cumulative_purchases_confirmed_sales(self):
        """Escenario 3: Cálculo reactivo de compras acumuladas tras confirmar órdenes de venta ($12.50 + $7.50)."""
        cliente = self.env['res.partner'].create({
            'name': 'Beatriz Rivas Test',
            'phone': '7222-3344',
        })
        self.assertEqual(cliente.total_compras_panaderia, 0.0)

        # Venta 1: 10 baguettes @ $1.25 = $12.50
        venta1 = self.env['panaderia.venta'].create({
            'cliente_id': cliente.id,
            'linea_ids': [(0, 0, {
                'producto_id': self.prod_baguette.id,
                'cantidad': 10.0,
                'precio_unitario': 1.25,
            })]
        })
        self.assertAlmostEqual(venta1.total, 12.50, places=2)

        # Venta en borrador no debe acumular todavía
        cliente._compute_total_compras_panaderia()
        self.assertEqual(cliente.total_compras_panaderia, 0.0, "Las ventas en borrador no deben sumar al acumulado.")

        # Confirmar Venta 1
        venta1.action_confirm()
        self.assertEqual(venta1.state, 'confirmed')
        self.assertAlmostEqual(cliente.total_compras_panaderia, 12.50, places=2)
        self.assertEqual(cliente.ventas_panaderia_count, 1)

        # Venta 2: 10 croissants @ $0.75 = $7.50
        venta2 = self.env['panaderia.venta'].create({
            'cliente_id': cliente.id,
            'linea_ids': [(0, 0, {
                'producto_id': self.prod_croissant.id,
                'cantidad': 10.0,
                'precio_unitario': 0.75,
            })]
        })
        self.assertAlmostEqual(venta2.total, 7.50, places=2)
        venta2.action_confirm()
        self.assertEqual(venta2.state, 'confirmed')

        # Total acumulado esperado: $12.50 + $7.50 = $20.00
        self.assertAlmostEqual(
            cliente.total_compras_panaderia,
            20.00,
            places=2,
            msg="El total de compras acumulado debe ser exactamente $20.00."
        )
        self.assertEqual(cliente.ventas_panaderia_count, 2)

    def test_04_cancellation_reverts_accumulated_total(self):
        """Escenario 4: Cancelar una orden de venta confirmada descuenta el importe del total del cliente."""
        cliente = self.env['res.partner'].create({
            'name': 'Diego Gómez Test',
        })
        venta = self.env['panaderia.venta'].create({
            'cliente_id': cliente.id,
            'linea_ids': [(0, 0, {
                'producto_id': self.prod_baguette.id,
                'cantidad': 20.0,
                'precio_unitario': 1.25,
            })]
        })
        venta.action_confirm()
        self.assertAlmostEqual(cliente.total_compras_panaderia, 25.00, places=2)

        # Cancelar la venta
        venta.action_cancel()
        self.assertEqual(venta.state, 'cancelled')
        self.assertAlmostEqual(
            cliente.total_compras_panaderia,
            0.00,
            places=2,
            msg="Al cancelar la venta, el total acumulado debe retornar a $0.00."
        )
        self.assertEqual(cliente.ventas_panaderia_count, 0)

    def test_05_bakery_customer_filtering_domain(self):
        """Escenario 5: El dominio de panadería filtra únicamente contactos con es_cliente_panaderia = True."""
        cliente_panaderia = self.env['res.partner'].create({
            'name': 'Cliente Panadería Activo',
            'es_cliente_panaderia': True,
        })
        proveedor_harina = self.env['res.partner'].create({
            'name': 'Distribuidora de Harinas S.A.',
            'es_cliente_panaderia': False,
        })

        clientes_filtrados = self.env['res.partner'].search([('es_cliente_panaderia', '=', True)])
        self.assertIn(cliente_panaderia, clientes_filtrados)
        self.assertNotIn(proveedor_harina, clientes_filtrados)

    def test_06_action_view_panaderia_ventas(self):
        """Escenario 6: Validación de la acción de ventana para consultar ventas desde la ficha del cliente."""
        cliente = self.env['res.partner'].create({
            'name': 'Elena Vásquez Test',
        })
        action = cliente.action_view_panaderia_ventas()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'panaderia.venta')
        self.assertEqual(action['domain'], [('cliente_id', '=', cliente.id)])
        self.assertEqual(action['context']['default_cliente_id'], cliente.id)
