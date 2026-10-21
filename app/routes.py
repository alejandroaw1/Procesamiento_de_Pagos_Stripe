import os

from flask import Blueprint, Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from app import services
from app.services import PagoError

bp = Blueprint("pagos", __name__, url_prefix="/api")


@bp.get("/config")
def config():
    # La publishable key es segura de exponer al frontend (a diferencia de la secret key).
    return jsonify({"publishableKey": os.getenv("STRIPE_PUBLISHABLE_KEY", "")}), 200


@bp.post("/pagos/intent")
def crear_intento_pago():
    data = request.get_json(force=True) or {}
    intento = services.crear_intento_pago(
        data.get("clientId"), data.get("amount"), data.get("currency"), data.get("productId")
    )
    return jsonify(intento), 201


@bp.post("/usuarios")
def crear_usuario():
    data = request.get_json(force=True) or {}
    cliente = services.crear_usuario(data.get("name"), data.get("email"))
    return jsonify(cliente), 201


@bp.post("/metodos-pago")
def crear_metodo_pago():
    data = request.get_json(silent=True) or {}
    metodo = services.crear_metodo_pago(data.get("token", "tok_visa"))
    return jsonify(metodo), 201


@bp.post("/metodos-pago/asociar")
def asociar_metodo_pago():
    data = request.get_json(force=True) or {}
    resultado = services.asociar_metodo_pago(data.get("clientId"), data.get("paymentMethodId"))
    return jsonify(resultado), 200


@bp.get("/productos/primero")
def obtener_producto():
    producto = services.obtener_producto()
    return jsonify(producto), 200


@bp.get("/productos")
def listar_productos():
    productos = services.listar_productos()
    return jsonify(productos), 200


@bp.get("/productos/<product_id>/precio")
def obtener_precio_producto(product_id):
    precio = services.obtener_precio_producto(product_id)
    return jsonify(precio), 200


@bp.post("/pagos")
def crear_pago():
    data = request.get_json(force=True) or {}
    pago = services.crear_pago(
        data.get("clientId"),
        data.get("paymentMethodId"),
        data.get("productId"),
        data.get("amount"),
        data.get("currency"),
    )
    return jsonify(pago), 201


@bp.post("/pagos/prueba-completa")
def flujo_completo_de_prueba():
    data = request.get_json(force=True) or {}
    resultado = services.flujo_completo_de_prueba(data.get("name"), data.get("email"))
    return jsonify(resultado), 201


def create_app():
    app = Flask(__name__)
    CORS(app)  # permite que el frontend (abierto como archivo o en otro puerto) llame a esta API
    app.register_blueprint(bp)

    @app.get("/health")
    def health():
        return jsonify({"servicio": "pagos-stripe", "estado": "ok"})

    @app.get("/")
    def index():
        # Este backend no sirve una página en "/": el frontend real está en
        # frontend/index.html. Esta ruta es solo para confirmar que el
        # servicio está vivo si alguien entra por el navegador.
        return jsonify({"servicio": "pagos-stripe", "mensaje": "API corriendo. Ver /health o /api/*"})

    @app.errorhandler(PagoError)
    def handle_pago_error(err):
        return jsonify({"error": err.mensaje}), err.codigo

    @app.errorhandler(HTTPException)
    def handle_http_exception(err):
        # 404, 405, etc. — errores normales de enrutamiento, no fallas del servicio.
        return jsonify({"error": err.description}), err.code

    @app.errorhandler(Exception)
    def handle_generic_error(err):
        # Solo errores realmente inesperados llegan aquí (bugs, fallas de red, etc.)
        app.logger.exception(err)
        return jsonify({"error": "Error interno del servicio de pagos"}), 500

    return app
