"""
Servicio de Bodegas — versión BASE DE DATOS LOCAL.

Maneja todas las operaciones de la tabla 'bodegas' en PostgreSQL local.
Mismo contrato que la versión anterior (Supabase):
  - Cada función usa try/except
  - Siempre retorna un diccionario con 'success' y 'message'
  - Si hay datos, los incluye bajo la llave 'data'
  - SIN importaciones de Flet — solo lógica pura

El id se genera automáticamente en la base de datos (DEFAULT gen_random_uuid()),
así que nunca lo mandamos nosotros al hacer INSERT.

Tabla:
    bodegas (id, nombre, tipo, created_at, dirty, synced_at)
"""

from src.core.local_db import run_query


class BodegasService:

    @staticmethod
    def get_all():
        """Trae todas las bodegas de la base de datos."""
        print("--- Trayendo todas las bodegas ---")
        try:
            # 'ubicacion AS tipo' — bodegas_view.py espera la llave "tipo"
            data = run_query(
                "SELECT id, nombre, ubicacion AS tipo, creado_en "
                "FROM bodegas ORDER BY nombre"
            )

            if not res.data:
                print(" No hay bodegas registradas aún")
                return {"success": False, "message": "No hay bodegas registradas"}

            print(f" Se encontraron {len(res.data)} bodega(s)")
            return {"success": True, "message": "Bodegas obtenidas", "data": res.data}

        except Exception as e:
            error_msg = str(e)
            print(f" Error en BodegasService.get_all: {error_msg}")
            return {
                "success": False,
                "message": f"Error al obtener bodegas: {error_msg}",
            }

    @staticmethod
    def get_one(bodega_id: str):
        """
        Trae una sola bodega por su ID.

        Parámetros:
            bodega_id: el id de la bodega que queremos buscar
        """
        print(f"--- Buscando bodega con id: {bodega_id} ---")
        try:
            bodega = run_query(
                "SELECT id, nombre, ubicacion AS tipo, creado_en "
                "FROM bodegas WHERE id = %s",
                (bodega_id,),
                fetch_one=True,
            )

            if not res.data:
                print(f"Bodega con id {bodega_id} no encontrada")
                return {"success": False, "message": "Bodega no encontrada"}

            print(f"Bodega encontrada: {res.data['nombre']}")
            return {"success": True, "message": "Bodega encontrada", "data": res.data}

        except Exception as e:
            error_msg = str(e)
            print(f"Error en BodegasService.get_one: {error_msg}")
            return {"success": False, "message": f"Error al buscar bodega: {error_msg}"}

    @staticmethod
    def create(nombre: str, tipo: str):
        """
        Crea una nueva bodega.

        Parámetros:
            nombre: nombre de la bodega, ej: "Bodega Principal"
            tipo:   se guarda en la columna 'ubicacion' de la tabla real.
                    (el parámetro se sigue llamando 'tipo' para no romper
                    bodegas_view.py, que ya te llama con tipo=tipo)
        """
        print(f"--- Creando bodega: {nombre} ({tipo}) ---")
        try:
            bodega = run_query(
                """
                INSERT INTO bodegas (nombre, ubicacion)
                VALUES (%s, %s)
                RETURNING *
                """,
                (nombre, tipo),
                fetch_one=True,
            )

            if not bodega:
                return {"success": False, "message": "No se pudo crear la bodega"}

            print(f"Bodega '{nombre}' creada con éxito")
            return {
                "success": True,
                "message": f"Bodega '{nombre}' creada con éxito",
                "data": bodega,
            }

        except Exception as e:
            error_msg = str(e)
            print(f"Error en BodegasService.create: {error_msg}")
            return {"success": False, "message": f"Error al crear bodega: {error_msg}"}

    @staticmethod
    def update(bodega_id: str, nombre: str, tipo: str):
        """
        Actualiza el nombre y/o tipo de una bodega existente.

        Parámetros:
            bodega_id: el id de la bodega a actualizar
            nombre:    nuevo nombre
            tipo:      nuevo tipo
        """
        print(f"--- Actualizando bodega id: {bodega_id} ---")
        try:
            bodega = run_query(
                """
                UPDATE bodegas
                SET nombre = %s, ubicacion = %s
                WHERE id = %s
                RETURNING *
                """,
                (nombre, tipo, bodega_id),
                fetch_one=True,
            )

            if not bodega:
                return {
                    "success": False,
                    "message": "Bodega no encontrada para actualizar",
                }

            print(f" Bodega actualizada con éxito")
            return {
                "success": True,
                "message": "Bodega actualizada con éxito",
                "data": bodega,
            }

        except Exception as e:
            error_msg = str(e)
            print(f" Error en BodegasService.update: {error_msg}")
            return {
                "success": False,
                "message": f"Error al actualizar bodega: {error_msg}",
            }

    @staticmethod
    def delete(bodega_id: str):
        """
        Elimina una bodega por su ID.

        Parámetros:
            bodega_id: el id de la bodega a eliminar
        """
        print(f"--- Eliminando bodega id: {bodega_id} ---")
        try:
            eliminado = run_query(
                "DELETE FROM bodegas WHERE id = %s RETURNING id",
                (bodega_id,),
                fetch_one=True,
            )

            if not eliminado:
                return {
                    "success": False,
                    "message": "Bodega no encontrada para eliminar",
                }

            print(f" Bodega eliminada con éxito")
            return {"success": True, "message": "Bodega eliminada con éxito"}

        except Exception as e:
            error_msg = str(e)
            print(f" Error en BodegasService.delete: {error_msg}")
            return {
                "success": False,
                "message": f"Error al eliminar bodega: {error_msg}",
            }


