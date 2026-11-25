from urllib.parse import quote
from flask import Flask, request, redirect, url_for, render_template_string, make_response

app = Flask(__name__)

opciones_venta = [
    {"id": 1, "producto": "1/4 Pollo + Papas", "precio": 22.00, "activa": True},
    {"id": 2, "producto": "Broaster Pierna", "precio": 14.00, "activa": True},
]
pedidos_pendientes = []
pedidos_enviados = []
pedidos_rechazados = []
ultimo_confirmado = None
contador_id = 1

FORMAS_PAGO = ["Efectivo", "Yape", "Plin", "Tarjeta"]

HTML = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tablero de Pedidos</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: 'Segoe UI', Arial, sans-serif;
      max-width: 1080px;
      margin: 18px auto;
      padding: 0 14px;
      background: #0f172a;
      color: #1e293b;
    }
    .topbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
      color: #f8fafc;
      margin-bottom: 16px;
    }
    .topbar h1 { margin: 0; font-size: 22px; }
    .kpis {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }
    .kpi {
      background: #1e293b;
      color: #f8fafc;
      padding: 14px;
      border-radius: 10px;
      border-left: 5px solid #38bdf8;
      transition: transform .15s ease;
    }
    .kpi:hover { transform: translateY(-2px); }
    .kpi.rojo { border-left-color: #ef4444; }
    .kpi.verde { border-left-color: #22c55e; }
    .kpi.ambar { border-left-color: #f59e0b; }
    .kpi span { font-size: 12px; color: #94a3b8; display: block; }
    .kpi strong { font-size: 22px; margin-top: 4px; display: block; }

    .aviso {
      padding: 12px 14px;
      border-radius: 10px;
      margin-bottom: 16px;
      font-weight: 600;
      font-size: 14px;
    }
    .aviso-ok { background: #dcfce7; color: #14532d; border: 1px solid #86efac; }
    .aviso-err { background: #fee2e2; color: #7f1d1d; border: 1px solid #fca5a5; }

    .card {
      background: #ffffff;
      padding: 18px;
      border-radius: 12px;
      margin-bottom: 18px;
      box-shadow: 0 6px 18px rgba(0,0,0,.18);
    }
    h2 { margin-top: 0; font-size: 18px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

    input, select, button {
      padding: 9px 11px;
      margin: 4px 0;
      border-radius: 7px;
      border: 1px solid #cbd5e1;
      font-size: 14px;
    }
    input:focus, select:focus {
      outline: none;
      border-color: #2563eb;
      box-shadow: 0 0 0 3px rgba(37,99,235,.15);
    }
    button {
      background: #16a34a;
      color: #fff;
      border: none;
      cursor: pointer;
      font-weight: 600;
      transition: filter .15s ease, transform .1s ease;
    }
    button:hover { filter: brightness(1.07); }
    button:active { transform: scale(0.98); }
    button.retirar { background: #dc2626; padding: 5px 10px; font-size: 12px; }
    button.enviar { background: #15803d; padding: 6px 10px; font-size: 12px; }
    button.rechazar { background: #d97706; padding: 6px 10px; font-size: 12px; }

    .fila { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
    .lista-productos {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 0;
      list-style: none;
      margin-top: 12px;
    }
    .chip {
      background: #f1f5f9;
      border: 1px solid #e2e8f0;
      padding: 6px 10px;
      border-radius: 999px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
    }
    .qty-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #f8fafc;
      padding: 8px 12px;
      border-radius: 8px;
      margin-bottom: 6px;
      border: 1px solid #e2e8f0;
    }

    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th, td { border: 1px solid #e2e8f0; padding: 9px; text-align: left; font-size: 13.5px; }
    th { background: #f1f5f9; color: #0f172a; }

    .card-pendientes { border-top: 5px solid #ef4444; }
    .fila-pendiente { background: #fef2f2; }
    .fila-pendiente:hover { background: #fee2e2; }

    .card-enviados { border-top: 5px solid #22c55e; }
    .fila-enviado { background: #f0fdf4; }
    .fila-enviado:hover { background: #dcfce7; }

    .card-rechazados { border-top: 5px solid #f59e0b; }
    .fila-rechazado { background: #fffbeb; }
    .fila-rechazado:hover { background: #fef3c7; }

    .badge {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 999px;
      font-size: 11.5px;
      font-weight: 700;
    }
    .badge-rojo { background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }
    .badge-verde { background: #dcfce7; color: #15803d; border: 1px solid #86efac; }
    .badge-ambar { background: #fef3c7; color: #b45309; border: 1px solid #fcd34d; }
    .badge-pago { background: #e0e7ff; color: #1d4ed8; }
    .acciones { display: flex; gap: 6px; flex-wrap: wrap; }
  </style>
</head>
<body>

  <div class="topbar">
    <h1>Tablero de Pedidos y Reparto</h1>
    <span style="font-size:13px; color:#94a3b8;">Sistema interno activo</span>
  </div>

  {% if msg_ok %}
    <div class="aviso aviso-ok">{{ msg_ok }}</div>
  {% endif %}
  {% if msg_err %}
    <div class="aviso aviso-err">{{ msg_err }}</div>
  {% endif %}

  <div class="kpis">
    <div class="kpi rojo">
      <span>Faltan enviar (Pendientes)</span>
      <strong>{{ pendientes|length }}</strong>
    </div>
    <div class="kpi verde">
      <span>Enviados</span>
      <strong>{{ enviados|length }}</strong>
    </div>
    <div class="kpi ambar">
      <span>No contesta / Ya no lo quiso</span>
      <strong>{{ rechazados|length }}</strong>
    </div>
    <div class="kpi">
      <span>Total enviado (S/)</span>
      <strong>S/ {{ "%.2f"|format(total_enviado) }}</strong>
    </div>
  </div>

  <div class="card">
    <h2>1. Opciones de venta (Producto, Precio y Retirar)</h2>
    <form method="post" action="{{ url_for('agregar_opcion') }}" class="fila">
      <input type="text" name="producto" placeholder="Nombre del producto" required style="flex:2; min-width:180px;">
      <input type="number" step="0.01" min="0" name="precio" placeholder="Precio (ej. 18.00)" required style="width:150px;">
      <button type="submit">+ Agregar</button>
    </form>

    <ul class="lista-productos">
      {% for op in opciones_activas %}
        <li class="chip">
          <span><strong>{{ op.producto }}</strong> — S/ {{ "%.2f"|format(op.precio) }}</span>
          <form method="post" action="{{ url_for('retirar_opcion', opcion_id=op.id) }}" style="margin:0;">
            <button type="submit" class="retirar" title="Retirar producto">Retirar</button>
          </form>
        </li>
      {% else %}
        <li style="color:#64748b; font-size:13px;">No hay productos activos. Agrega uno arriba.</li>
      {% endfor %}
    </ul>
  </div>

  <div class="card">
    <h2>2. Registrar pedido</h2>
    <form method="post" action="{{ url_for('confirmar_pedido') }}">
      <div class="fila">
        <input type="text" name="cliente" placeholder="Nombre del cliente" required style="flex:1; min-width:180px;">
        <input type="text" name="celular" placeholder="Celular del cliente (motorizado)" required style="flex:1; min-width:180px;">
        <select name="forma_pago" required style="min-width:150px;">
          {% for fp in formas_pago %}
            <option value="{{ fp }}">{{ fp }}</option>
          {% endfor %}
        </select>
      </div>
      <input type="text" name="direccion" placeholder="Dirección o referencia de entrega" required style="width:100%;">

      <p style="margin:10px 0 6px;"><strong>Cantidades por producto:</strong></p>
      {% for op in opciones_activas %}
        <div class="qty-row">
          <span><strong>{{ op.producto }}</strong> <span style="color:#475569;">(S/ {{ "%.2f"|format(op.precio) }})</span></span>
          <input type="number" min="0" value="0" name="cant_{{ op.id }}" style="width:80px; text-align:center;">
        </div>
      {% endfor %}

      <button type="submit" style="margin-top:8px;">Confirmar pedido</button>
    </form>

    {% if confirmado %}
      <h3 style="margin-top:16px;">Tabla de pedido confirmado</h3>
      <div class="table-wrap">
        <table>
          <tr>
            <th>Cliente</th><th>Celular</th><th>Dirección / Referencia</th><th>Pago</th><th>Pedido</th><th>Total</th>
          </tr>
          <tr>
            <td>{{ confirmado.cliente }}</td>
            <td>{{ confirmado.celular }}</td>
            <td>{{ confirmado.direccion }}</td>
            <td><span class="badge badge-pago">{{ confirmado.forma_pago }}</span></td>
            <td>{{ confirmado.detalle }}</td>
            <td><strong>S/ {{ "%.2f"|format(confirmado.total) }}</strong></td>
          </tr>
        </table>
      </div>
    {% endif %}
  </div>

  <div class="card card-pendientes">
    <h2>
      <span>3. Pedidos que faltan enviar</span>
      <span class="badge badge-rojo">{{ pendientes|length }} pendientes</span>
    </h2>
    <div class="table-wrap">
      <table>
        <tr>
          <th>#</th><th>Estado</th><th>Cliente</th><th>Celular</th><th>Dirección / Referencia</th><th>Pago</th><th>Pedido</th><th>Total</th><th>Acciones</th>
        </tr>
        {% for p in pendientes %}
          <tr class="fila-pendiente">
            <td>{{ p.id }}</td>
            <td><span class="badge badge-rojo">Falta enviar</span></td>
            <td><strong>{{ p.cliente }}</strong></td>
            <td>{{ p.celular }}</td>
            <td>{{ p.direccion }}</td>
            <td><span class="badge badge-pago">{{ p.forma_pago }}</span></td>
            <td>{{ p.detalle }}</td>
            <td><strong>S/ {{ "%.2f"|format(p.total) }}</strong></td>
            <td>
              <div class="acciones">
                <form method="post" action="{{ url_for('marcar_enviado', pedido_id=p.id) }}" style="margin:0;">
                  <button type="submit" class="enviar">Marcar enviado</button>
                </form>
                <form method="post" action="{{ url_for('marcar_rechazado', origen='pendientes', pedido_id=p.id) }}" style="margin:0;">
                  <button type="submit" class="rechazar">No contesta / Ya no lo quiso</button>
                </form>
              </div>
            </td>
          </tr>
        {% else %}
          <tr><td colspan="9">No hay pedidos pendientes por enviar.</td></tr>
        {% endfor %}
      </table>
    </div>
  </div>

  <div class="card card-enviados">
    <h2>
      <span>4. Pedidos enviados</span>
      <span class="badge badge-verde">{{ enviados|length }} enviados</span>
    </h2>
    <div class="table-wrap">
      <table>
        <tr>
          <th>#</th><th>Estado</th><th>Cliente</th><th>Celular</th><th>Dirección / Referencia</th><th>Pago</th><th>Pedido</th><th>Total</th><th>Acción</th>
        </tr>
        {% for p in enviados %}
          <tr class="fila-enviado">
            <td>{{ p.id }}</td>
            <td><span class="badge badge-verde">Enviado</span></td>
            <td><strong>{{ p.cliente }}</strong></td>
            <td>{{ p.celular }}</td>
            <td>{{ p.direccion }}</td>
            <td><span class="badge badge-pago">{{ p.forma_pago }}</span></td>
            <td>{{ p.detalle }}</td>
            <td><strong>S/ {{ "%.2f"|format(p.total) }}</strong></td>
            <td>
              <form method="post" action="{{ url_for('marcar_rechazado', origen='enviados', pedido_id=p.id) }}" style="margin:0;">
                <button type="submit" class="rechazar">No contesta / Ya no lo quiso</button>
              </form>
            </td>
          </tr>
        {% else %}
          <tr><td colspan="9">Aún no hay pedidos enviados.</td></tr>
        {% endfor %}
      </table>
    </div>
  </div>

  <div class="card card-rechazados">
    <h2>
      <span>5. No contesta / Ya no lo quiso</span>
      <span class="badge badge-ambar">{{ rechazados|length }} casos</span>
    </h2>
    <div class="table-wrap">
      <table>
        <tr>
          <th>#</th><th>Estado</th><th>Cliente</th><th>Celular</th><th>Dirección / Referencia</th><th>Pago</th><th>Pedido</th><th>Total</th>
        </tr>
        {% for p in rechazados %}
          <tr class="fila-rechazado">
            <td>{{ p.id }}</td>
            <td><span class="badge badge-ambar">No contesta / Ya no lo quiso</span></td>
            <td><strong>{{ p.cliente }}</strong></td>
            <td>{{ p.celular }}</td>
            <td>{{ p.direccion }}</td>
            <td><span class="badge badge-pago">{{ p.forma_pago }}</span></td>
            <td>{{ p.detalle }}</td>
            <td>S/ {{ "%.2f"|format(p.total) }}</td>
          </tr>
        {% else %}
          <tr><td colspan="8">No hay pedidos marcados como no contesta o ya no lo quiso.</td></tr>
        {% endfor %}
      </table>
    </div>
  </div>

</body>
</html>
"""

def redirigir_tablero(ok="", err=""):
    destino = url_for("index")
    params = []
    if ok:
        params.append("ok=" + quote(ok))
    if err:
        params.append("err=" + quote(err))
    if params:
        destino += "?" + "&".join(params)
    resp = make_response(redirect(destino, code=303))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp

@app.route("/")
def index():
    activas = [op for op in opciones_venta if op.get("activa", True)]
    total_enviado = sum(p["total"] for p in pedidos_enviados)
    html = render_template_string(
        HTML,
        opciones_activas=activas,
        formas_pago=FORMAS_PAGO,
        pendientes=pedidos_pendientes,
        enviados=pedidos_enviados,
        rechazados=pedidos_rechazados,
        confirmado=ultimo_confirmado,
        total_enviado=total_enviado,
        msg_ok=request.args.get("ok", ""),
        msg_err=request.args.get("err", ""),
    )
    resp = make_response(html)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp

@app.route("/agregar_opcion", methods=["POST"])
def agregar_opcion():
    global contador_id
    producto = request.form.get("producto", "").strip()
    try:
        precio = float(request.form.get("precio", "0"))
    except ValueError:
        return redirigir_tablero(err="Precio inválido.")
    if producto and precio >= 0:
        opciones_venta.append({
            "id": contador_id,
            "producto": producto,
            "precio": precio,
            "activa": True,
        })
        contador_id += 1
        return redirigir_tablero(ok=f"Producto '{producto}' agregado.")
    return redirigir_tablero(err="Completa el nombre y un precio válido.")

@app.route("/retirar_opcion/<int:opcion_id>", methods=["POST"])
def retirar_opcion(opcion_id):
    for op in opciones_venta:
        if op["id"] == opcion_id:
            op["activa"] = False
            return redirigir_tablero(ok=f"Producto '{op['producto']}' retirado.")
    return redirigir_tablero()

@app.route("/confirmar_pedido", methods=["POST"])
def confirmar_pedido():
    global contador_id, ultimo_confirmado
    cliente = request.form.get("cliente", "").strip()
    celular = request.form.get("celular", "").strip()
    direccion = request.form.get("direccion", "").strip()
    forma_pago = request.form.get("forma_pago", "Efectivo").strip()
    if forma_pago not in FORMAS_PAGO:
        forma_pago = "Efectivo"

    items = []
    total = 0.0
    for op in opciones_venta:
        if not op.get("activa", True):
            continue
        try:
            cant = int(request.form.get(f"cant_{op['id']}", 0) or 0)
        except ValueError:
            cant = 0
        if cant > 0:
            subtotal = cant * op["precio"]
            total += subtotal
            items.append(f"{cant}x {op['producto']} (S/ {subtotal:.2f})")

    if not cliente or not celular or not direccion:
        return redirigir_tablero(err="Completa cliente, celular y dirección.")
    if not items:
        return redirigir_tablero(err="Pon cantidad mayor a 0 en al menos un producto.")

    pedido = {
        "id": contador_id,
        "cliente": cliente,
        "celular": celular,
        "direccion": direccion,
        "forma_pago": forma_pago,
        "detalle": ", ".join(items),
        "total": total,
    }
    contador_id += 1
    ultimo_confirmado = pedido
    pedidos_pendientes.append(pedido)
    return redirigir_tablero(ok=f"Pedido #{pedido['id']} de {cliente} registrado en Pendientes.")

@app.route("/marcar_enviado/<int:pedido_id>", methods=["POST"])
def marcar_enviado(pedido_id):
    for i, p in enumerate(pedidos_pendientes):
        if p["id"] == pedido_id:
            pedidos_enviados.append(pedidos_pendientes.pop(i))
            return redirigir_tablero(ok=f"Pedido #{pedido_id} marcado como enviado.")
    return redirigir_tablero()

@app.route("/marcar_rechazado/<origen>/<int:pedido_id>", methods=["POST"])
def marcar_rechazado(origen, pedido_id):
    lista = pedidos_pendientes if origen == "pendientes" else pedidos_enviados
    for i, p in enumerate(lista):
        if p["id"] == pedido_id:
            pedidos_rechazados.append(lista.pop(i))
            return redirigir_tablero(ok=f"Pedido #{pedido_id} movido a No contesta / Ya no lo quiso.")
    return redirigir_tablero()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)