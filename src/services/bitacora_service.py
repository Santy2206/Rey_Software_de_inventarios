from datetime import datetime

# --- Lógica de Consola (CLI) opcional ---
usuarios_nuevos = []
contrasena_nueva = []
ventas = []
clientes = []
bodegas = []
descripciones = []


def registrar_descripcion():
    while True:
        try:
            descrip = str(input("Señor usuario: anexe una descripción breve: "))
            descripciones.append(descrip)
            print("Señor usuario, la descripción fue guardada exitosamente.")
            break
        except ValueError:
            print(
                "Señor usuario, su descripción no cumple con los parámetros establecidos."
            )


def menu_usuarios():
    print("Ingrese la opción deseada:")
    print("1. Usuarios registrados")
    print("2. Registrar usuario")

    try:
        opcion = int(input("Ingrese la opción deseada: "))
        if opcion == 1:
            for usr in usuarios_nuevos:
                print("//// Usuarios registrados ////")
                print("=", usr)
        elif opcion == 2:
            nuevo_usuario = str(input("Ingrese el nuevo usuario: "))
            usuarios_nuevos.append(nuevo_usuario)
            while True:
                contrasena = input("Ingrese una contraseña alfanumérica: ")
                if contrasena.isalnum():
                    contrasena_nueva.append(contrasena)
                    print("¡Contraseña alfanumérica registrada con éxito!")
                    break
                else:
                    print("La contraseña no es alfanumérica, vuelva a intentarlo.")
        else:
            print("No existe la opción deseada.")
    except ValueError:
        print("La opción ingresada no es válida.")


def obtener_fecha_hora():
    fecha_final, hora_final = "", ""
    while True:
        fecha_input = input("Ingrese la fecha (DD/MM/AAAA): ")
        try:
            fecha_validada = datetime.strptime(fecha_input, "%d/%m/%Y").date()
            fecha_final = fecha_validada.strftime("%d/%m/%Y")
            break
        except ValueError:
            print("Fecha incorrecta. Use el formato Día/Mes/Año.")

    while True:
        hora_input = input("Ingrese la hora (HH:MM): ")
        try:
            hora_validada = datetime.strptime(hora_input, "%H:%M").time()
            hora_final = hora_validada.strftime("%H:%M")
            break
        except ValueError:
            print("Hora incorrecta. Use el formato de 24 horas.")

    return [fecha_final, hora_final]


def menu_acciones():
    print("Ingrese la opción deseada:")
    print("1. Agregar ventas")
    print("2. Historial de ventas")
    print("3. Ingresar clientes")
    print("4. Historial de clientes")
    print("5. Ingresar bodegas")
    print("6. Historial de bodegas")

    try:
        opcion = int(input("Ingrese la opción deseada: "))

        if opcion == 1:
            vent = str(input("Ingrese el producto vendido: "))
            ventas.append(vent)
            print("Venta agregada.")

        elif opcion == 2:
            print("/////////// Historial de ventas ////////////")
            for v in ventas:
                print("=", v)

        elif opcion == 3:
            cly = str(input("Ingrese el cliente que va a comprar: "))
            clientes.append(cly)
            print("Cliente agregado.")

        elif opcion == 4:
            print("//// Historial de Clientes ////")
            for c in clientes:
                print("=", c)

        elif opcion == 5:
            try:
                bod = int(input("Ingrese el número de bodegas que desea ingresar: "))
                bodegas.append(bod)
            except ValueError:
                print("El número de bodegas no es válido.")

        elif opcion == 6:
            print("/// Historial de Bodegas ////")
            for b in bodegas:
                print("=", b)
        else:
            print("Opción no válida.")

    except ValueError:
        print("La opción no es válida.")


# --- Servicio de Bitácora para la App (Flet/DB) ---
class BitacoraService:
    """Clase principal de la bitácora a usar en la app."""

    def __init__(self, bitacora_repository=None):
        self.bitacora_repository = bitacora_repository
        self.registros = []

    def registrar_evento(self, evento):
        # Si existe repositorio local DB se registra allí
        if self.bitacora_repository:
            self.bitacora_repository.registrar_evento(evento)

        # También lo guardamos en memoria local como respaldo/prueba
        self.registros.append(evento)
        print("Registro guardado correctamente")

    def mostrar_bitacora(self):
        for registro in self.registros:
            print("----------------------")
            print(f"Usuario: {registro.get('usuario', 'N/A')}")
            print(f"Acción: {registro.get('accion', 'N/A')}")
            print(f"Descripción: {registro.get('descripcion', 'N/A')}")
            print("----------------------")

    @staticmethod
    def get_all():
        """
        Método simulado para que bitacora_view.py no falle al arrancar.
        Deberías reemplazar esto con un `run_query` hacia tu BD.
        """
        return {"success": True, "message": "Datos obtenidos", "data": []}
