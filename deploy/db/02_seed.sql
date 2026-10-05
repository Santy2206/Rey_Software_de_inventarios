-- =====================================================================
-- REY Inventarios - Datos iniciales para el ambiente de pruebas
-- Usuarios de prueba:
--   admin    / admin123     (rol administrador)
--   empleado / empleado123  (rol empleado)
-- Las contraseñas se guardan como SHA-256 (igual que auth_service.py).
-- Los registros se marcan dirty = false para que NO se sincronicen a la nube.
-- =====================================================================
SET search_path TO public;

INSERT INTO usuarios (name, email, rol, password_hash) VALUES
  ('admin',    'admin@rey.local',    'administrador', encode(sha256('admin123'::bytea), 'hex')),
  ('empleado', 'empleado@rey.local', 'empleado',      encode(sha256('empleado123'::bytea), 'hex'))
ON CONFLICT (name) DO NOTHING;

INSERT INTO bodegas (nombre, ubicacion, es_principal, orden, descripcion, dirty) VALUES
  ('General',    'Bogotá - Sede principal', true,  1, 'Bodega general de la empresa', false),
  ('Fragancias', 'Bogotá - Sede principal', false, 2, 'Perfumes y fragancias',        false),
  ('Bala Negra', 'Bogotá - Sede principal', false, 3, 'Envases y accesorios',         false);

INSERT INTO productos (bodega_id, nombre, descripcion, sku, codigo, precio, stock_actual, dirty)
SELECT b.id, p.nombre, p.descripcion, p.sku, p.codigo, p.precio, p.stock, false
FROM (VALUES
  ('Fragancias', 'Esencia Vainilla 30ml',  'Esencia concentrada',   'FRG-001', 'F001', 25000, 40),
  ('Fragancias', 'Esencia Cítrica 30ml',   'Esencia concentrada',   'FRG-002', 'F002', 25000, 35),
  ('Bala Negra', 'Envase atomizador 50ml', 'Envase de vidrio negro','BAL-001', 'B001',  6000, 120),
  ('General',    'Caja de regalo',         'Empaque de cartón',     'GEN-001', 'G001',  3500, 80)
) AS p(bodega, nombre, descripcion, sku, codigo, precio, stock)
JOIN bodegas b ON b.nombre = p.bodega;

INSERT INTO clientes (nombre, telefono, email, es_generico, dirty) VALUES
  ('Cliente genérico', NULL, NULL, true, false),
  ('Cliente de prueba', '3000000000', 'cliente@prueba.com', false, false);
