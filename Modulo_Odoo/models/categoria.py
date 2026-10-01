# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PanaderiaCategoria(models.Model):
    _name = 'panaderia.categoria'
    _description = 'Categoría de Productos de Panadería'
    _order = 'sequence, name asc'

    name = fields.Char(
        string='Nombre de la Categoría',
        required=True,
        index=True,
        help='Nombre comercial o denominación de la categoría de productos.'
    )
    codigo = fields.Char(
        string='Código Corto',
        size=10,
        required=True,
        copy=False,
        index=True,
        help='Código alfanumérico corto o prefijo de la categoría (e.g. PAN, PAS, GAL, BEB).'
    )
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Orden de visualización y prioridad en listas y menús.'
    )
    descripcion = fields.Text(
        string='Descripción',
        help='Notas descriptivas sobre los tipos de productos y variedades que abarca esta categoría.'
    )
    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Permite ocultar la categoría sin eliminar los registros históricos.'
    )
    producto_ids = fields.One2many(
        comodel_name='panaderia.producto',
        inverse_name='categoria_id',
        string='Productos Asociados',
        help='Listado de productos pertenecientes a esta categoría.'
    )
    total_productos = fields.Integer(
        string='Total Productos',
        compute='_compute_total_productos',
        store=True,
        help='Cantidad total de productos registrados bajo esta categoría.'
    )

    _sql_constraints = [
        ('categoria_name_unique', 'UNIQUE(name)', 'Ya existe una categoría con este nombre. Debe ser único.'),
        ('categoria_codigo_unique', 'UNIQUE(codigo)', 'Ya existe una categoría con este código / prefijo.'),
    ]

    @api.depends('producto_ids')
    def _compute_total_productos(self):
        """Calcula de forma reactiva y almacena el conteo de productos vinculados."""
        for rec in self:
            rec.total_productos = len(rec.producto_ids)

    @api.constrains('name', 'codigo')
    def _check_unique_case_insensitive(self):
        """Valida que el nombre y código de categoría no tengan duplicados ignorando mayúsculas/minúsculas."""
        for rec in self:
            if rec.name:
                duplicate_name = self.search([
                    ('id', '!=', rec.id),
                    ('name', '=ilike', rec.name.strip())
                ])
                if duplicate_name:
                    raise ValidationError(f"Ya existe una categoría registrada con el nombre '{rec.name}'. El nombre debe ser único.")
            if rec.codigo:
                duplicate_code = self.search([
                    ('id', '!=', rec.id),
                    ('codigo', '=ilike', rec.codigo.strip())
                ])
                if duplicate_code:
                    raise ValidationError(f"Ya existe una categoría con el código '{rec.codigo}'. El código debe ser único.")

    def action_view_productos(self):
        """Acción de ventana para visualizar los productos vinculados a esta categoría."""
        self.ensure_one()
        return {
            'name': f'Productos de {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'panaderia.producto',
            'view_mode': 'tree,form',
            'domain': [('categoria_id', '=', self.id)],
            'context': {
                'default_categoria_id': self.id,
                'search_default_categoria_id': self.id,
            }
        }
