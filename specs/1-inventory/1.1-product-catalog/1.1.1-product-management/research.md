# Phase 0: Outline & Research - Gestión de Catálogo de Productos

**Feature**: `SPEC-1.1.1: Gestión de Catálogo de Productos`  
**Branch / Directory**: `specs/1-inventory/1.1-product-catalog/1.1.1-product-management`  
**Date**: 2026-09-29  
**Status**: Completed  

---

## 1. Executive Summary & Objective

This research resolves all technical decisions and unknowns required to implement the Product Catalog Management module (`panaderia.producto`) for Panadería "Delicias Dulces" ERP. The module operates as the foundational data master for the inventory control (`SPEC-1.2.1`), point of sale (`SPEC-2.1.1`), customer purchases tracking (`SPEC-3.1.1`), and invoicing (`SPEC-4.1.1`) flows.

---

## 2. Research Findings & Technical Decisions

### Decision 1: Odoo Model Architecture & Base Class Selection
* **Decision**: Implement a dedicated, lightweight custom model `panaderia.producto` inheriting directly from `models.Model` rather than extending Odoo's standard `product.template` / `product.product`.
* **Rationale**:
  * Extending standard `product.template` introduces substantial overhead (attributes matrix, multi-uom, complex procurement rules, automated accounting journals) unnecessary for the academic scope of Desafío 3.
  * Creating `panaderia.producto` guarantees clean encapsulation, predictable database schema migrations, and 100% compliance with Principle I (Odoo Modular Architecture & MVC Separation) and Principle V (Operational Usability).
* **Alternatives Considered**:
  * *Option A: Inherit `product.template` / `product.product`*: Rejected because it introduces dozens of unused standard views, fields, and complex relational constraints that clutter UI ergonomics and hinder turnkey demo evaluation.
  * *Option B: Raw PostgreSQL schema with custom UI*: Rejected because it violates Odoo MVC framework requirements.

### Decision 2: Dual-Layer Data Integrity & Validation Architecture
* **Decision**: Enforce validation rules at two complementary layers:
  1. **Database Layer (SQL Constraints)**: Declare `_sql_constraints` to guarantee uniqueness on `name`.
  2. **Application Layer (Python ORM Decorators)**: Implement `@api.constrains('precio_venta', 'costo')` to validate commercial bounds (`precio_venta > 0.0` and `costo >= 0.0`).
* **Rationale**:
  * PostgreSQL UNIQUE constraint prevents race conditions during concurrent product creation.
  * Python `@api.constrains` provides user-friendly, localized Spanish error dialogs (`ValidationError`) directly in the web client without exposing raw SQL errors.
* **Alternatives Considered**:
  * *Option A: Only UI-level validation (HTML/XML attributes)*: Rejected because RPC/API calls or script imports could bypass browser validation.
  * *Option B: Database trigger functions*: Rejected because it bypasses Odoo ORM error handling and produces unformatted database exceptions.

### Decision 3: Categorization & Relational Integrity
* **Decision**: Model `categoria_id` as `fields.Many2one('panaderia.categoria', string='Categoría', required=True, ondelete='restrict')`.
* **Rationale**:
  * `ondelete='restrict'` prevents accidental deletion of product categories that contain active products.
  * Linking with `panaderia.categoria` (`SPEC-1.1.2`) enables structured search filtering, tree grouping, and aggregated inventory reporting.
* **Alternatives Considered**:
  * *Option A: Selection field (`selection=[('pan', 'Pan'), ...])`*: Rejected because selection fields cannot be dynamically extended by bakery administrators without code changes.

### Decision 4: Archival vs Physical Deletion (Data Lifecycle)
* **Decision**: Implement Odoo's native active archiving mechanism (`active = fields.Boolean(string='Activo', default=True)`), and override the `unlink()` method to prevent hard deletion of products referenced in historical sales orders or invoices.
* **Rationale**:
  * Preserves historical sales records and invoice audit trails while allowing operators to hide discontinued bakery items from POS pickers and active listings.
* **Alternatives Considered**:
  * *Option A: Unrestricted `unlink()`*: Rejected because deleting products would cause cascading foreign key errors or orphan sales order lines.

### Decision 5: Role-Based Access Control (RBAC) & Least Privilege
* **Decision**: Define two granular security groups in `security/res_groups.xml` (or `security/security.xml`) and map them in `security/ir.model.access.csv`:
  * `group_panaderia_user` (Operador de Panadería): Read (`1`), Write (`1`), Create (`1`), Unlink (`0`).
  * `group_panaderia_manager` (Administrador de Panadería): Read (`1`), Write (`1`), Create (`1`), Unlink (`1`).
* **Rationale**:
  * Strictly complies with ISO-27001 Principle of Least Privilege and Constitution Principle I. Standard cashiers and bakers cannot permanently destroy catalog master data.

### Decision 6: Hot-Reloading & Local Docker Provisioning Parity
* **Decision**: Mount local addon folder `./Modulo_Odoo` to `/mnt/extra-addons/panaderia` in `docker-compose.yml`, using development command parameters `--dev=xml,reload` in Odoo configuration.
* **Rationale**:
  * Enables instant reflection of XML view modifications and rapid Python model upgrades via `odoo -u panaderia_delicias_dulces -d panaderia_db --stop-after-init`.
* **Alternatives Considered**:
  * *Option A: Copying files inside container image*: Rejected because it requires full container rebuilds on every view tweak.

---

## 3. Technology Matrix

| Parameter | Specification |
| :--- | :--- |
| **Language & Runtime** | Python 3.10+ |
| **Framework** | Odoo 16.0 / 17.0 / 18.0 Community Edition (ORM, QWeb, XML Views) |
| **Database** | PostgreSQL 15 / 16 Alpine |
| **Container Engine** | Docker & Docker Compose v2 |
| **Testing Framework** | `odoo.tests.common.TransactionCase` (Python Unit Testing) |
| **Localization** | Spanish (es_ES / es_SV) for all UI labels, models, and error messages |

---

## 4. Risks and Mitigations

| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| Negative profit margins when `precio_venta < costo` | Financial / Operational | Add visual computed badge/warning on the form view alerting the operator before saving. |
| Duplicate product SKU/Code collisions | Data Integrity | Add SQL unique constraint on `codigo` (when provided) and normalize whitespace on input. |
| Product deletion breaking sales history | Audit Integrity | Override `unlink()` to block removal if `panaderia.venta.linea` records reference the item; enforce `active=False` archival. |
