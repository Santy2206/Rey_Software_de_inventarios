from fastapi import FastAPI
from pydantic import BaseModel

from src.services.productos_service import ProductosService
from src.services.bodegas_service import BodegasService


app = FastAPI(
    title="API REY Inventarios",
    description="API REST para el sistema de inventarios REY",
    version="1.0.0"
)


class BodegaCreate(BaseModel):
    nombre: str
    tipo: str


class ProductoCreate(BaseModel):
    nombre: str
    descripcion: str
    sku: str
    precio: float
    stock_actual: int
    bodega_id: str


@app.get("/")
def inicio():
    return {
        "success": True,
        "message": "API REY Inventarios funcionando correctamente"
    }


@app.get("/productos")
def obtener_productos():
    return ProductosService.get_all()

@app.get("/productos/{producto_id}")
def obtener_producto(producto_id: str):
    return ProductosService.get_one(producto_id)

@app.put("/productos/{producto_id}")
def actualizar_producto(producto_id: str, producto: ProductoCreate):
    return ProductosService.update(
        producto_id=producto_id,
        nombre=producto.nombre,
        descripcion=producto.descripcion,
        sku=producto.sku,
        precio=producto.precio,
        bodega_id=producto.bodega_id
    )


@app.get("/bodegas")
def obtener_bodegas():
    return BodegasService.get_all()


@app.post("/bodegas")
def crear_bodega(bodega: BodegaCreate):
    return BodegasService.create(
        nombre=bodega.nombre,
        tipo=bodega.tipo
    )


@app.post("/productos")
def crear_producto(producto: ProductoCreate):
    return ProductosService.create(
        nombre=producto.nombre,
        descripcion=producto.descripcion,
        sku=producto.sku,
        precio=producto.precio,
        stock_actual=producto.stock_actual,
        bodega_id=producto.bodega_id
    )
    
@app.delete("/productos/{producto_id}")
def eliminar_producto(producto_id: str):
    return ProductosService.delete(producto_id)    