import src.sync.sync_service as sync_module
from src.core.local_db import run_query

TABLAS = ["productos", "movimientos", "ventas"]

# --- Simulación de éxito ---------------------------------
class FakeResp:
    data = [{"id": "ok"}]

class FakeTable:
    def __init__(self, name):
        self.name = name
    def upsert(self, payload):
        return self
    def execute(self):
        return FakeResp()

class FakeSupabase:
    def table(self, name):
        return FakeTable(name)

sync_module.supabase = FakeSupabase()

print("=== Sync con conexión simulada (éxito) ===")
for t in TABLAS:
    n = run_query(
        f"SELECT COUNT(*) AS n FROM {t} WHERE dirty = true", fetch_one=True
    )["n"]
    print(f"  {t} dirty antes: {n}")

resultado = sync_module.SyncService.sync_pendientes()
print("Resultado:", resultado)

for t in TABLAS:
    n = run_query(
        f"SELECT COUNT(*) AS n FROM {t} WHERE dirty = true", fetch_one=True
    )["n"]
    print(f"  {t} dirty después: {n}")

# --- Simulación de fallo de red --------------------------
class FakeTableFail:
    def upsert(self, payload):
        return self
    def execute(self):
        raise Exception("Network error: no hay conexion a internet")

class FakeSupabaseFail:
    def table(self, name):
        return FakeTableFail()

# Volver a marcar productos como dirty para probar el fallo
run_query("UPDATE productos SET dirty = true, synced_at = NULL")
n_antes = run_query(
    "SELECT COUNT(*) AS n FROM productos WHERE dirty = true", fetch_one=True
)["n"]
print(f"\n=== Sync con fallo de red ===")
print(f"  productos dirty antes: {n_antes}")

sync_module.supabase = FakeSupabaseFail()
resultado = sync_module.SyncService.sync_pendientes()
print("Resultado:", resultado)

n_despues = run_query(
    "SELECT COUNT(*) AS n FROM productos WHERE dirty = true", fetch_one=True
)["n"]
print(f"  productos dirty después: {n_despues}")