# crear un diccionario que contenga [fecha ,hora ], [usuario ],[rol] ,[accion ] y [descripcion ]
# array de las horas
fecha_hora = []
hora = []
# array de las horas
usuarios_nuevos = []
contraeña_nueva = []
# roles
administrador = []
# acciones
ventas = []
clientes = []
bodegas = []
# //////////////////////
DESCRIPCION = []


# funcionespara cada uno y despues poner en un diccionario
def DESCRIPCION():
    while True:
        try:
            descrip = str(input("Señor usuario:anexe una descripcion breve "))
            DESCRIPCION.append(descrip)
            print("señor usuaio la descripcion fue guardada exitosamente")
            break
        except ValueError:
            print(
                "Sñor usuario su descripcion no cumple con los parametros establecidos"
            )


def usuarios():
    print("ingrese la opcion deseada")
    print("1 usuarios registrados")
    print("2 registrar usuario")
    opcion = int(input("ingrese la opcion deseada"))
    while True:
        try:
            if opcion == 1:
                while True:
                    nuevo_usuarios = str(input("ingrese el nuevo usuario"))
                    usuarios_nuevos.append(nuevo_usuarios)
                    contraseña = input("ingrese una contraseña alfanumerica")
                    if contraseña.isalnum():
                        contraeña_nueva.append(contraseña)
                        print("¡Contraseña alfanumérica registrada con éxito!")
                    else:
                        break
                        print(
                            "la contraseña no es alphanumerica vuelva a intentarlo nuevamente"
                        )
            elif opcion == 2:
                for usuarios_nuevos in nuevo_usuarios:
                    print("////usuarios registrados////")
                    print("=", usuarios_nuevos)
                    break
        except ValueError:
            print("no existe la opcion deseada")


from datetime import datetime


def fecha_hora():
    while True:
        fecha_input = input("Ingrese la fecha (DD/MM/AAAA): ")
        try:
            fecha_validada = datetime.strptime(fecha_input, "%d/%m/%Y").date()
            fecha_hora = fecha_validada.strftime("%d/%m/%Y")
            break
        except ValueError:
            print(" Fecha incorrecta. Use el formato Día/Mes/Año.")

        while True:
            hora_input = input("Ingrese la hora (HH:MM): ")
        try:
            hora_validada = datetime.strptime(hora_input, "%H:%M").time()
            hora = hora_validada.strftime("%H:%M")
            break
        except ValueError:
            print(" Hora incorrecta. Use el formato de 24 horas.")

        return [fecha_final, hora_final]


def accion():

    print("ingrese la opcion deseada:")
    print("1 agregar ventas")
    print("2 historial de ventas")
    print("3 ingresar clientes")
    print("4 historial de ventas")
    print("5 ingresar bodegas")
    print("6 historial de bodegas")
    opcion = "ingrese la opcion deseada"
    while True:
        try:
            if opcion == 1:
                while True:
                    try:
                        vent = str("ingrese el producto del cual vendio")
                        ventas.append(vent)
                        break
                    except ValueError:
                        print("error vuelva a intentarlos")
            if opcion == 2:
                for ventas in vent:
                    print("///////////historial de ventas////////////")
                    print("=", ventas)

            if opcion == 3:
                while True:
                    try:
                        cly = str(input("ingrese el cliente que va a comprar"))
                        clientes.appen(cly)
                        break
                    except ValueError:
                        print("error vuelva a intentarlos")
            if opcion == 4:
                for clientes in cly:
                    print("//// Historial////")
                    print("=", clientes)

            if opcion == 5:
                while True:
                    try:
                        bod = int(
                            input("ingrese el numero de bodegas que desea ingresar")
                        )
                        bodegas.append(bod)
                        break
                    except ValueError:
                        print("el numero de bodegas no es valido")
            if opcion == 6:
                for bodegas in bod:
                    print("///historial////")
                    print("=", bodegas)
        except ValueError:
            print("la opcion no es valida")

    # diccionario donde pueda relacionar todas las funciones


bitacora = {
    "fechita": fecha_hora(),  # VARABLE TEMPORAL Q RELACIONA EL DICCIONARIO
    "objet": usuarios(),
    "descrip": DESCRIPCION(),
    "aci": accion(),
}
print(bitacora)
