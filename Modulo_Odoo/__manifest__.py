# -*- coding: utf-8 -*-
{
    'name': 'Panadería Delicias Dulces - Gestión ERP',
    'version': '1.0.0',
    'category': 'Sales/Inventory',
    'summary': 'Sistema ERP a medida para la gestión de panadería: catálogo, inventario, ventas y facturación.',
    'description': """
Panadería "Delicias Dulces" ERP
================================
Módulo modular para la gestión integral de operaciones de panadería:
- Catálogo de productos con costos, precios de venta y cálculo automático de márgenes.
- Clasificación por categorías de productos de panadería (Pan, Pastel, Galleta, Bebida).
- Control de inventario y alertas de stock mínimo.
- Proceso ágil de órdenes de venta y facturación simple.
- Reportes operativos de rentabilidad y ventas.
    """,
    'author': 'Equipo de Desarrollo Delicias Dulces',
    'website': 'https://panaderia-deliciasdulces.local',
    'license': 'LGPL-3',
    'depends': [
        'base',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/categoria_data.xml',
        'data/producto_data.xml',
        'data/venta_sequence.xml',
        'views/categoria_views.xml',
        'views/producto_views.xml',
        'views/venta_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
