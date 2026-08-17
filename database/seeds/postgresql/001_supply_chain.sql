-- SupplyMind teaching source database. Run against a dedicated source database,
-- never against the platform PostgreSQL database.
CREATE TABLE IF NOT EXISTS suppliers (
  supplier_id BIGSERIAL PRIMARY KEY,
  supplier_code VARCHAR(40) UNIQUE NOT NULL,
  supplier_name VARCHAR(160) NOT NULL,
  region VARCHAR(80) NOT NULL
);
CREATE TABLE IF NOT EXISTS materials (
  material_id BIGSERIAL PRIMARY KEY,
  material_code VARCHAR(40) UNIQUE NOT NULL,
  material_name VARCHAR(160) NOT NULL,
  product_line VARCHAR(80) NOT NULL,
  safety_stock NUMERIC(14,2) NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS purchase_orders (
  purchase_order_id BIGSERIAL PRIMARY KEY,
  po_number VARCHAR(40) UNIQUE NOT NULL,
  supplier_id BIGINT NOT NULL REFERENCES suppliers(supplier_id),
  planned_date DATE NOT NULL,
  delivered_date DATE,
  status VARCHAR(32) NOT NULL
);
CREATE TABLE IF NOT EXISTS production_work_orders (
  work_order_id BIGSERIAL PRIMARY KEY,
  order_number VARCHAR(40) UNIQUE NOT NULL,
  factory VARCHAR(80) NOT NULL,
  product_line VARCHAR(80) NOT NULL,
  planned_quantity NUMERIC(14,2) NOT NULL,
  completed_quantity NUMERIC(14,2) NOT NULL DEFAULT 0,
  planned_date DATE NOT NULL
);
CREATE TABLE IF NOT EXISTS inventory_balances (
  inventory_id BIGSERIAL PRIMARY KEY,
  material_id BIGINT NOT NULL REFERENCES materials(material_id),
  factory VARCHAR(80) NOT NULL,
  quantity NUMERIC(14,2) NOT NULL DEFAULT 0,
  snapshot_date DATE NOT NULL
);
CREATE TABLE IF NOT EXISTS quality_inspections (
  inspection_id BIGSERIAL PRIMARY KEY,
  work_order_id BIGINT NOT NULL REFERENCES production_work_orders(work_order_id),
  inspected_quantity NUMERIC(14,2) NOT NULL,
  passed_quantity NUMERIC(14,2) NOT NULL,
  inspected_at DATE NOT NULL
);
CREATE TABLE IF NOT EXISTS sales_orders (
  sales_order_id BIGSERIAL PRIMARY KEY,
  order_number VARCHAR(40) UNIQUE NOT NULL,
  factory VARCHAR(80) NOT NULL,
  product_line VARCHAR(80) NOT NULL,
  ordered_quantity NUMERIC(14,2) NOT NULL,
  delivered_quantity NUMERIC(14,2) NOT NULL DEFAULT 0,
  promised_date DATE NOT NULL,
  delivered_date DATE
);
CREATE TABLE IF NOT EXISTS delivery_plans (
  delivery_plan_id BIGSERIAL PRIMARY KEY,
  sales_order_id BIGINT NOT NULL REFERENCES sales_orders(sales_order_id),
  planned_date DATE NOT NULL,
  actual_date DATE
);

INSERT INTO suppliers (supplier_code, supplier_name, region) VALUES
  ('SUP-001', '华东精密供应', '华东'),
  ('SUP-002', '西南新材', '西南')
ON CONFLICT (supplier_code) DO NOTHING;
INSERT INTO materials (material_code, material_name, product_line, safety_stock) VALUES
  ('MAT-001', '控制器总成', '智能控制', 100),
  ('MAT-002', '动力模块', '新能源', 80),
  ('MAT-003', '传感器组件', '智能控制', 120)
ON CONFLICT (material_code) DO NOTHING;

INSERT INTO production_work_orders
  (order_number, factory, product_line, planned_quantity, completed_quantity, planned_date)
VALUES
  ('WO-20260801', '成都工厂', '智能控制', 1000, 930, CURRENT_DATE - 5),
  ('WO-20260802', '苏州工厂', '新能源', 800, 760, CURRENT_DATE - 4),
  ('WO-20260803', '成都工厂', '新能源', 600, 510, CURRENT_DATE - 3)
ON CONFLICT (order_number) DO NOTHING;
INSERT INTO inventory_balances (material_id, factory, quantity, snapshot_date)
SELECT m.material_id, '成都工厂', v.quantity, CURRENT_DATE
FROM materials m
JOIN (VALUES ('MAT-001', 36::numeric), ('MAT-002', 160::numeric), ('MAT-003', 95::numeric)) v(code, quantity)
  ON v.code = m.material_code
WHERE NOT EXISTS (
  SELECT 1 FROM inventory_balances i
  WHERE i.material_id = m.material_id AND i.factory = '成都工厂' AND i.snapshot_date = CURRENT_DATE
);

CREATE INDEX IF NOT EXISTS idx_work_orders_factory_date ON production_work_orders(factory, planned_date);
CREATE INDEX IF NOT EXISTS idx_inventory_factory_snapshot ON inventory_balances(factory, snapshot_date);
CREATE INDEX IF NOT EXISTS idx_purchase_orders_supplier_date ON purchase_orders(supplier_id, planned_date);

-- Run separately as a privileged administrator and replace the password through
-- a secret manager. The application must use this account, never the owner.
-- CREATE ROLE supplymind_readonly LOGIN PASSWORD '<inject-at-deploy-time>';
-- GRANT CONNECT ON DATABASE supplymind_demo TO supplymind_readonly;
-- GRANT USAGE ON SCHEMA public TO supplymind_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO supplymind_readonly;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO supplymind_readonly;
