# Quickstart & Verification Guide: Gestión de Catálogo de Productos

**Feature**: `SPEC-1.1.1: Gestión de Catálogo de Productos`  
**Target Module**: `Modulo_Odoo`  
**Related Spec**: [`specs/1-inventory/1.1-product-catalog/1.1.1-product-management/spec.md`](file:///d:/UDB/CICLO-10-2026/DES/LAB/Desafio%203/des-panaderia-erp/specs/1-inventory/1.1-product-catalog/1.1.1-product-management/spec.md)  
**Data Model**: [`data-model.md`](file:///d:/UDB/CICLO-10-2026/DES/LAB/Desafio%203/des-panaderia-erp/specs/1-inventory/1.1-product-catalog/1.1.1-product-management/data-model.md)  
**ORM Contract**: [`contracts/producto-orm-contract.md`](file:///d:/UDB/CICLO-10-2026/DES/LAB/Desafio%203/des-panaderia-erp/specs/1-inventory/1.1-product-catalog/1.1.1-product-management/contracts/producto-orm-contract.md)  

---

## 1. Prerequisites

1. Docker and Docker Compose v2 installed and running on the host system.
2. PostgreSQL and Odoo container services provisioned as defined in `SPEC-0.1.1`.
3. Root environment file `.env` configured with safe database credentials (cloned from `.env.sample`).

---

## 2. Environment Startup & Module Upgrade

### Step 1: Launch Containers
```powershell
docker compose up -d
```

### Step 2: Upgrade / Install Bakery ERP Module
```powershell
docker compose exec odoo odoo -u panaderia_delicias_dulces -d panaderia_db --stop-after-init
```

---

## 3. Automated Verification (Python / Odoo ORM Test Suite)

Execute the unit test suite inside the container to validate constraints and calculations:

```powershell
docker compose exec odoo odoo -d panaderia_db --test-enable --test-tags=panaderia_delicias_dulces.test_producto --stop-after-init
```

### Expected Output:
```text
...
INFO panaderia_db odoo.addons.panaderia_delicias_dulces.tests.test_producto: Starting PanaderiaProductoTestCase.test_01_create_valid_product ...
INFO panaderia_db odoo.addons.panaderia_delicias_dulces.tests.test_producto: Starting PanaderiaProductoTestCase.test_02_invalid_price_zero ...
INFO panaderia_db odoo.addons.panaderia_delicias_dulces.tests.test_producto: Starting PanaderiaProductoTestCase.test_03_negative_cost ...
INFO panaderia_db odoo.addons.panaderia_delicias_dulces.tests.test_producto: Starting PanaderiaProductoTestCase.test_04_duplicate_name_constraint ...
INFO panaderia_db odoo.addons.panaderia_delicias_dulces.tests.test_producto: 4 tests ran in 0.245s, 0 failed, 0 errors.
```

---

## 4. Manual End-to-End Validation Flow

### Test Journey 1: Visual Inspection of Seed Products
1. Open browser and navigate to `http://localhost:8069`.
2. Log in with credentials: `admin` / `admin`.
3. Go to main navigation: **Panadería** $\to$ **Inventario** $\to$ **Productos**.
4. **Verification**: Confirm that the 4 seed products are visible in the list:
   - Pan Francés Tradicional (SKU: `PAN-001`, Costo: `$0.05`, Venta: `$0.10`)
   - Pastel Selva Negra (SKU: `PAS-001`, Costo: `$8.50`, Venta: `$16.00`)
   - Galleta de Avena y Miel (SKU: `GAL-001`, Costo: `$0.35`, Venta: `$0.75`)
   - Café Americano 12oz (SKU: `BEB-001`, Costo: `$0.40`, Venta: `$1.50`)

### Test Journey 2: Create a New Product (Success Path)
1. Click **Nuevo** / **Crear**.
2. Fill fields:
   - Nombre: `Croissant de Mantequilla`
   - Código: `PAN-002`
   - Categoría: `Pan`
   - Costo: `0.45`
   - Precio de Venta: `1.20`
3. Click **Guardar**.
4. **Verification**: Record is saved without errors. `Margen Bruto` calculates `$0.75` and `% Margen` calculates `62.50%`.

### Test Journey 3: Validation Error Handling (Error Path)
1. Click **Nuevo**.
2. Fill fields:
   - Nombre: `Pan Dulce Inválido`
   - Categoría: `Pan`
   - Costo: `-0.10`
   - Precio de Venta: `0.00`
3. Click **Guardar**.
4. **Verification**: System rejects creation with dialog: *"El precio de venta debe ser un valor estrictamente mayor a $0.00."* or *"El costo de producción no puede ser un valor negativo."*
