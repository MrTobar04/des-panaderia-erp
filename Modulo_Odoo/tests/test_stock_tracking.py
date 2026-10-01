# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError


class TestStockTracking(TransactionCase):
    """Pruebas unitarias completas para SPEC-1.2.1: Control y Alerta de Stock Mínimo."""

    @classmethod
    def setUpClass(cls):
        super(TestStockTracking, cls).setUpClass()
        cls.categoria = cls.env['panaderia.categoria'].create({
            'name': 'Panes Especiales',
            'codigo': 'CAT-STOCK-TEST',
            'descripcion': 'Categoría para pruebas de stock.'
        })

        cls.producto = cls.env['panaderia.producto'].create({
            'name': 'Baguette Tradicional',
            'codigo': 'BAG-STOCK-01',
            'categoria_id': cls.categoria.id,
            'costo': 0.40,
            'precio_venta': 1.20,
            'cantidad_disponible': 15.0,
            'stock_minimo': 10.0,
        })

        # Usuarios con diferentes roles
        group_user = cls.env.ref('panaderia.group_panaderia_user', raise_if_not_found=False) or cls.env.ref('Modulo_Odoo.group_panaderia_user')
        cls.user_operador = cls.env['res.users'].create({
            'name': 'Operador Juan',
            'login': 'operador_juan',
            'email': 'juan@deliciasdulces.local',
            'groups_id': [(6, 0, [group_user.id])],
        })

        group_manager = cls.env.ref('panaderia.group_panaderia_manager', raise_if_not_found=False) or cls.env.ref('Modulo_Odoo.group_panaderia_manager')
        cls.user_manager = cls.env['res.users'].create({
            'name': 'Gerente Maria',
            'login': 'gerente_maria',
            'email': 'maria@deliciasdulces.local',
            'groups_id': [(6, 0, [group_manager.id])],
        })

    def test_01_stock_estado_normal_initial(self):
        """Verifica que un producto con stock inicial superior al mínimo empiece en estado 'normal'."""
        self.assertEqual(self.producto.estado_stock, 'normal')
        self.assertFalse(self.producto.alerta_stock_bajo)

    def test_02_scenario_1_stock_bajo_trigger(self):
        """Escenario 1: Disparo de alerta por stock bajo cuando la cantidad baja de 15 a 8 (umbral 10)."""
        self.env['panaderia.inventario.ajuste'].with_user(self.user_manager).create({
            'producto_id': self.producto.id,
            'tipo': 'salida',
            'cantidad': 7.0,
            'motivo': 'Venta rápida o consumo de prueba',
        })
        self.assertEqual(self.producto.cantidad_disponible, 8.0)
        self.assertEqual(self.producto.estado_stock, 'bajo')
        self.assertTrue(self.producto.alerta_stock_bajo)

    def test_03_scenario_2_producto_agotado_trigger(self):
        """Escenario 2: Detección de producto agotado cuando la cantidad llega a 0."""
        self.env['panaderia.inventario.ajuste'].with_user(self.user_manager).create({
            'producto_id': self.producto.id,
            'tipo': 'conteo',
            'cantidad': 0.0,
            'motivo': 'Ajuste a cero existencias por inventario físico',
        })
        self.assertEqual(self.producto.cantidad_disponible, 0.0)
        self.assertEqual(self.producto.estado_stock, 'agotado')
        self.assertTrue(self.producto.alerta_stock_bajo)

    def test_04_scenario_3_entrada_produccion(self):
        """Escenario 3: Registro de entrada de producción diaria (+50 unidades)."""
        producto_francés = self.env['panaderia.producto'].create({
            'name': 'Pan Francés',
            'codigo': 'PFR-001',
            'categoria_id': self.categoria.id,
            'costo': 0.15,
            'precio_venta': 0.35,
            'cantidad_disponible': 10.0,
            'stock_minimo': 5.0,
        })
        self.env['panaderia.inventario.ajuste'].with_user(self.user_operador).create({
            'producto_id': producto_francés.id,
            'tipo': 'entrada',
            'cantidad': 50.0,
            'motivo': 'Horneado matutino lote #12',
        })
        self.assertEqual(producto_francés.cantidad_disponible, 60.0)
        self.assertEqual(producto_francés.estado_stock, 'normal')

    def test_05_merma_salida_permissions(self):
        """Verifica que un operador común NO pueda registrar mermas o ajustes directos de conteo."""
        with self.assertRaises(UserError):
            self.env['panaderia.inventario.ajuste'].with_user(self.user_operador).create({
                'producto_id': self.producto.id,
                'tipo': 'salida',
                'cantidad': 2.0,
                'motivo': 'Intento no autorizado de registrar merma',
            })

    def test_06_salida_excede_stock_disponible_raises_user_error(self):
        """Verifica que una salida superior al stock disponible sea rechazada."""
        with self.assertRaises(UserError):
            self.env['panaderia.inventario.ajuste'].with_user(self.user_manager).create({
                'producto_id': self.producto.id,
                'tipo': 'salida',
                'cantidad': 999.0,
                'motivo': 'Salida excesiva',
            })

    def test_07_invalid_negative_stock_minimo(self):
        """Verifica restricción para evitar stock mínimo negativo."""
        with self.assertRaises(ValidationError):
            self.producto.write({'stock_minimo': -5.0})
