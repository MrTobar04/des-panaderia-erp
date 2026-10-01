# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class PanaderiaProducto(models.Model):
    _name = 'panaderia.producto'
    _description = 'Producto de Panadería'
    _order = 'name asc, id desc'

    name = fields.Char(
        string='Nombre del Producto',
        required=True,
        index=True,
        help='Nombre comercial único del producto elaborado o vendido en la panadería.'
    )
    codigo = fields.Char(
        string='Código / SKU',
        copy=False,
        index=True,
        help='Identificador único alfanumérico o SKU del producto.'
    )
    categoria_id = fields.Many2one(
        comodel_name='panaderia.categoria',
        string='Categoría',
        required=True,
        ondelete='restrict',
        help='Clasificación a la que pertenece el producto (e.g. Pan, Pastel, Galleta, Bebida).'
    )
    costo = fields.Float(
        string='Costo de Producción ($)',
        required=True,
        default=0.0,
        digits=(10, 2),
        help='Costo unitario de los ingredientes y elaboración del producto.'
    )
    precio_venta = fields.Float(
        string='Precio de Venta ($)',
        required=True,
        default=0.0,
        digits=(10, 2),
        help='Precio unitario de venta al público cobrado al cliente.'
    )
    margen_bruto = fields.Float(
        string='Margen Bruto ($)',
        compute='_compute_margenes',
        store=True,
        digits=(10, 2),
        help='Diferencia monetaria directa entre precio de venta y costo de producción.'
    )
    porcentaje_margen = fields.Float(
        string='% Margen',
        compute='_compute_margenes',
        store=True,
        digits=(5, 2),
        help='Margen de ganancia porcentual sobre el precio de venta.'
    )
    cantidad_disponible = fields.Float(
        string='Stock Disponible',
        default=0.0,
        required=True,
        digits=(10, 2),
        help='Cantidad física de unidades disponibles en la panadería.'
    )
    stock_minimo = fields.Float(
        string='Stock Mínimo de Alerta',
        default=5.0,
        required=True,
        digits=(10, 2),
        help='Umbral mínimo configurable de existencias para emitir alerta de reabastecimiento.'
    )
    alerta_stock_bajo = fields.Boolean(
        string='Alerta Stock Bajo',
        compute='_compute_estado_stock',
        store=True,
        help='Indicador binario de advertencia activo cuando el stock cae a nivel bajo o nulo.'
    )
    estado_stock = fields.Selection(
        selection=[
            ('normal', 'Normal'),
            ('bajo', 'Bajo Stock'),
            ('agotado', 'Agotado')
        ],
        string='Estado de Stock',
        compute='_compute_estado_stock',
        store=True,
        default='agotado',
        help='Estado cualitativo del inventario: verde (normal), amarillo (bajo stock) y rojo (agotado).'
    )
    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Permite ocultar o descontinuar el producto sin eliminar registros históricos asociados.'
    )
    descripcion = fields.Text(
        string='Descripción / Notas',
        help='Información detallada de ingredientes, alérgenos, presentación o modo de conservación.'
    )

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Ya existe un producto registrado con este nombre. El nombre debe ser único.'),
        ('codigo_unique', 'UNIQUE(codigo)', 'Ya existe un producto registrado con este código / SKU.'),
    ]

    @api.depends('cantidad_disponible', 'stock_minimo')
    def _compute_estado_stock(self):
        """Calcula el estado de stock (normal, bajo, agotado) y activa la alerta visual."""
        for rec in self:
            if rec.cantidad_disponible <= 0.0:
                rec.estado_stock = 'agotado'
                rec.alerta_stock_bajo = True
            elif rec.cantidad_disponible <= rec.stock_minimo:
                rec.estado_stock = 'bajo'
                rec.alerta_stock_bajo = True
            else:
                rec.estado_stock = 'normal'
                rec.alerta_stock_bajo = False

    @api.depends('precio_venta', 'costo')
    def _compute_margenes(self):
        """Calcula el margen bruto en dólares y el porcentaje de margen sobre el precio de venta."""
        for record in self:
            record.margen_bruto = record.precio_venta - record.costo
            if record.precio_venta > 0.0:
                record.porcentaje_margen = (record.margen_bruto / record.precio_venta) * 100.0
            else:
                record.porcentaje_margen = 0.0

    @api.constrains('precio_venta', 'costo')
    def _check_precios_y_costos(self):
        """Valida que los valores financieros cumplan con las reglas de negocio de la panadería."""
        for record in self:
            if record.precio_venta <= 0.0:
                raise ValidationError("El precio de venta debe ser un valor strictly mayor a $0.00.")
            if record.costo < 0.0:
                raise ValidationError("El costo de producción no puede ser un valor negativo.")

    @api.constrains('stock_minimo')
    def _check_stock_values(self):
        """Valida que los parámetros de inventario sean consistentes."""
        for record in self:
            if record.stock_minimo < 0.0:
                raise ValidationError("El stock mínimo no puede ser un valor negativo.")

    def action_ajustar_stock(self):
        """Abre el asistente en ventana emergente para registrar un ajuste de inventario."""
        self.ensure_one()
        return {
            'name': 'Ajustar Inventario de Producto',
            'type': 'ir.actions.act_window',
            'res_model': 'panaderia.inventario.ajuste',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_producto_id': self.id,
            }
        }

    def unlink(self):
        """Impide la eliminación física si existen transacciones o líneas vinculadas."""
        # Se verifica si existen modelos de líneas de venta instalados en el entorno
        if 'panaderia.venta.linea' in self.env:
            lineas_venta = self.env['panaderia.venta.linea'].search_count([('producto_id', 'in', self.ids)])
            if lineas_venta > 0:
                raise UserError(
                    "No es posible eliminar productos que cuentan con historial de órdenes de venta. "
                    "En su lugar, utilice la función de archivar (desactivar)."
                )
        return super(PanaderiaProducto, self).unlink()
