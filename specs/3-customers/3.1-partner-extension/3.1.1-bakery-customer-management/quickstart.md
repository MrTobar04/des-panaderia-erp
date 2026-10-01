# Quickstart & Verification: SPEC-3.1.1 Extensión y Registro de Clientes

**Branch**: `3.1.1-bakery-customer-management` | **Date**: 2026-09-30 | **Spec**: [`specs/3-customers/3.1-partner-extension/3.1.1-bakery-customer-management/spec.md`](file:///d:/UDB/CICLO-10-2026/DES/LAB/Desafio%203/des-panaderia-erp/specs/3-customers/3.1-partner-extension/3.1.1-bakery-customer-management/spec.md)

---

## 1. Quick Setup & Module Upgrade

1. Ensure the docker containers are active:
   ```powershell
   .\scripts\docker-start.ps1
   ```
2. Upgrade `Modulo_Odoo` to load customer extension models, seed data, and views:
   ```bash
   docker exec -it panaderia_odoo_web odoo -u Modulo_Odoo -d panaderia_db --stop-after-init
   ```

---

## 2. Verification Scenarios

### Scenario 1: Walk-in & Specialized Customer Creation
- Navigate to **Panadería** $\to$ **Clientes**.
- Click **Crear** / **Nuevo**.
- Enter:
  - **Nombre**: `Carlos Mendoza`
  - **Teléfono**: `7123-4567`
  - **Preferencias / Notas**: `Prefiere pan integral y bajo en azúcar.`
- Save the record.
- **Expected**: `es_cliente_panaderia` is `True`, `fecha_registro_panaderia` is populated with today's date, and `total_compras_panaderia` starts at `$0.00`.

### Scenario 2: Cumulative Purchase Update
- Navigate to **Panadería** $\to$ **Ventas** $\to$ **Órdenes de Venta**.
- Create a sale order for `Carlos Mendoza` totaling `$12.50` and click **Confirmar Venta**.
- Create a second sale order for `Carlos Mendoza` totaling `$7.50` and click **Confirmar Venta**.
- Navigate back to **Panadería** $\to$ **Clientes** and open `Carlos Mendoza`.
- **Expected**: `total_compras_panaderia` automatically reflects `$20.00`.

### Scenario 3: Contact List Filtering
- Navigate to **Panadería** $\to$ **Clientes**.
- Verify that standard internal users, system bots, or suppliers without `es_cliente_panaderia = True` are filtered out.
- Only registered bakery customers (including seed `Cliente General / Mostrador`) appear in the active list.
