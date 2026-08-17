-- MySQL 8+ equivalent teaching source schema. Execute in a dedicated source DB.
CREATE TABLE IF NOT EXISTS suppliers (
  supplier_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  supplier_code VARCHAR(40) NOT NULL UNIQUE,
  supplier_name VARCHAR(160) NOT NULL,
  region VARCHAR(80) NOT NULL
);
CREATE TABLE IF NOT EXISTS materials (
  material_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  material_code VARCHAR(40) NOT NULL UNIQUE,
  material_name VARCHAR(160) NOT NULL,
  product_line VARCHAR(80) NOT NULL,
  safety_stock DECIMAL(14,2) NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS production_work_orders (
  work_order_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  order_number VARCHAR(40) NOT NULL UNIQUE,
  factory VARCHAR(80) NOT NULL,
  product_line VARCHAR(80) NOT NULL,
  planned_quantity DECIMAL(14,2) NOT NULL,
  completed_quantity DECIMAL(14,2) NOT NULL DEFAULT 0,
  planned_date DATE NOT NULL,
  INDEX idx_work_orders_factory_date (factory, planned_date)
);
CREATE TABLE IF NOT EXISTS inventory_balances (
  inventory_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  material_id BIGINT NOT NULL,
  factory VARCHAR(80) NOT NULL,
  quantity DECIMAL(14,2) NOT NULL DEFAULT 0,
  snapshot_date DATE NOT NULL,
  CONSTRAINT fk_inventory_material FOREIGN KEY (material_id) REFERENCES materials(material_id),
  INDEX idx_inventory_factory_snapshot (factory, snapshot_date)
);
INSERT IGNORE INTO suppliers (supplier_code, supplier_name, region) VALUES
  ('SUP-001', '华东精密供应', '华东'), ('SUP-002', '西南新材', '西南');
INSERT IGNORE INTO materials (material_code, material_name, product_line, safety_stock) VALUES
  ('MAT-001', '控制器总成', '智能控制', 100),
  ('MAT-002', '动力模块', '新能源', 80),
  ('MAT-003', '传感器组件', '智能控制', 120);
INSERT IGNORE INTO production_work_orders
  (order_number, factory, product_line, planned_quantity, completed_quantity, planned_date)
VALUES
  ('WO-20260801', '成都工厂', '智能控制', 1000, 930, CURRENT_DATE - INTERVAL 5 DAY),
  ('WO-20260802', '苏州工厂', '新能源', 800, 760, CURRENT_DATE - INTERVAL 4 DAY),
  ('WO-20260803', '成都工厂', '新能源', 600, 510, CURRENT_DATE - INTERVAL 3 DAY);
