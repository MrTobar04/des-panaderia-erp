# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class PanaderiaVenta(models.Model):
    _name = 'panaderia.venta'
    _description = 'Orden de Venta de Panadería'
    _order = 'fecha desc, name desc, id desc'

    name = fields.Char(
        string='Folio',
        required=True,
        copy=False,
        readonly=True,
        default='Nuevo',
        index=True,
        help='Folio secuencial único de la orden de venta (e.g. VEN-0001).'
    )
    cliente_id = fields.Many2one(
        comodel_name='res.partner',
        string='Cliente',
        required=True,
        index=True,
        help='Cliente que realiza la compra en mostrador o pedido especial.'
    )
    fecha = fields.Datetime(
        string='Fecha de Venta',
        default=fields.Datetime.now,
        required=True,
        index=True,
        help='Fecha y hora en que se registra la venta en la panadería.'
    )
    linea_ids = fields.One2many(
        comodel_name='panaderia.venta.linea',
        inverse_name='venta_id',
        string='Líneas de Venta',
        copy=True,
        help='Productos, cantidades y precios que conforman la orden de venta.'
    )
    total = fields.Float(
        string='Total ($)',
        compute='_compute_total',
        store=True,
        digits=(10, 2),
        help='Importe monetario total calculado como la suma de los subtotales de las líneas.'
    )
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirmed', 'Confirmada'),
        ('cancelled', 'Cancelada')
    ], string='Estado', default='draft', required=True, index=True,
       help='Ciclo de vida de la orden: Borrador (en edición), Confirmada (bloqueada y stock descontado), Cancelada.')

    factura_id = fields.Many2one(
        comodel_name='panaderia.factura',
        string='Factura Asociada',
        readonly=True,
        copy=False,
        help='Comprobante fiscal o factura simple generada a partir de esta venta.'
    )

    @api.depends('linea_ids.subtotal')
    def _compute_total(self):
        for order in self:
            order.total = round(sum(order.linea_ids.mapped('subtotal')), 2)

    @api.constrains('linea_ids')
    def _check_lineas_no_vacias(self):
        for order in self:
            if order.state == 'confirmed' and not order.linea_ids:
                raise ValidationError("No es posible confirmar una orden de venta sin al menos una línea de producto.")

    def action_confirm(self):
        """Confirma la orden de venta, genera secuencia, decrementa existencias y crea factura."""
        for order in self:
            if order.state != 'draft':
                raise UserError("Solo se pueden confirmar órdenes de venta en estado Borrador.")
            if not order.linea_ids:
                raise ValidationError("Debe agregar al menos una línea de producto para confirmar la venta.")

            # 1. Asignar secuencia si es 'Nuevo'
            if order.name == 'Nuevo':
                seq = self.env['ir.sequence'].next_by_code('panaderia.venta.secuencia')
                order.name = seq or 'VEN-0001'

            # 2. Validar existencias y decrementar stock de forma atómica
            for line in order.linea_ids:
                prod = line.producto_id
                if hasattr(prod, 'cantidad_disponible'):
                    if prod.cantidad_disponible < line.cantidad:
                        raise ValidationError(
                            f"Stock insuficiente para el producto '{prod.name}'. "
                            f"Disponible: {prod.cantidad_disponible}, Solicitado: {line.cantidad}."
                        )
                    prod.cantidad_disponible -= line.cantidad

            # 3. Crear factura asociada si el modelo existe
            if 'panaderia.factura' in self.env:
                factura = self.env['panaderia.factura'].create({
                    'name': 'Borrador',
                    'venta_id': order.id,
                    'cliente_id': order.cliente_id.id,
                    'monto_total': order.total,
                    'state': 'pending',
                })
                order.factura_id = factura.id

            # 4. Cambiar estado a confirmada (desencadena recompute en res.partner)
            order.state = 'confirmed'

    def action_cancel(self):
        """Cancela la orden de venta y revierte el stock si estaba confirmada."""
        for order in self:
            if order.state == 'confirmed':
                # Revertir existencias de inventario
                for line in order.linea_ids:
                    prod = line.producto_id
                    if hasattr(prod, 'cantidad_disponible'):
                        prod.cantidad_disponible += line.cantidad
                # Cancelar factura asociada si existe
                if order.factura_id:
                    order.factura_id.state = 'cancelled'
            # Cambiar estado a cancelada (desencadena recompute en res.partner)
            order.state = 'cancelled'

    def action_draft(self):
        """Permite regresar la orden a estado borrador si fue cancelada."""
        for order in self:
            if order.state != 'cancelled':
                raise UserError("Solo se pueden restablecer a borrador órdenes que estén canceladas.")
            order.state = 'draft'

    def action_view_factura(self):
        """Abre la vista formulario de la factura asociada."""
        self.ensure_one()
        if not self.factura_id:
            raise UserError("Esta orden de venta no cuenta con una factura asociada.")
        return {
            'name': 'Factura de Venta',
            'type': 'ir.actions.act_window',
            'res_model': 'panaderia.factura',
            'view_mode': 'form',
            'res_id': self.factura_id.id,
            'target': 'current',
        }

    def action_print_factura_dte(self):
        """Imprime la factura DTE en PDF vinculada a esta orden de venta."""
        self.ensure_one()
        if not self.factura_id:
            raise UserError("Esta orden de venta no cuenta con una factura asociada para imprimir.")
        return self.factura_id.action_print_factura_dte()

    def write(self, vals):
        """Garantiza la inmutabilidad de la orden de venta una vez confirmada."""
        for order in self:
            if order.state == 'confirmed':
                # Permitir cambios de estado o asignación de factura, pero bloquear datos de venta
                forbidden = {'cliente_id', 'linea_ids', 'fecha', 'total'}
                if any(k in vals for k in forbidden):
                    raise UserError("No se pueden alterar líneas, clientes ni importes de una orden de venta ya confirmada.")
        return super(PanaderiaVenta, self).write(vals)

    def unlink(self):
        """Impide la eliminación física de órdenes de venta confirmadas."""
        for order in self:
            if order.state == 'confirmed':
                raise UserError(f"No es posible eliminar la orden de venta confirmada '{order.name}'. Cancele la orden primero.")
        return super(PanaderiaVenta, self).unlink()


