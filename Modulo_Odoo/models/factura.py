# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class PanaderiaFactura(models.Model):
    _name = 'panaderia.factura'
    _description = 'Factura Simple de Panadería'
    _order = 'fecha_emision desc, name desc, id desc'

    name = fields.Char(
        string='Número de Factura',
        required=True,
        copy=False,
        readonly=True,
        default='Borrador',
        index=True
    )
    venta_id = fields.Many2one(
        comodel_name='panaderia.venta',
        string='Orden de Venta Origen',
        readonly=True,
        ondelete='set null',
        index=True
    )
    cliente_id = fields.Many2one(
        comodel_name='res.partner',
        string='Cliente',
        required=True,
        index=True
    )
    fecha_emision = fields.Datetime(
        string='Fecha de Emisión',
        default=fields.Datetime.now,
        required=True,
        index=True
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
    ], string='Estado de Pago', default='pending', required=True, index=True)

    @api.model
    def create(self, vals):
        """Asigna automáticamente la secuencia correlativa FAC-XXXX."""
        if vals.get('name', 'Borrador') == 'Borrador' or not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('panaderia.factura.secuencia') or 'FAC-0001'
        return super(PanaderiaFactura, self).create(vals)

    def write(self, vals):
        """Protección de inmutabilidad fiscal contra modificaciones en facturas pagadas."""
        protected_fields = {'monto_total', 'cliente_id', 'venta_id', 'fecha_emision'}
        for rec in self:
            if rec.state == 'paid' and any(f in vals for f in protected_fields):
                raise UserError(_("No se pueden modificar los datos financieros de una factura que ya ha sido pagada."))
        return super(PanaderiaFactura, self).write(vals)

    def unlink(self):
        """Protección de auditoría fiscal impidiendo borrar facturas pagadas."""
        for rec in self:
            if rec.state == 'paid':
                raise UserError(_("No se pueden eliminar facturas en estado Pagada por motivos de auditoría contable."))
        return super(PanaderiaFactura, self).unlink()

    @api.constrains('monto_total')
    def _check_monto_total(self):
        """Valida que el monto total sea no negativo."""
        for rec in self:
            if rec.monto_total < 0.0:
                raise ValidationError(_("El monto total de la factura no puede ser negativo."))

    @api.constrains('venta_id')
    def _check_unique_active_invoice_per_sale(self):
        """Evita la creación de facturas duplicadas para la misma orden de venta."""
        for rec in self:
            if rec.venta_id and rec.state != 'cancelled':
                duplicates = self.search([
                    ('venta_id', '=', rec.venta_id.id),
                    ('id', '!=', rec.id),
                    ('state', '!=', 'cancelled')
                ])
                if duplicates:
                    raise ValidationError(_(
                        f"La orden de venta '{rec.venta_id.name}' ya tiene una factura activa asociada ({duplicates[0].name})."
                    ))

    def action_register_payment(self):
        """Registra el cobro en caja de la factura, cambiando a 'paid' y guardando la fecha."""
        for rec in self:
            if rec.state == 'cancelled':
                raise UserError(_("No se puede registrar el pago de una factura cancelada."))
            rec.write({
                'state': 'paid',
                'fecha_pago': fields.Datetime.now(),
            })

    def action_cancel(self):
        """Cancela la factura si está en estado pendiente."""
        for rec in self:
            if rec.state == 'paid':
                raise UserError(_("No se puede cancelar una factura que ya ha sido pagada."))
            rec.write({'state': 'cancelled'})

    def action_view_venta(self):
        """Abre la vista formulario de la orden de venta vinculada."""
        self.ensure_one()
        if not self.venta_id:
            raise UserError(_("Esta factura no cuenta con una orden de venta asociada."))
        return {
            'name': 'Orden de Venta',
            'type': 'ir.actions.act_window',
            'res_model': 'panaderia.venta',
            'view_mode': 'form',
            'res_id': self.venta_id.id,
            'target': 'current',
        }
