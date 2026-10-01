# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    """Extensión del modelo res.partner para la gestión de clientes en Panadería 'Delicias Dulces'."""
    _inherit = 'res.partner'

    es_cliente_panaderia = fields.Boolean(
        string='Es Cliente de Panadería',
        default=True,
        index=True,
        help='Identifica si el contacto es un cliente regular o de mostrador de la panadería.'
    )
    fecha_registro_panaderia = fields.Date(
        string='Fecha de Registro en Panadería',
        default=fields.Date.context_today,
        index=True,
        help='Fecha en la que el cliente fue dado de alta en la panadería.'
    )
    total_compras_panaderia = fields.Float(
        string='Total en Compras ($)',
        compute='_compute_total_compras_panaderia',
        store=True,
        digits=(10, 2),
        help='Suma total monetaria de todas las ventas confirmadas asociadas a este cliente.'
    )
    notas_preferencias = fields.Text(
        string='Preferencias / Notas de Panadería',
        help='Alergias alimentarias, panes preferidos, restricciones dietéticas o solicitudes especiales.'
    )
    venta_panaderia_ids = fields.One2many(
        comodel_name='panaderia.venta',
        inverse_name='cliente_id',
        string='Ventas de Panadería',
        help='Historial completo de órdenes de venta registradas a nombre de este cliente.'
    )
    ventas_panaderia_count = fields.Integer(
        string='Núm. de Ventas',
        compute='_compute_total_compras_panaderia',
        store=True,
        help='Cantidad total de órdenes de venta confirmadas.'
    )

    @api.depends('venta_panaderia_ids.state', 'venta_panaderia_ids.total')
    def _compute_total_compras_panaderia(self):
        """Calcula de forma acumulativa y automática el importe de compras de ventas confirmadas."""
        for partner in self:
            ventas_confirmadas = partner.venta_panaderia_ids.filtered(lambda v: v.state == 'confirmed')
            partner.total_compras_panaderia = round(sum(ventas_confirmadas.mapped('total')), 2)
            partner.ventas_panaderia_count = len(ventas_confirmadas)

    def action_view_panaderia_ventas(self):
        """Acción de ventana para visualizar las órdenes de venta del cliente en modo lista/formulario."""
        self.ensure_one()
        return {
            'name': f'Ventas de {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'panaderia.venta',
            'view_mode': 'tree,form',
            'domain': [('cliente_id', '=', self.id)],
            'context': {'default_cliente_id': self.id},
            'target': 'current',
        }
