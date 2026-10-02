# -*- coding: utf-8 -*-
from psycopg2 import IntegrityError
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from odoo.tools import mute_logger


class TestPanaderiaProducto(TransactionCase):
    """Suite de pruebas unitarias para el modelo panaderia.producto."""

    @classmethod
    def setUpClass(cls):
        super(TestPanaderiaProducto, cls).setUpClass()
        # Crear categoría de prueba
        cls.categoria_pan = cls.env['panaderia.categoria'].create({
            'name': 'Pan de Prueba',
            'codigo': 'PAN-TEST',
            'descripcion': 'Categoría utilizada exclusivamente para pruebas unitarias.',
        })

    def test_01_create_valid_product_and_margin_calc(self):
        """Escenario 1: Creación exitosa y cálculo de margen bruto."""
        producto = self.env['panaderia.producto'].create({
            'name': 'Pan Baguette Francés',
            'codigo': 'BAG-001',
            'categoria_id': self.categoria_pan.id,
            'costo': 0.50,
            'precio_venta': 1.50,
            'descripcion': 'Baguette tradicional de masa madre.',
        })
        self.assertTrue(producto.id, "El producto debe crearse exitosamente.")
        self.assertAlmostEqual(producto.margen_bruto, 1.00, places=2, msg="El margen bruto debe ser 1.50 - 0.50 = 1.00")
        self.assertAlmostEqual(producto.porcentaje_margen, 0.6667, places=2, msg="El porcentaje de margen debe ser (1.00 / 1.50) = 0.6667 (66.67%)")
        self.assertTrue(producto.active, "El producto debe crearse activo por defecto.")

    def test_02_invalid_sale_price_zero_raises_validation_error(self):
        """Escenario 2A: Validación de precio de venta igual a cero."""
        with self.assertRaises(ValidationError):
            self.env['panaderia.producto'].create({
                'name': 'Pan Gratis No Permitido',
                'codigo': 'GRA-001',
                'categoria_id': self.categoria_pan.id,
                'costo': 0.10,
                'precio_venta': 0.0,
            })

    def test_03_invalid_sale_price_negative_raises_validation_error(self):
        """Escenario 2B: Validación de precio de venta negativo."""
        with self.assertRaises(ValidationError):
            self.env['panaderia.producto'].create({
                'name': 'Pan Negativo No Permitido',
                'codigo': 'NEG-001',
                'categoria_id': self.categoria_pan.id,
                'costo': 0.10,
                'precio_venta': -0.50,
            })

    def test_04_invalid_cost_negative_raises_validation_error(self):
        """Escenario 2C: Validación de costo de producción negativo."""
        with self.assertRaises(ValidationError):
            self.env['panaderia.producto'].create({
                'name': 'Pan con Costo Negativo',
                'codigo': 'CST-001',
                'categoria_id': self.categoria_pan.id,
                'costo': -0.25,
                'precio_venta': 1.00,
            })

    @mute_logger('odoo.sql_db')
    def test_05_duplicate_name_raises_sql_constraint(self):
        """Escenario 3A: Restricción de unicidad de nombre de producto."""
        self.env['panaderia.producto'].create({
            'name': 'Quesadilla Especial',
            'codigo': 'QSD-001',
            'categoria_id': self.categoria_pan.id,
            'costo': 1.00,
            'precio_venta': 2.50,
        })
        with self.assertRaises(IntegrityError):
            with self.cr.savepoint():
                self.env['panaderia.producto'].create({
                    'name': 'Quesadilla Especial',
                    'codigo': 'QSD-002',
                    'categoria_id': self.categoria_pan.id,
                    'costo': 1.20,
                    'precio_venta': 3.00,
                })

    @mute_logger('odoo.sql_db')
    def test_06_duplicate_sku_raises_sql_constraint(self):
        """Escenario 3B: Restricción de unicidad de código SKU."""
        self.env['panaderia.producto'].create({
            'name': 'Semita Alta',
            'codigo': 'SEM-001',
            'categoria_id': self.categoria_pan.id,
            'costo': 0.60,
            'precio_venta': 1.25,
        })
        with self.assertRaises(IntegrityError):
            with self.cr.savepoint():
                self.env['panaderia.producto'].create({
                    'name': 'Semita Pacha',
                    'codigo': 'SEM-001',
                    'categoria_id': self.categoria_pan.id,
                    'costo': 0.50,
                    'precio_venta': 1.00,
                })

    def test_07_archive_and_reactivate_product(self):
        """Escenario 4: Ciclo de vida y archivado lógico."""
        producto = self.env['panaderia.producto'].create({
            'name': 'Pan de Temporada Navideña',
            'codigo': 'NAV-001',
            'categoria_id': self.categoria_pan.id,
            'costo': 2.00,
            'precio_venta': 5.00,
            'active': True,
        })
        self.assertTrue(producto.active, "El producto inicial debe estar activo.")
        producto.write({'active': False})
        self.assertFalse(producto.active, "El producto debe archivarse lógicamente.")
        producto.write({'active': True})
        self.assertTrue(producto.active, "El producto debe poder reactivarse.")
