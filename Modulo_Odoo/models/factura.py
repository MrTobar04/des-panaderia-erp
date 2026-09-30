# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PanaderiaFactura(models.Model):
    _name = 'panaderia.factura'
    _description = 'Factura Simple de Panadería'
    _order = 'fecha_emision desc, name desc, id desc'

    name = fields.Char(
        string='Número de Factura',
        required=True,
        copy=False,
        readonly=True,
        default='Borrador'
    )
    venta_id = fields.Many2one(
        comodel_name='panaderia.venta',
        string='Orden de Venta Origen',
        readonly=True
    )
    cliente_id = fields.Many2one(
        comodel_name='res.partner',
        string='Cliente',
        required=True
    )
    fecha_emision = fields.Datetime(
        string='Fecha de Emisión',
        default=fields.Datetime.now,
        required=True
    )
    fecha_pago = fields.Datetime(
        string='Fecha de Pago',
        readonly=True
    )
    monto_total = fields.Float(
        string='Monto Total ($)',
        required=True,
        digits=(10, 2)
    )
    metodo_pago = fields.Selection([
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta de Débito / Crédito'),
        ('transferencia', 'Transferencia')
    ], string='Método de Pago', default='efectivo', required=True)
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('paid', 'Pagada'),
        ('cancelled', 'Cancelada')
    ], string='Estado de Pago', default='pending', required=True)

    def action_register_payment(self):
        for rec in self:
            rec.write({
                'state': 'paid',
                'fecha_pago': fields.Datetime.now(),
            })
