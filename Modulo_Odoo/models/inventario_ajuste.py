# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class PanaderiaInventarioAjuste(models.Model):
    _name = 'panaderia.inventario.ajuste'
    _description = 'Ajuste Manual de Inventario'
    _order = 'fecha desc, id desc'

    producto_id = fields.Many2one(
        comodel_name='panaderia.producto',
        string='Producto',
        required=True,
        ondelete='cascade',
        help='Producto al que se aplicará el ajuste de existencias.'
    )
    fecha = fields.Datetime(
        string='Fecha',
        default=fields.Datetime.now,
        required=True,
        help='Fecha y hora en que se realiza el movimiento de inventario.'
    )
    tipo = fields.Selection(
        selection=[
            ('entrada', 'Entrada de Producción'),
            ('salida', 'Merma / Desperdicio'),
            ('conteo', 'Ajuste de Conteo')
        ],
        string='Tipo de Ajuste',
        required=True,
        default='entrada',
        help='Naturaleza del ajuste: ingreso de cocina/horno, merma por desecho o corrección por conteo físico.'
    )
    cantidad = fields.Float(
        string='Cantidad',
        required=True,
        digits=(10, 2),
        help='Cantidad de unidades a ajustar.'
    )
    motivo = fields.Char(
        string='Motivo / Observación',
        required=True,
        help='Justificación del ajuste o referencia de lote/producción.'
    )
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Responsable',
        default=lambda self: self.env.user,
        required=True,
        help='Usuario responsable de la operación.'
    )

    @api.constrains('cantidad', 'tipo')
    def _check_cantidad(self):
        for rec in self:
            if rec.tipo in ('entrada', 'salida') and rec.cantidad <= 0.0:
                raise ValidationError("La cantidad para un ajuste de entrada o salida debe ser estrictamente mayor a 0.")
            if rec.tipo == 'conteo' and rec.cantidad < 0.0:
                raise ValidationError("La cantidad para un ajuste por conteo no puede ser un valor negativo.")

    @api.model_create_multi
    def create(self, vals_list):
        records = super(PanaderiaInventarioAjuste, self).create(vals_list)
        for rec in records:
            # Control de permisos para tipos de ajuste 'salida' y 'conteo'
            if rec.tipo in ('salida', 'conteo'):
                is_manager = (
                    self.env.user.has_group('panaderia.group_panaderia_manager')
                    or self.env.user.has_group('Modulo_Odoo.group_panaderia_manager')
                    or self.env.is_admin()
                )
                if not is_manager:
                    raise UserError("Solo los administradores o supervisores de panadería están autorizados para registrar mermas o ajustes directos de conteo.")

            # Actualización del stock del producto
            if rec.tipo == 'entrada':
                rec.producto_id.cantidad_disponible += rec.cantidad
            elif rec.tipo == 'salida':
                nueva_cantidad = rec.producto_id.cantidad_disponible - rec.cantidad
                if nueva_cantidad < 0.0:
                    raise UserError(f"No hay suficiente stock disponible para realizar la salida. Stock actual de {rec.producto_id.name}: {rec.producto_id.cantidad_disponible}")
                rec.producto_id.cantidad_disponible = nueva_cantidad
            elif rec.tipo == 'conteo':
                rec.producto_id.cantidad_disponible = rec.cantidad
        return records
