# -*- coding: utf-8 -*-
from odoo import models, fields


class PanaderiaCategoria(models.Model):
    _name = 'panaderia.categoria'
    _description = 'Categoría de Productos de Panadería'
    _order = 'name asc'

    name = fields.Char(string='Nombre de la Categoría', required=True, index=True)
    codigo = fields.Char(string='Código / Prefijo', copy=False, index=True)
    descripcion = fields.Text(string='Descripción')
    active = fields.Boolean(string='Activo', default=True)

    _sql_constraints = [
        ('categoria_name_unique', 'UNIQUE(name)', 'Ya existe una categoría con este nombre. Debe ser único.'),
        ('categoria_codigo_unique', 'UNIQUE(codigo)', 'Ya existe una categoría con este código / prefijo.'),
    ]
