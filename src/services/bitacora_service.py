from bodegas_service import historial


class bitacora_service:  # clase principal de la bitacora a usar
    def __init__(self, bitacora_repository):  # constructor de la clase
        self.bitacora_repository = (
            bitacora_repository  # se asigna el repositorio de la bitacora a la clase
        )

    def registrar_evento(
        self, evento
    ):  # metodo para registrar un evento en la bitacora
        self.bitacora_repository.registrar_evento(
            evento
        )  # se llama al metodo del repositorio para registrar el evento
        self.registros = []

        def registrar_evento(self, evento):
            self.registros.append(evento)  # se agrega el evento a la lista de registros
            registro = {
                "usuario": "usuario",
                "accion": "accion",
                "descripcion": "descripcion",
            }
            self.registros.append(registro)

        print("Registro guardado correctamente")

    def mostrar_bitacora(self):

        for registro in self.registros:

            print("----------------------")
            print(f"Usuario: {registro['usuario']}")
            print(f"Acción: {registro['accion']}")
            print(f"Descripción: {registro['descripcion']}")
            print("----------------------")
