-- =====================================================================
-- REY Inventarios - Prueba CRUD directa sobre la base de datos
-- Ejecutar en pgAdmin (Query Tool sobre rey_inventarios) o con psql:
--   psql -h localhost -U rey_user -d rey_inventarios -f prueba_crud.sql
-- (en pgAdmin se pueden ignorar las líneas que empiezan por \echo)
-- =====================================================================
\echo '--- 1. CREATE: insertar producto de prueba ---'
INSERT INTO productos (bodega_id, nombre, sku, precio, stock_actual, dirty)
SELECT id, 'Producto prueba despliegue', 'PRB-001', 10000, 10, false FROM bodegas WHERE nombre = 'General'
RETURNING id, nombre, precio, stock_actual;

\echo '--- 2. READ: consultar el producto ---'
SELECT p.nombre, b.nombre AS bodega, p.precio, p.stock_actual
FROM productos p JOIN bodegas b ON b.id = p.bodega_id
WHERE p.sku = 'PRB-001';

\echo '--- 3. UPDATE: modificar precio y stock ---'
UPDATE productos SET precio = 12500, stock_actual = 15 WHERE sku = 'PRB-001'
RETURNING nombre, precio, stock_actual;

\echo '--- 4. DELETE: eliminar el producto ---'
DELETE FROM productos WHERE sku = 'PRB-001' RETURNING nombre;

\echo '--- 5. Verificación: el producto ya no existe (debe dar 0) ---'
SELECT count(*) AS quedan FROM productos WHERE sku = 'PRB-001';
