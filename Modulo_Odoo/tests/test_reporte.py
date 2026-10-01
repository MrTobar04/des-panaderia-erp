# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from datetime import date


class TestPanaderiaReportes(TransactionCase):
    """Suite de pruebas unitarias para el módulo de reportes analíticos y alertas de panadería (SPEC-5.1.1)."""

    @classmethod
    def setUpClass(cls):
        super(TestPanaderiaReportes, cls).setUpClass()
        # 1. Crear Categorías
        cls.categoria_pan = cls.env['panaderia.categoria'].create({
            'name': 'Pan Tradicional Reportes',
            'codigo': 'PAN-REP',
        })
        cls.categoria_pasteles = cls.env['panaderia.categoria'].create({
            'name': 'Pasteles Reportes',
            'codigo': 'PAS-REP',
        })

        # 2. Crear Cliente
        cls.cliente_test = cls.env['res.partner'].create({
            'name': 'Cliente Reportes Test',
            'email': 'reportes@panaderia.test',
        })

        # 3. Crear Productos con existencias
        cls.prod_pan_frances = cls.env['panaderia.producto'].create({
            'name': 'Pan Francés Reportes',
            'codigo': 'PFR-REP',
            'categoria_id': cls.categoria_pan.id,
            'costo': 0.05,
            'precio_venta': 0.10,
            'cantidad_disponible': 200.0,
            'stock_minimo': 20.0,
        })
        cls.prod_selva_negra = cls.env['panaderia.producto'].create({
            'name': 'Pastel Selva Negra Reportes',
            'codigo': 'SEL-REP',
            'categoria_id': cls.categoria_pasteles.id,
            'costo': 7.00,
            'precio_venta': 15.00,
            'cantidad_disponible': 25.0,
            'stock_minimo': 5.0,
        })
        cls.prod_stock_critico = cls.env['panaderia.producto'].create({
            'name': 'Dona Rellena Crítica',
            'codigo': 'DON-CRI',
            'categoria_id': cls.categoria_pan.id,
            'costo': 0.50,
            'precio_venta': 1.25,
            'cantidad_disponible': 3.0,
            'stock_minimo': 10.0,
        })

    def test_01_sql_view_daily_sales_aggregation(self):
        """Escenario 1: Consulta de ventas del día actual y agregación en la vista SQL."""
        # Registrar y confirmar venta
        venta = self.env['panaderia.venta'].create({
            'cliente_id': self.cliente_test.id,
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
        venta.action_confirm()

        # Consultar la vista SQL panaderia.reporte.ventas
        hoy = date.today()
        reporte_pan = self.env['panaderia.reporte.ventas'].search([
            ('fecha', '=', hoy),
            ('producto_id', '=', self.prod_pan_frances.id)
        ])
        self.assertTrue(reporte_pan, "Debe existir un registro analítico para Pan Francés en el día de hoy.")
        self.assertAlmostEqual(reporte_pan.cantidad_vendida, 10.0, places=2)
        self.assertAlmostEqual(reporte_pan.total_ingresos, 1.00, places=2)

        reporte_pastel = self.env['panaderia.reporte.ventas'].search([
            ('fecha', '=', hoy),
            ('producto_id', '=', self.prod_selva_negra.id)
        ])
        self.assertTrue(reporte_pastel, "Debe existir un registro analítico para Pastel Selva Negra en el día de hoy.")
        self.assertAlmostEqual(reporte_pastel.cantidad_vendida, 1.0, places=2)
        self.assertAlmostEqual(reporte_pastel.total_ingresos, 15.00, places=2)

    def test_02_draft_and_cancelled_sales_excluded_from_report(self):
        """Validar que ventas en borrador o canceladas no se reflejan en las métricas analíticas."""
        # 1. Crear venta en borrador
        venta_draft = self.env['panaderia.venta'].create({
            'cliente_id': self.cliente_test.id,
            'linea_ids': [
                (0, 0, {
                    'producto_id': self.prod_pan_frances.id,
                    'cantidad': 50.0,
                    'precio_unitario': 0.10,
                })
            ]
        })
        self.assertEqual(venta_draft.state, 'draft')

        # 2. Crear venta y cancelarla
        venta_canc = self.env['panaderia.venta'].create({
            'cliente_id': self.cliente_test.id,
            'linea_ids': [
                (0, 0, {
                    'producto_id': self.prod_pan_frances.id,
                    'cantidad': 30.0,
                    'precio_unitario': 0.10,
                })
            ]
        })
        venta_canc.action_confirm()
        venta_canc.action_cancel()
        self.assertEqual(venta_canc.state, 'cancelled')

        # Comprobar que solo ventas confirmadas suman
        hoy = date.today()
        registros = self.env['panaderia.reporte.ventas'].search([
            ('fecha', '=', hoy),
            ('producto_id', '=', self.prod_pan_frances.id)
        ])
        # Las 50 unidades de borrador y las 30 canceladas no deben aparecer sumadas
        total_unidades = sum(registros.mapped('cantidad_vendida'))
        self.assertLessEqual(total_unidades, 10.0, "Las ventas no confirmadas no deben sumarse al reporte analítico.")

    def test_03_top_products_ranking(self):
        """Escenario 2: Detección y ordenamiento de productos más vendidos."""
        # Registrar venta mayoritaria de Pan Francés (100 unidades)
        venta1 = self.env['panaderia.venta'].create({
            'cliente_id': self.cliente_test.id,
            'linea_ids': [
                (0, 0, {
                    'producto_id': self.prod_pan_frances.id,
                    'cantidad': 100.0,
                    'precio_unitario': 0.10,
                })
            ]
        })
        venta1.action_confirm()

        # Registrar venta menor de Pastel (10 unidades)
        venta2 = self.env['panaderia.venta'].create({
            'cliente_id': self.cliente_test.id,
            'linea_ids': [
                (0, 0, {
                    'producto_id': self.prod_selva_negra.id,
                    'cantidad': 10.0,
                    'precio_unitario': 15.00,
                })
            ]
        })
        venta2.action_confirm()

        # Consultar el ranking ordenado por cantidad vendida descendente
        hoy = date.today()
        ranking = self.env['panaderia.reporte.ventas'].search([
            ('fecha', '=', hoy)
        ], order='cantidad_vendida desc')

        self.assertTrue(len(ranking) >= 2, "Deben existir al menos dos productos en el ranking de ventas de hoy.")
        self.assertEqual(ranking[0].producto_id.id, self.prod_pan_frances.id, "Pan Francés debe liderar el ranking con 100+ unidades.")
        self.assertGreater(ranking[0].cantidad_vendida, ranking[1].cantidad_vendida)

    def test_04_low_stock_alert_query(self):
        """Escenario 3: Listado de alerta de stock bajo y detección de reposición."""
        # El producto 'Dona Rellena Crítica' tiene cantidad 3.0 <= stock_minimo 10.0
        self.assertTrue(self.prod_stock_critico.alerta_stock_bajo, "El indicador alerta_stock_bajo debe ser True.")
        self.assertEqual(self.prod_stock_critico.estado_stock, 'bajo')

        # Buscar todos los productos en alerta de stock
        productos_alerta = self.env['panaderia.producto'].search([
            ('alerta_stock_bajo', '=', True),
            ('active', '=', True)
        ])
        self.assertIn(self.prod_stock_critico, productos_alerta, "El producto crítico debe ser detectado en la vista de alerta de stock.")

    def test_05_daily_report_parser_and_wizard(self):
        """Verificación del asistente de impresión y generador de datos QWeb PDF."""
        wizard = self.env['panaderia.reporte.diario.wizard'].create({
            'fecha': date.today()
        })
        self.assertEqual(wizard.fecha, date.today())

        # Ejecutar acción de impresión
        action = wizard.action_print_pdf()
        self.assertEqual(action.get('type'), 'ir.actions.report')
        self.assertEqual(action.get('report_name'), 'Modulo_Odoo.reporte_diario_template')

        # Validar el parser QWeb
        parser = self.env['report.Modulo_Odoo.reporte_diario_template']
        values = parser._get_report_values([wizard.id])
        self.assertIn('total_ingresos_dia', values)
        self.assertIn('total_ordenes_dia', values)
        self.assertIn('top_productos', values)
        self.assertIn('productos_stock_bajo', values)
        self.assertEqual(values['wizard'].id, wizard.id)
