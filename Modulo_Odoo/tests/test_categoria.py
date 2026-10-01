# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, AccessError
from psycopg2 import IntegrityError
from odoo.tools import mute_logger


class TestPanaderiaCategoria(TransactionCase):

    def setUp(self):
        super(TestPanaderiaCategoria, self).setUp()
        self.CategoriaModel = self.env['panaderia.categoria']
        self.ProductoModel = self.env['panaderia.producto']

        # Clean up any leftover test records from previous non-isolated runs
        test_codigos = ['PFR', 'BOC', 'TAR', 'TAR2', 'BBC', 'NAV', 'VER']
        leftover_prods = self.ProductoModel.search([('codigo', 'in', ['BOC-001', 'BOC-002', 'NAV-001'])])
        if leftover_prods:
            leftover_prods.unlink()
        leftover_cats = self.CategoriaModel.search([('codigo', 'in', test_codigos)])
        if leftover_cats:
            leftover_cats.unlink()

        # Ensure seed categories exist or fetch them
        self.cat_pan = self.CategoriaModel.search([('codigo', '=', 'PAN')], limit=1)
        if not self.cat_pan:
            self.cat_pan = self.CategoriaModel.create({
                'name': 'Pan',
                'codigo': 'PAN',
                'sequence': 10,
                'descripcion': 'Variedad de panes tradicionales y artesanales.'
            })

        self.cat_pastel = self.CategoriaModel.search([('codigo', '=', 'PAS')], limit=1)
        if not self.cat_pastel:
            self.cat_pastel = self.CategoriaModel.create({
                'name': 'Pastel',
                'codigo': 'PAS',
                'sequence': 20,
                'descripcion': 'Pasteles para eventos y postres.'
            })

    def test_01_seed_categories_loaded(self):
        """Verifica que las 4 categorías estándar de panadería existan en el sistema."""
        codigos = ['PAN', 'PAS', 'GAL', 'BEB']
        for cod in codigos:
            categoria = self.CategoriaModel.search([('codigo', '=', cod)], limit=1)
            self.assertTrue(categoria, f"La categoría con código '{cod}' debe existir en el sistema.")
            self.assertTrue(categoria.name, f"La categoría con código '{cod}' debe tener un nombre asignado.")

    def test_02_create_custom_category(self):
        """Valida la creación correcta de una nueva categoría de panadería."""
        nueva_cat = self.CategoriaModel.create({
            'name': 'Postres Fríos',
            'codigo': 'PFR',
            'sequence': 50,
            'descripcion': 'Gelatinas, mousses y postres refrigerados.',
            'active': True,
        })
        self.assertEqual(nueva_cat.name, 'Postres Fríos')
        self.assertEqual(nueva_cat.codigo, 'PFR')
        self.assertEqual(nueva_cat.sequence, 50)
        self.assertEqual(nueva_cat.total_productos, 0)
        self.assertTrue(nueva_cat.active)

    def test_03_compute_total_productos(self):
        """Comprueba el cálculo dinámico y reactivo del campo total_productos."""
        test_cat = self.CategoriaModel.create({
            'name': 'Bocadillos',
            'codigo': 'BOC',
            'sequence': 60,
        })
        self.assertEqual(test_cat.total_productos, 0)

        # Crear 2 productos asignados a esta categoría
        prod1 = self.ProductoModel.create({
            'name': 'Mini Empanada de Pollo',
            'codigo': 'BOC-001',
            'categoria_id': test_cat.id,
            'costo': 0.30,
            'precio_venta': 0.75,
        })
        test_cat._compute_total_productos()
        self.assertEqual(test_cat.total_productos, 1)

        prod2 = self.ProductoModel.create({
            'name': 'Mini Croissant Jamón y Queso',
            'codigo': 'BOC-002',
            'categoria_id': test_cat.id,
            'costo': 0.40,
            'precio_venta': 1.00,
        })
        test_cat._compute_total_productos()
        self.assertEqual(test_cat.total_productos, 2)

        # Reasignar un producto a otra categoría
        prod1.categoria_id = self.cat_pan.id
        test_cat._compute_total_productos()
        self.assertEqual(test_cat.total_productos, 1)

    def test_04_duplicate_name_case_insensitive_validation(self):
        """Verifica que no se permita registrar dos categorías con el mismo nombre (case-insensitive)."""
        self.CategoriaModel.create({
            'name': 'Tartas Finas',
            'codigo': 'TAR',
        })

        with self.assertRaises(ValidationError):
            self.CategoriaModel.create({
                'name': 'tartas finas',  # Misma categoría en minúsculas
                'codigo': 'TAR2',
            })

    def test_05_duplicate_codigo_case_insensitive_validation(self):
        """Verifica que no se permita registrar dos categorías con el mismo código / prefijo."""
        self.CategoriaModel.create({
            'name': 'Bebidas Calientes',
            'codigo': 'BBC',
        })

        with self.assertRaises(ValidationError):
            self.CategoriaModel.create({
                'name': 'Bebidas Calientes Especiales',
                'codigo': 'bbc',  # Mismo código en minúsculas
            })

    def test_06_restrict_deletion_with_products(self):
        """Verifica que no se pueda eliminar una categoría que contiene productos vinculados (ondelete='restrict')."""
        cat_temp = self.CategoriaModel.create({
            'name': 'Temporada Navideña',
            'codigo': 'NAV',
        })

        self.ProductoModel.create({
            'name': 'Pan de Pascua Navideño',
            'codigo': 'NAV-001',
            'categoria_id': cat_temp.id,
            'costo': 2.50,
            'precio_venta': 6.00,
        })

        with self.assertRaises(Exception):
            with mute_logger('odoo.sql_db'):
                cat_temp.unlink()

    def test_07_action_view_productos(self):
        """Verifica que la acción del Smart Button retorne la vista filtrada por categoría."""
        action = self.cat_pan.action_view_productos()
        self.assertEqual(action['res_model'], 'panaderia.producto')
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertIn(('categoria_id', '=', self.cat_pan.id), action['domain'])
        self.assertEqual(action['context']['default_categoria_id'], self.cat_pan.id)

    def test_08_archive_and_reactivate_category(self):
        """Verifica el archivado y posterior reactivación lógica de una categoría."""
        cat_archive = self.CategoriaModel.create({
            'name': 'Edición Limitada Verano',
            'codigo': 'VER',
            'active': True,
        })
        self.assertTrue(cat_archive.active)

        # Archivar
        cat_archive.active = False
        self.assertFalse(cat_archive.active)

        # Reactivar
        cat_archive.active = True
        self.assertTrue(cat_archive.active)
