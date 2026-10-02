# -*- coding: utf-8 -*-
import uuid
import hashlib
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


def convertir_monto_a_letras(numero):
    """Convierte deterministamente un importe monetario a texto en español."""
    unidades = ["", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE"]
    especiales = {
        10: "DIEZ", 11: "ONCE", 12: "DOCE", 13: "TRECE", 14: "CATORCE", 15: "QUINCE",
        16: "DIECISEIS", 17: "DIECISIETE", 18: "DIECIOCHO", 19: "DIECINUEVE",
        20: "VEINTE", 21: "VEINTIUNO", 22: "VEINTIDOS", 23: "VEINTITRES", 24: "VEINTICUATRO",
        25: "VEINTICINCO", 26: "VEINTISEIS", 27: "VEINTISIETE", 28: "VEINTIOCHO", 29: "VEINTINUEVE"
    }
    decenas = ["", "DIEZ", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"]
    centenas = [
        "", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS",
        "QUINIENTOS", "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"
    ]

    def _convertir_grupo(n):
        if n == 0:
            return ""
        if n == 100:
            return "CIEN"
        c = n // 100
        d_u = n % 100
        d = d_u // 10
        u = d_u % 10
        texto = []
        if c > 0:
            texto.append(centenas[c])
        if d_u in especiales:
            texto.append(especiales[d_u])
        elif d > 0:
            if u > 0:
                texto.append(f"{decenas[d]} Y {unidades[u]}")
            else:
                texto.append(decenas[d])
        elif u > 0:
            texto.append(unidades[u])
        return " ".join(texto)

    try:
        val = float(numero or 0.0)
    except (ValueError, TypeError):
        val = 0.0

    entero = int(val)
    centavos = int(round((val - entero) * 100))
    if centavos >= 100:
        entero += 1
        centavos = 0

    if entero == 0:
        texto_entero = "CERO"
    elif entero < 1000:
        texto_entero = _convertir_grupo(entero)
    elif entero < 1000000:
        miles = entero // 1000
        resto = entero % 1000
        txt_miles = "MIL" if miles == 1 else f"{_convertir_grupo(miles)} MIL"
        txt_resto = _convertir_grupo(resto)
        texto_entero = f"{txt_miles} {txt_resto}".strip()
    else:
        texto_entero = str(entero)

    return f"{texto_entero} CON {centavos:02d}/100"


class PanaderiaFactura(models.Model):
    _name = 'panaderia.factura'
    _description = 'Factura de Panadería y Documento Tributario Electrónico (DTE)'
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

    # =========================================================================
    # CAMPOS OFICIALES DOCUMENTO TRIBUTARIO ELECTRÓNICO (DTE HACIENDA EL SALVADOR)
    # =========================================================================
    codigo_generacion = fields.Char(
        string='Código de Generación DTE',
        copy=False,
        readonly=True,
        index=True,
        help='Identificador universal único (UUID v4) oficial del DTE ante Hacienda.'
    )
    numero_control = fields.Char(
        string='Número de Control DTE',
        copy=False,
        readonly=True,
        index=True,
        help='Número de control correlativo oficial de Hacienda (ej. DTE-01-M001P001-XXXXXXXXXXXXXXX).'
    )
    sello_recepcion = fields.Char(
        string='Sello de Recepción MH',
        copy=False,
        readonly=True,
        help='Cadena de seguridad de control tributario generada para recepción fiscal.'
    )
    modelo_facturacion = fields.Char(
        string='Modelo de Facturación',
        default='Modelo Facturación previo',
        readonly=True
    )
    tipo_transmision = fields.Char(
        string='Tipo de Transmisión',
        default='Transmisión normal',
        readonly=True
    )
    fecha_dte = fields.Datetime(
        string='Fecha y Hora DTE',
        readonly=True,
        copy=False,
        help='Momento cronológico de generación del Documento Tributario Electrónico.'
    )
    condicion_operacion = fields.Selection([
        ('contado', 'CONTADO'),
        ('credito', 'CRÉDITO')
    ], string='Condición de la Operación', default='contado', required=True)

    linea_ids = fields.One2many(
        related='venta_id.linea_ids',
        readonly=True,
        string='Líneas Facturadas'
    )
    monto_letras = fields.Char(
        string='Valor en Letras',
        compute='_compute_monto_letras',
        store=True,
        help='Expresión formal en palabras del importe total en dólares de EE.UU.'
    )
    qr_data = fields.Text(
        string='Contenido QR DTE',
        compute='_compute_qr_data',
        store=True,
        help='Cadena o URL de consulta oficial de Hacienda embebida en el código QR.'
    )

    # Resumen tributario para renderizado en plantilla QWeb
    subtotal_ventas = fields.Float(
        string='Subtotal Ventas',
        compute='_compute_resumen_tributario'
    )
    total_gravada = fields.Float(
        string='Ventas Gravadas',
        compute='_compute_resumen_tributario'
    )
    total_exenta = fields.Float(
        string='Ventas Exentas',
        compute='_compute_resumen_tributario'
    )
    total_no_sujeta = fields.Float(
        string='Ventas No Sujetas',
        compute='_compute_resumen_tributario'
    )
    iva_calculado = fields.Float(
        string='IVA Calculado (13%)',
        compute='_compute_resumen_tributario'
    )

    @api.depends('monto_total')
    def _compute_monto_letras(self):
        for rec in self:
            rec.monto_letras = convertir_monto_a_letras(rec.monto_total)

    @api.depends('codigo_generacion', 'fecha_dte', 'fecha_emision')
    def _compute_qr_data(self):
        for rec in self:
            cod_gen = rec.codigo_generacion or '00000000-0000-0000-0000-000000000000'
            fec = (rec.fecha_dte or rec.fecha_emision or fields.Datetime.now()).strftime('%Y-%m-%d')
            # URL de consulta pública estándar de Hacienda El Salvador para DTE
            rec.qr_data = f"https://admin.factura.gob.sv/consultaPublica?ambiente=01&codGen={cod_gen}&fechaEmi={fec}"

    @api.depends('monto_total')
    def _compute_resumen_tributario(self):
        for rec in self:
            rec.total_gravada = rec.monto_total
            rec.total_exenta = 0.0
            rec.total_no_sujeta = 0.0
            rec.subtotal_ventas = rec.monto_total
            # El IVA en ventas al consumidor final en panaderías está incluido (13% / 1.13)
            rec.iva_calculado = round(rec.monto_total - (rec.monto_total / 1.13), 2) if rec.monto_total > 0 else 0.0

    @api.model
    def create(self, vals):
        """Asigna automáticamente secuencia FAC-XXXX e identificadores oficiales DTE."""
        if vals.get('name', 'Borrador') == 'Borrador' or not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('panaderia.factura.secuencia') or 'FAC-0001'

        # Asignar Código de Generación UUID v4 si no existe
        if not vals.get('codigo_generacion'):
            vals['codigo_generacion'] = str(uuid.uuid4()).upper()

        # Asignar Número de Control DTE
        if not vals.get('numero_control'):
            seq_ctrl = self.env['ir.sequence'].next_by_code('panaderia.factura.dte.control')
            if seq_ctrl:
                vals['numero_control'] = seq_ctrl
            else:
                # Generar correlativo de 15 dígitos con prefijo oficial
                last_id = self.search([], order='id desc', limit=1).id or 0
                vals['numero_control'] = f"DTE-01-M001P001-{last_id + 1:015d}"

        # Asignar Sello de Recepción de Hacienda simulado (40 caracteres hex)
        if not vals.get('sello_recepcion'):
            seed_data = f"{vals['codigo_generacion']}:{fields.Datetime.now()}:{vals['name']}"
            vals['sello_recepcion'] = hashlib.sha1(seed_data.encode()).hexdigest().upper()

        # Asignar fecha y hora oficial del DTE
        if not vals.get('fecha_dte'):
            vals['fecha_dte'] = fields.Datetime.now()

        return super(PanaderiaFactura, self).create(vals)

    def write(self, vals):
        """Protección de inmutabilidad fiscal contra modificaciones en facturas pagadas."""
        protected_fields = {'monto_total', 'cliente_id', 'venta_id', 'fecha_emision', 'codigo_generacion', 'numero_control'}
        for rec in self:
            if rec.state == 'paid' and any(f in vals for f in protected_fields):
                raise UserError(_("No se pueden modificar los datos financieros o tributarios de una factura pagada."))
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

    def action_print_factura_dte(self):
        """Dispara la generación e impresión del PDF de Factura Electrónica DTE."""
        self.ensure_one()
        report_action = self.env.ref('panaderia.action_report_factura_dte', raise_if_not_found=False)
        if not report_action:
            # Fallback buscando la acción de reporte por xmlid o modelo
            report_action = self.env['ir.actions.report'].search([
                ('report_name', '=', 'panaderia.reporte_factura_dte')
            ], limit=1)
        if not report_action:
            raise UserError(_("No se encontró la acción del reporte de Factura DTE."))
        return report_action.report_action(self, config=False)