class PanaderiaVentaLinea(models.Model):
    _name = 'panaderia.venta.linea'
    _description = 'Línea de Venta de Panadería'
    _order = 'id asc'

    venta_id = fields.Many2one(
        comodel_name='panaderia.venta',
        string='Orden de Venta',
        required=True,
        ondelete='cascade',
        index=True
    )
    producto_id = fields.Many2one(
        comodel_name='panaderia.producto',
        string='Producto',
        required=True,
        ondelete='restrict',
        index=True,
        help='Producto de panadería vendido.'
    )
    cantidad = fields.Float(
        string='Cantidad',
        required=True,
        default=1.0,
        digits=(10, 2),
        help='Cantidad de unidades o piezas vendidas.'
    )
    precio_unitario = fields.Float(
        string='Precio Unitario ($)',
        required=True,
        digits=(10, 2),
        help='Precio unitario aplicado a la venta.'
    )
    subtotal = fields.Float(
        string='Subtotal ($)',
        compute='_compute_subtotal',
        store=True,
        digits=(10, 2),
        help='Subtotal calculado multiplicando cantidad por precio unitario.'
    )

    @api.onchange('producto_id')
    def _onchange_producto_id(self):
        if self.producto_id:
            self.precio_unitario = self.producto_id.precio_venta

    @api.depends('cantidad', 'precio_unitario')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = round(line.cantidad * line.precio_unitario, 2)

    @api.constrains('cantidad', 'precio_unitario')
    def _check_valores_linea(self):
        for line in self:
            if line.cantidad <= 0.0:
                raise ValidationError("La cantidad vendida debe ser estrictamente mayor a 0.00.")
            if line.precio_unitario < 0.0:
                raise ValidationError("El precio unitario no puede ser un valor negativo.")
