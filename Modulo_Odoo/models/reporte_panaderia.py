# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from datetime import datetime


class PanaderiaReporteVentas(models.Model):
    """Modelo analítico basado en vista SQL para reportes operativos de ventas de panadería."""
    _name = 'panaderia.reporte.ventas'
    _description = 'Análisis de Ventas de Panadería'
    _auto = False
    _order = 'fecha desc, total_ingresos desc, id desc'

    fecha = fields.Date(
        string='Fecha',
        readonly=True,
        help='Fecha en que se confirmó la venta.'
    )
    producto_id = fields.Many2one(
        comodel_name='panaderia.producto',
        string='Producto',
        readonly=True,
        help='Producto de panadería vendido.'
    )
    categoria_id = fields.Many2one(
        comodel_name='panaderia.categoria',
        string='Categoría',
        readonly=True,
        help='Categoría del producto.'
    )
    cantidad_vendida = fields.Float(
        string='Unidades Vendidas',
        readonly=True,
        digits=(10, 2),
        help='Cantidad acumulada de unidades vendidas.'
    )
    total_ingresos = fields.Float(
        string='Total Ingresos ($)',
        readonly=True,
        digits=(10, 2),
        help='Monto total de ingresos generados por el producto en la fecha.'
    )
    precio_promedio = fields.Float(
        string='Precio Promedio ($)',
        readonly=True,
        digits=(10, 2),
        help='Precio promedio de venta por unidad.'
    )
    ordenes_count = fields.Integer(
        string='Órdenes',
        readonly=True,
        help='Número de órdenes de venta confirmadas asociadas.'
    )

    def init(self):
        """Crea o actualiza la vista SQL panaderia_reporte_ventas en PostgreSQL."""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW panaderia_reporte_ventas AS (
                SELECT
                    min(l.id) AS id,
                    v.fecha::date AS fecha,
                    l.producto_id AS producto_id,
                    p.categoria_id AS categoria_id,
                    sum(l.cantidad) AS cantidad_vendida,
                    sum(l.subtotal) AS total_ingresos,
                    CASE 
                        WHEN sum(l.cantidad) > 0 THEN round((sum(l.subtotal) / sum(l.cantidad))::numeric, 2) 
                        ELSE 0.0 
                    END AS precio_promedio,
                    count(DISTINCT v.id) AS ordenes_count
                FROM panaderia_venta_linea l
                JOIN panaderia_venta v ON l.venta_id = v.id
                JOIN panaderia_producto p ON l.producto_id = p.id
                WHERE v.state = 'confirmed'
                GROUP BY v.fecha::date, l.producto_id, p.categoria_id
            )
        """)


class PanaderiaReporteDiarioWizard(models.TransientModel):
    """Asistente para la generación e impresión del Resumen Operativo Diario en PDF."""
    _name = 'panaderia.reporte.diario.wizard'
    _description = 'Asistente de Resumen Operativo Diario'

    fecha = fields.Date(
        string='Fecha del Reporte',
        default=fields.Date.context_today,
        required=True,
        help='Fecha sobre la cual se generará el resumen de ventas y stock.'
    )

    def action_print_pdf(self):
        """Ejecuta y retorna la acción de reporte QWeb PDF."""
        self.ensure_one()
        report_action = (
            self.env.ref('panaderia.action_report_resumen_diario', raise_if_not_found=False)
            or self.env.ref('Modulo_Odoo.action_report_resumen_diario', raise_if_not_found=False)
        )
        if not report_action:
            raise UserError(_("No se encontró la acción de reporte 'action_report_resumen_diario'."))
        return report_action.report_action(self, config=False)


class ReporteDiarioParser(models.AbstractModel):
    """Generador de datos contextuales para la plantilla QWeb del Resumen Operativo Diario."""
    _name = 'report.panaderia.reporte_diario_template'
    _description = 'Parser de Plantilla QWeb Resumen Diario'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['panaderia.reporte.diario.wizard'].browse(docids)
        wizard = docs[0] if docs else False
        fecha_reporte = wizard.fecha if wizard else fields.Date.context_today(self)

        # 1. Ventas del día (Órdenes confirmadas en la fecha)
        ventas_dia = self.env['panaderia.venta'].search([
            ('state', '=', 'confirmed'),
            ('fecha', '>=', datetime.combine(fecha_reporte, datetime.min.time())),
            ('fecha', '<=', datetime.combine(fecha_reporte, datetime.max.time())),
        ])
        total_ingresos_dia = sum(ventas_dia.mapped('total'))
        total_ordenes_dia = len(ventas_dia)
        total_unidades_dia = sum(ventas_dia.mapped('linea_ids.cantidad'))

        # 2. Ranking de productos más vendidos en el día
        top_productos = self.env['panaderia.reporte.ventas'].search([
            ('fecha', '=', fecha_reporte)
        ], order='cantidad_vendida desc', limit=10)

        # 3. Alertas de stock bajo actuales en la panadería
        productos_stock_bajo = self.env['panaderia.producto'].search([
            ('alerta_stock_bajo', '=', True),
            ('active', '=', True)
        ], order='estado_stock desc, cantidad_disponible asc')

        return {
            'doc_ids': docids,
            'doc_model': 'panaderia.reporte.diario.wizard',
            'docs': docs,
            'wizard': wizard,
            'fecha_reporte': fecha_reporte,
            'total_ingresos_dia': total_ingresos_dia,
            'total_ordenes_dia': total_ordenes_dia,
            'total_unidades_dia': total_unidades_dia,
            'top_productos': top_productos,
            'productos_stock_bajo': productos_stock_bajo,
            'company': self.env.company,
        }
