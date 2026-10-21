import os

import dotenv
import stripe

dotenv.load_dotenv()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


class PagoError(Exception):
    """Error de negocio (se traduce a una respuesta HTTP en las rutas)."""

    def __init__(self, mensaje, codigo=400):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


def crear_usuario(name: str, email: str) -> dict:
    if not name or not email:
        raise PagoError("name y email son requeridos")

    try:
        cliente = stripe.Customer.create(name=name, email=email)
        return {"id": cliente.id, "name": cliente.name, "email": cliente.email}
    except stripe.error.StripeError as e:
        raise PagoError(e.user_message or str(e), 502)


def crear_metodo_pago(token: str = "tok_visa") -> dict:
    try:
        metodo = stripe.PaymentMethod.create(type="card", card={"token": token})
        return {"id": metodo.id}
    except stripe.error.StripeError as e:
        raise PagoError(e.user_message or str(e), 502)


def asociar_metodo_pago(client_id: str, payment_method_id: str) -> dict:
    if not client_id or not payment_method_id:
        raise PagoError("clientId y paymentMethodId son requeridos")

    try:
        stripe.PaymentMethod.attach(payment_method_id, customer=client_id)
        return {"clientId": client_id, "paymentMethodId": payment_method_id, "asociado": True}
    except stripe.error.StripeError as e:
        raise PagoError(e.user_message or str(e), 502)


def obtener_producto() -> dict:
    try:
        productos = stripe.Product.list(limit=1)
        if not productos["data"]:
            raise PagoError("No hay productos configurados en Stripe", 404)
        return {"id": productos["data"][0]["id"], "nombre": productos["data"][0]["name"]}
    except stripe.error.StripeError as e:
        raise PagoError(e.user_message or str(e), 502)


def listar_productos() -> list:
    try:
        productos = stripe.Product.list(active=True, limit=20)
        return [{"id": p["id"], "nombre": p["name"]} for p in productos["data"]]
    except stripe.error.StripeError as e:
        raise PagoError(e.user_message or str(e), 502)


def obtener_precio_producto(product_id: str) -> dict:
    if not product_id:
        raise PagoError("product_id es requerido")

    try:
        precios = stripe.Price.list(product=product_id, limit=1)
        if not precios["data"]:
            raise PagoError("El producto no tiene un precio configurado", 404)

        precio = precios["data"][0]
        return {
            "priceId": precio["id"],
            "amount": precio["unit_amount"],
            "currency": precio["currency"],
        }
    except stripe.error.StripeError as e:
        raise PagoError(e.user_message or str(e), 502)


def crear_pago(client_id: str, payment_method_id: str, product_id: str, amount: int, currency: str) -> dict:
    if not all([client_id, payment_method_id, product_id, amount, currency]):
        raise PagoError("clientId, paymentMethodId, productId, amount y currency son requeridos")

    try:
        payment = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            customer=client_id,
            payment_method=payment_method_id,
            payment_method_types=["card"],
            confirm=True,
            metadata={"product_id": product_id},
        )
        return {"id": payment.id, "estado": payment.status, "monto": amount, "moneda": currency}
    except stripe.error.CardError as e:
        raise PagoError(e.user_message or "La tarjeta fue rechazada", 402)
    except stripe.error.StripeError as e:
        raise PagoError(e.user_message or str(e), 502)


def crear_intento_pago(client_id: str, amount: int, currency: str, product_id: str) -> dict:
    """Crea un PaymentIntent SIN confirmarlo. El frontend (Stripe.js) confirma
    el pago en el navegador usando el client_secret devuelto aquí, capturando
    la tarjeta del usuario de forma segura."""
    if not all([client_id, amount, currency]):
        raise PagoError("clientId, amount y currency son requeridos")

    try:
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            customer=client_id,
            automatic_payment_methods={"enabled": True},
            metadata={"product_id": product_id} if product_id else {},
        )
        return {"clientSecret": intent.client_secret, "id": intent.id}
    except stripe.error.StripeError as e:
        raise PagoError(e.user_message or str(e), 502)


def flujo_completo_de_prueba(name: str, email: str) -> dict:
    """Equivalente al bloque de PRUEBAS del script original, pero como una
    función invocable (no se ejecuta sola al importar el módulo)."""
    cliente = crear_usuario(name, email)
    metodo = crear_metodo_pago()
    asociar_metodo_pago(cliente["id"], metodo["id"])
    producto = obtener_producto()
    precio = obtener_precio_producto(producto["id"])
    pago = crear_pago(
        cliente["id"], metodo["id"], producto["id"], precio["amount"], precio["currency"]
    )
    return {"cliente": cliente, "metodo": metodo, "producto": producto, "precio": precio, "pago": pago}
