# -*- coding: utf-8 -*-
{
    'name': 'Panadería Delicias Dulces - Gestión ERP',
    'version': '1.0.0',
    'category': 'Sales/Inventory',
    'summary': 'Sistema ERP a medida para la gestión de panadería: catálogo, inventario, ventas, facturación y reportes.',
    'description': """
Panadería "Delicias Dulces" ERP
================================
Módulo modular para la gestión integral de operaciones de panadería:
- Catálogo de productos con costos, precios de venta y cálculo automático de márgenes.
- Clasificación por categorías de productos de panadería (Pan, Pastel, Galleta, Bebida).
- Control de inventario y alertas de stock mínimo.
- Proceso ágil de órdenes de venta y facturación simple.
- Reportes operativos de rentabilidad, ventas del día, top de productos y alertas de reposición.
    """,
    'author': 'Equipo de Desarrollo Delicias Dulces',
    'website': 'https://panaderia-deliciasdulces.local',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/company_data.xml',
        'data/categoria_data.xml',
        'data/producto_data.xml',
        'data/cliente_data.xml',
        'data/venta_sequence.xml',
        'data/factura_sequence.xml',
        'views/categoria_views.xml',
        'views/producto_views.xml',
        'views/inventario_views.xml',
        'views/venta_views.xml',
        'views/cliente_views.xml',
        'views/factura_views.xml',
        'views/reporte_views.xml',
        'views/login_templates.xml',
        'report/reporte_diario_template.xml',
        'report/reporte_factura_dte_template.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
