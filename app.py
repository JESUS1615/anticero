import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import quote
from zoneinfo import ZoneInfo
from flask import Flask, request, redirect, url_for, render_template_string, make_response, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "anticero-clave-secreta-2026-cambiar")

ZONA_HORARIA = ZoneInfo("America/Lima")
ARCHIVO_DATOS = os.environ.get("DATA_FILE", "datos_anticero.json")

# =========================================================
# CÓDIGO ÚNICO DE PROGRAMADOR (SOLO TÚ LO SABES)
# Sirve para reactivar / renovar la licencia mensual cuando venza
# =========================================================
CODIGO_MAESTRO_PROGRAMADOR = os.environ.get("DEV_MASTER_CODE", "PROG-ANTICERO-2026")

# =========================================================
# USUARIOS Y CONTRASEÑAS ÚNICAS DEL OPERADOR / CAJA
# =========================================================
USUARIOS_OPERADORES = {
    "jesus": os.environ.get("PASS_JESUS", "Anticero2026!"),
    "caja1": os.environ.get("PASS_CAJA1", "Caja01#2026"),
    "motorizado1": os.environ.get("PASS_MOTO1", "Moto01#2026"),
}

FORMAS_PAGO = ["Efectivo", "Yape", "Plin", "Tarjeta"]

def fecha_hoy_peru():
    return datetime.now(ZONA_HORARIA).date()

def datos_iniciales():
    hoy = fecha_hoy_peru()
    vence_inicial = (hoy + timedelta(days=30)).strftime("%Y-%m-%d")
    return {
        "licencia": {
            "vence": vence_inicial,
            "activa": True,
            "ultima_renovacion": hoy.strftime("%Y-%m-%d"),
        },
        "opciones_venta": [
            {"id": 1, "producto": "1/4 Pollo + Papas", "precio": 22.00, "activa": True},
            {"id": 2, "producto": "Broaster Pierna", "precio": 14.00, "activa": True},
        ],
        "pedidos_pendientes": [],
        "pedidos_enviados": [],
        "pedidos_rechazados": [],
        "ventas_registradas": [],  # Cada venta: {"id", "fecha", "pedido_id", "cliente", "detalle", "forma_pago", "total"}
        "ultimo_confirmado": None,
        "contador_id": 3,
    }

def cargar_datos():
    if not os.path.exists(ARCHIVO_DATOS):
        d = datos_iniciales()
        guardar_datos(d)
        return d
    try:
        with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = datos_iniciales()
    base = datos_iniciales()
    for k, v in base.items():
        if k not in data:
            data[k] = v
    if "licencia" not in data or not isinstance(data["licencia"], dict):
        data["licencia"] = base["licencia"]
    return data

def guardar_datos(data):
    with open(ARCHIVO_DATOS, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def estado_licencia(data):
    lic = data.get("licencia", {})
    vence_str = lic.get("vence")
    if not lic.get("activa", True) or not vence_str:
        return False, None, vence_str or "Sin fecha"
    try:
        fecha_cierre = datetime.strptime(vence_str, "%Y-%m-%d").date()
    except ValueError:
        return False, None, vence_str
    dias_restantes = (fecha_cierre - fecha_hoy_peru()).days
    if dias_restantes < 0:
        return False, dias_restantes, fecha_cierre.strftime("%d/%m/%Y")
    return True, dias_restantes, fecha_cierre.strftime("%d/%m/%Y")

HTML_LICENCIA_VENCIDA = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Licencia Mensual Vencida</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: 'Segoe UI', Arial, sans-serif;
      background: #0f172a;
      color: #1e293b;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      padding: 16px;
    }
    .card {
      background: #ffffff;
      width: 100%;
      max-width: 430px;
      padding: 26px 24px;
      border-radius: 14px;
      box-shadow: 0 14px 34px rgba(0,0,0,.4);
      border-top: 6px solid #dc2626;
    }
    h1 { margin: 0 0 8px; font-size: 21px; color: #991b1b; }
    p { margin: 0 0 16px; font-size: 13.5px; color: #475569; line-height: 1.45; }
    .box-info {
      background: #fef2f2;
      border: 1px solid #fecaca;
      color: #7f1d1d;
      padding: 10px 12px;
      border-radius: 8px;
      font-size: 13px;
      margin-bottom: 16px;
    }
    label {
      display: block;
      font-size: 13px;
      font-weight: 600;
      margin-bottom: 5px;
      color: #334155;
    }
    input {
      width: 100%;
      padding: 10px 12px;
      margin-bottom: 14px;
      border-radius: 8px;
      border: 1px solid #cbd5e1;
      font-size: 14px;
    }
    button {
      width: 100%;
      padding: 11px;
      background: #16a34a;
      color: #fff;
      border: none;
      border-radius: 8px;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
    }
    button:hover { filter: brightness(1.07); }
    .err {
      background: #fee2e2;
      color: #7f1d1d;
      border: 1px solid #fca5a5;
      padding: 10px 12px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      margin-bottom: 14px;
    }
    .ok {
      background: #dcfce7;
      color: #14532d;
      border: 1px solid #86efac;
      padding: 10px 12px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      margin-bottom: 14px;
    }
  </style>
</head>
<body>
  <div class="card">
    <h1>Programa Cerrado — Licencia Vencida</h1>
    <p>El ciclo mensual del sistema ha finalizado. Para reactivarlo por otro mes, ingresa el código único de programador.</p>

    <div class="box-info">
      <strong>Fecha de cierre anterior:</strong> {{ fecha_cierre_texto }}
    </div>

    {% if error %}
      <div class="err">{{ error }}</div>
    {% endif %}
    {% if ok %}
      <div class="ok">{{ ok }}</div>
    {% endif %}

    <form method="post" action="{{ url_for('activar_licencia') }}">
      <label for="codigo_prog">Código de programador</label>
      <input type="password" id="codigo_prog" name="codigo_prog" placeholder="Ingresa tu código maestro" required autofocus>

      <label for="dias_extra">Duración de renovación (días)</label>
      <input type="number" id="dias_extra" name="dias_extra" min="1" max="365" value="30" required>

      <button type="submit">Activar nueva licencia mensual</button>
    </form>
  </div>
</body>
</html>
"""

HTML_LOGIN = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Iniciar Sesión - Tablero de Pedidos</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: 'Segoe UI', Arial, sans-serif;
      background: #0f172a;
      color: #1e293b;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      padding: 16px;
    }
    .login-card {
      background: #ffffff;
      width: 100%;
      max-width: 400px;
      padding: 26px 24px;
      border-radius: 14px;
      box-shadow: 0 12px 30px rgba(0,0,0,.35);
      border-top: 5px solid #16a34a;
    }
    .login-card h1 { margin: 0 0 6px; font-size: 21px; color: #0f172a; }
    .login-card p { margin: 0 0 12px; font-size: 13.5px; color: #64748b; }
    .lic-tag {
      display: inline-block;
      background: #f0fdf4;
      color: #15803d;
      border: 1px solid #86efac;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 16px;
    }
    label {
      display: block;
      font-size: 13px;
      font-weight: 600;
      margin-bottom: 5px;
      color: #334155;
    }
    input {
      width: 100%;
      padding: 10px 12px;
      margin-bottom: 14px;
      border-radius: 8px;
      border: 1px solid #cbd5e1;
      font-size: 14px;
    }
    button {
      width: 100%;
      padding: 11px;
      background: #16a34a;
      color: #fff;
      border: none;
      border-radius: 8px;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
    }
    button:hover { filter: brightness(1.07); }
    .err {
      background: #fee2e2;
      color: #7f1d1d;
      border: 1px solid #fca5a5;
      padding: 10px 12px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      margin-bottom: 14px;
    }
  </style>
</head>
<body>
  <div class="login-card">
    <h1>Acceso al Sistema</h1>
    <p>Ingresa tu usuario y contraseña única asignados para continuar a pedidos.</p>
    <div class="lic-tag">Licencia vigente hasta {{ fecha_cierre_texto }} ({{ dias_restantes }} días)</div>

    {% if error %}
      <div class="err">{{ error }}</div>
    {% endif %}

    <form method="post" action="{{ url_for('login') }}">
      <label for="usuario">Usuario</label>
      <input type="text" id="usuario" name="usuario" placeholder="Ej. caja1" required autofocus>

      <label for="password">Contraseña única</label>
      <input type="password" id="password" name="password" placeholder="Ingresa tu contraseña" required>

      <button type="submit">Ingresar a pedidos</button>
    </form>
  </div>
</body>
</html>
"""

HTML = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tablero de Pedidos y Ventas</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: 'Segoe UI', Arial, sans-serif;
      max-width: 1120px;
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
    .user-box {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: #cbd5e1;
      flex-wrap: wrap;
    }
    .pill {
      background: #1e293b;
      border: 1px solid #334155;
      padding: 5px 10px;
      border-radius: 999px;
      font-size: 12px;
      color: #e2e8f0;
    }
    .pill.alerta { border-color: #f59e0b; color: #fde68a; }
    .btn-salir {
      background: #334155;
      color: #f8fafc;
      padding: 6px 12px;
      font-size: 12.5px;
      border-radius: 7px;
      text-decoration: none;
      font-weight: 600;
      border: 1px solid #475569;
    }
    .btn-salir:hover { background: #dc2626; border-color: #dc2626; }

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
    }
    .kpi.rojo { border-left-color: #ef4444; }
    .kpi.verde { border-left-color: #22c55e; }
    .kpi.ambar { border-left-color: #f59e0b; }
    .kpi span { font-size: 12px; color: #94a3b8; display: block; }
    .kpi strong { font-size: 21px; margin-top: 4px; display: block; }

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
    button {
      background: #16a34a;
      color: #fff;
      border: none;
      cursor: pointer;
      font-weight: 600;
    }
    button:hover { filter: brightness(1.07); }
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
    .card-enviados { border-top: 5px solid #22c55e; }
    .fila-enviado { background: #f0fdf4; }
    .card-rechazados { border-top: 5px solid #f59e0b; }
    .fila-rechazado { background: #fffbeb; }
    .card-ventas { border-top: 5px solid #2563eb; }

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
    .badge-max { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
    .badge-min { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }
    .acciones { display: flex; gap: 6px; flex-wrap: wrap; }

    .resumen-extremos {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      gap: 10px;
      margin: 12px 0 16px;
    }
    .extremo-box {
      padding: 12px;
      border-radius: 10px;
      border: 1px solid #e2e8f0;
      background: #f8fafc;
    }
    .extremo-box.max { border-left: 5px solid #16a34a; background: #f0fdf4; }
    .extremo-box.min { border-left: 5px solid #dc2626; background: #fef2f2; }
    .extremo-box small { color: #475569; display: block; font-weight: 600; }
    .extremo-box strong { font-size: 16px; color: #0f172a; }

    .grafico-wrap {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 14px;
      margin-bottom: 16px;
    }
    .barra-fila {
      display: grid;
      grid-template-columns: 105px 1fr 125px;
      gap: 10px;
      align-items: center;
      margin-bottom: 8px;
      font-size: 13px;
    }
    .barra-pista {
      background: #e2e8f0;
      border-radius: 999px;
      height: 18px;
      overflow: hidden;
    }
    .barra-relleno {
      height: 100%;
      background: #2563eb;
      border-radius: 999px;
      transition: width .25s ease;
    }
    .barra-relleno.dia-max { background: #16a34a; }
    .barra-relleno.dia-min { background: #dc2626; }
  </style>
</head>
<body>

  <div class="topbar">
    <h1>Tablero de Pedidos y Ventas</h1>
    <div class="user-box">
      <span>Usuario: <strong>{{ usuario_actual }}</strong></span>
      <span class="pill {% if dias_restantes is not none and dias_restantes <= 5 %}alerta{% endif %}">
        Licencia vence {{ fecha_cierre_texto }} ({{ dias_restantes }}d)
      </span>
      <a href="#seccion-ventas" class="pill" style="text-decoration:none; background:#1d4ed8; border-color:#1d4ed8; color:#fff; font-weight:700;">
        Ir a Ventas y Balance
      </a>
      <a href="{{ url_for('logout') }}" class="btn-salir">Cerrar sesión</a>
    </div>
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
      <span>Total ventas acumuladas (S/)</span>
      <strong>S/ {{ "%.2f"|format(total_ventas_hist) }}</strong>
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

  <div id="seccion-ventas" class="card card-ventas">
    <h2>
      <span>6. Ventas, Balance por Día y Gráfico Mensual</span>
      <span class="badge badge-pago">{{ ventas|length }} ventas guardadas</span>
    </h2>

    <form method="get" action="{{ url_for('index') }}" class="fila" style="margin-bottom:12px;">
      <label for="mes" style="font-size:13px; font-weight:700; margin:0;">Mes del balance:</label>
      <select id="mes" name="mes" onchange="this.form.submit()">
        {% for m in meses_disponibles %}
          <option value="{{ m }}" {% if m == mes_seleccionado %}selected{% endif %}>{{ m }}</option>
        {% endfor %}
      </select>
      <span style="font-size:13px; color:#475569;">
        Total del mes (<strong>{{ mes_seleccionado }}</strong>): <strong>S/ {{ "%.2f"|format(total_mes) }}</strong>
      </span>
    </form>

    {% if balance_diario %}
      <div class="resumen-extremos">
        <div class="extremo-box max">
          <small>DÍA QUE SE VENDIÓ MÁS</small>
          <strong>{{ dia_mayor.fecha }} — S/ {{ "%.2f"|format(dia_mayor.total) }}</strong>
          <div style="font-size:12.5px; color:#166534;">{{ dia_mayor.cantidad }} pedido(s) enviado(s)</div>
        </div>
        <div class="extremo-box min">
          <small>DÍA QUE SE VENDIÓ MENOS</small>
          <strong>{{ dia_menor.fecha }} — S/ {{ "%.2f"|format(dia_menor.total) }}</strong>
          <div style="font-size:12.5px; color:#991b1b;">{{ dia_menor.cantidad }} pedido(s) enviado(s)</div>
        </div>
      </div>

      <div class="grafico-wrap">
        <strong style="display:block; margin-bottom:10px; color:#0f172a;">
          Gráfico comparativo de ventas por día ({{ mes_seleccionado }})
        </strong>
        {% for d in balance_diario %}
          {% set pct = (d.total / max_venta_dia * 100) if max_venta_dia > 0 else 0 %}
          <div class="barra-fila">
            <span><strong>{{ d.fecha }}</strong></span>
            <div class="barra-pista">
              <div class="barra-relleno {% if d.fecha == dia_mayor.fecha %}dia-max{% elif d.fecha == dia_menor.fecha and balance_diario|length > 1 %}dia-min{% endif %}" style="width: {{ '%.1f'|format(pct) }}%;"></div>
            </div>
            <span style="text-align:right; font-weight:700;">S/ {{ "%.2f"|format(d.total) }} ({{ d.cantidad }})</span>
          </div>
        {% endfor %}
      </div>

      <h3 style="margin:12px 0 6px;">Balance detallado por día</h3>
      <div class="table-wrap">
        <table>
          <tr>
            <th>Fecha</th><th>Pedidos enviados</th><th>Total vendido (S/)</th><th>Indicador</th>
          </tr>
          {% for d in balance_diario %}
            <tr>
              <td><strong>{{ d.fecha }}</strong></td>
              <td>{{ d.cantidad }}</td>
              <td><strong>S/ {{ "%.2f"|format(d.total) }}</strong></td>
              <td>
                {% if d.fecha == dia_mayor.fecha %}
                  <span class="badge badge-max">Mayor venta</span>
                {% elif d.fecha == dia_menor.fecha and balance_diario|length > 1 %}
                  <span class="badge badge-min">Menor venta</span>
                {% else %}
                  <span style="color:#64748b; font-size:12.5px;">Normal</span>
                {% endif %}
              </td>
            </tr>
          {% endfor %}
        </table>
      </div>
    {% else %}
      <p style="color:#64748b; font-size:13.5px; margin:8px 0 14px;">
        Aún no hay ventas registradas en el mes {{ mes_seleccionado }}. Cuando marques un pedido como <strong>Marcar enviado</strong>, aparecerá aquí y en el gráfico diario.
      </p>
    {% endif %}

    <h3 style="margin:18px 0 6px;">Registro guardado de ventas</h3>
    <div class="table-wrap">
      <table>
        <tr>
          <th>Fecha</th><th>Pedido #</th><th>Cliente</th><th>Detalle</th><th>Pago</th><th>Monto (S/)</th>
        </tr>
        {% for v in ventas_mes_ordenadas %}
          <tr>
            <td>{{ v.fecha }}</td>
            <td>#{{ v.pedido_id }}</td>
            <td><strong>{{ v.cliente }}</strong></td>
            <td>{{ v.detalle }}</td>
            <td><span class="badge badge-pago">{{ v.forma_pago }}</span></td>
            <td><strong>S/ {{ "%.2f"|format(v.total) }}</strong></td>
          </tr>
        {% else %}
          <tr><td colspan="6">Sin registros de ventas para este mes.</td></tr>
        {% endfor %}
      </table>
    </div>
  </div>

</body>
</html>
"""

def requiere_licencia_y_login(f):
    @wraps(f)
    def decorada(*args, **kwargs):
        data = cargar_datos()
        vigente, _, _ = estado_licencia(data)
        if not vigente:
            session.pop("usuario", None)
            return redirect(url_for("licencia_vencida"))
        usuario = session.get("usuario")
        if not usuario or usuario not in USUARIOS_OPERADORES:
            session.pop("usuario", None)
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorada

def redirigir_tablero(ok="", err="", mes=""):
    destino = url_for("index")
    params = []
    if ok:
        params.append("ok=" + quote(ok))
    if err:
        params.append("err=" + quote(err))
    if mes:
        params.append("mes=" + quote(mes))
    if params:
        destino += "?" + "&".join(params)
    resp = make_response(redirect(destino, code=303))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp

@app.route("/licencia-vencida", methods=["GET"])
def licencia_vencida():
    data = cargar_datos()
    vigente, _, fecha_cierre_texto = estado_licencia(data)
    if vigente:
        return redirect(url_for("login"))
    resp = make_response(render_template_string(
        HTML_LICENCIA_VENCIDA,
        fecha_cierre_texto=fecha_cierre_texto,
        error=request.args.get("err", ""),
        ok=request.args.get("ok", ""),
    ))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp

@app.route("/activar-licencia", methods=["POST"])
def activar_licencia():
    codigo = request.form.get("codigo_prog", "").strip()
    try:
        dias_extra = int(request.form.get("dias_extra", "30"))
    except ValueError:
        dias_extra = 30
    if dias_extra < 1:
        dias_extra = 30

    if codigo != CODIGO_MAESTRO_PROGRAMADOR:
        return redirect(url_for("licencia_vencida", err="Código de programador incorrecto."))

    data = cargar_datos()
    hoy = fecha_hoy_peru()
    nueva_fecha = (hoy + timedelta(days=dias_extra)).strftime("%Y-%m-%d")
    data["licencia"] = {
        "vence": nueva_fecha,
        "activa": True,
        "ultima_renovacion": hoy.strftime("%Y-%m-%d"),
    }
    guardar_datos(data)
    return redirect(url_for("login", ok=f"Licencia renovada por {dias_extra} días (hasta {nueva_fecha})."))

@app.route("/login", methods=["GET", "POST"])
def login():
    data = cargar_datos()
    vigente, dias_restantes, fecha_cierre_texto = estado_licencia(data)
    if not vigente:
        return redirect(url_for("licencia_vencida"))

    error = ""
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "").strip()
        if usuario in USUARIOS_OPERADORES and USUARIOS_OPERADORES[usuario] == password:
            session["usuario"] = usuario
            return redirect(url_for("index"))
        error = "Usuario o contraseña incorrectos."

    resp = make_response(render_template_string(
        HTML_LOGIN,
        error=error,
        fecha_cierre_texto=fecha_cierre_texto,
        dias_restantes=dias_restantes,
    ))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp

@app.route("/logout")
def logout():
    session.pop("usuario", None)
    return redirect(url_for("login"))

@app.route("/")
@requiere_licencia_y_login
def index():
    data = cargar_datos()
    _, dias_restantes, fecha_cierre_texto = estado_licencia(data)
    activas = [op for op in data["opciones_venta"] if op.get("activa", True)]
    ventas = data.get("ventas_registradas", [])

    hoy_str = fecha_hoy_peru().strftime("%Y-%m")
    meses_set = {v.get("fecha", "")[:7] for v in ventas if len(v.get("fecha", "")) >= 7}
    meses_set.add(hoy_str)
    meses_disponibles = sorted(meses_set, reverse=True)

    mes_sel = request.args.get("mes", hoy_str).strip()
    if mes_sel not in meses_disponibles:
        mes_sel = hoy_str

    ventas_mes = [v for v in ventas if v.get("fecha", "").startswith(mes_sel)]
    ventas_mes_ordenadas = sorted(ventas_mes, key=lambda x: (x.get("fecha", ""), x.get("id", 0)), reverse=True)

    agrupado = defaultdict(lambda: {"cantidad": 0, "total": 0.0})
    for v in ventas_mes:
        f = v.get("fecha", "")
        agrupado[f]["cantidad"] += 1
        agrupado[f]["total"] += float(v.get("total", 0.0))

    balance_diario = [
        {"fecha": f, "cantidad": info["cantidad"], "total": round(info["total"], 2)}
        for f, info in sorted(agrupado.items())
    ]

    total_mes = sum(d["total"] for d in balance_diario)
    total_ventas_hist = sum(float(v.get("total", 0.0)) for v in ventas)
    max_venta_dia = max((d["total"] for d in balance_diario), default=0.0)

    dia_mayor = max(balance_diario, key=lambda x: x["total"]) if balance_diario else None
    dia_menor = min(balance_diario, key=lambda x: x["total"]) if balance_diario else None

    html = render_template_string(
        HTML,
        usuario_actual=session.get("usuario", ""),
        fecha_cierre_texto=fecha_cierre_texto,
        dias_restantes=dias_restantes,
        opciones_activas=activas,
        formas_pago=FORMAS_PAGO,
        pendientes=data["pedidos_pendientes"],
        enviados=data["pedidos_enviados"],
        rechazados=data["pedidos_rechazados"],
        confirmado=data["ultimo_confirmado"],
        total_ventas_hist=total_ventas_hist,
        ventas=ventas,
        meses_disponibles=meses_disponibles,
        mes_seleccionado=mes_sel,
        total_mes=total_mes,
        balance_diario=balance_diario,
        dia_mayor=dia_mayor,
        dia_menor=dia_menor,
        max_venta_dia=max_venta_dia,
        ventas_mes_ordenadas=ventas_mes_ordenadas,
        msg_ok=request.args.get("ok", ""),
        msg_err=request.args.get("err", ""),
    )
    resp = make_response(html)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp

@app.route("/agregar_opcion", methods=["POST"])
@requiere_licencia_y_login
def agregar_opcion():
    data = cargar_datos()
    producto = request.form.get("producto", "").strip()
    try:
        precio = float(request.form.get("precio", "0"))
    except ValueError:
        return redirigir_tablero(err="Precio inválido.")
    if producto and precio >= 0:
        nuevo_id = data["contador_id"]
        data["contador_id"] += 1
        data["opciones_venta"].append({
            "id": nuevo_id,
            "producto": producto,
            "precio": precio,
            "activa": True,
        })
        guardar_datos(data)
        return redirigir_tablero(ok=f"Producto '{producto}' agregado.")
    return redirigir_tablero(err="Completa el nombre y un precio válido.")

@app.route("/retirar_opcion/<int:opcion_id>", methods=["POST"])
@requiere_licencia_y_login
def retirar_opcion(opcion_id):
    data = cargar_datos()
    for op in data["opciones_venta"]:
        if op["id"] == opcion_id:
            op["activa"] = False
            guardar_datos(data)
            return redirigir_tablero(ok=f"Producto '{op['producto']}' retirado.")
    return redirigir_tablero()

@app.route("/confirmar_pedido", methods=["POST"])
@requiere_licencia_y_login
def confirmar_pedido():
    data = cargar_datos()
    cliente = request.form.get("cliente", "").strip()
    celular = request.form.get("celular", "").strip()
    direccion = request.form.get("direccion", "").strip()
    forma_pago = request.form.get("forma_pago", "Efectivo").strip()
    if forma_pago not in FORMAS_PAGO:
        forma_pago = "Efectivo"

    items = []
    total = 0.0
    for op in data["opciones_venta"]:
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

    pedido_id = data["contador_id"]
    data["contador_id"] += 1
    pedido = {
        "id": pedido_id,
        "fecha": fecha_hoy_peru().strftime("%Y-%m-%d"),
        "cliente": cliente,
        "celular": celular,
        "direccion": direccion,
        "forma_pago": forma_pago,
        "detalle": ", ".join(items),
        "total": round(total, 2),
    }
    data["ultimo_confirmado"] = pedido
    data["pedidos_pendientes"].append(pedido)
    guardar_datos(data)
    return redirigir_tablero(ok=f"Pedido #{pedido['id']} de {cliente} registrado en Pendientes.")

@app.route("/marcar_enviado/<int:pedido_id>", methods=["POST"])
@requiere_licencia_y_login
def marcar_enviado(pedido_id):
    data = cargar_datos()
    for i, p in enumerate(data["pedidos_pendientes"]):
        if p["id"] == pedido_id:
            pedido_enviado = data["pedidos_pendientes"].pop(i)
            data["pedidos_enviados"].append(pedido_enviado)
            venta_id = data["contador_id"]
            data["contador_id"] += 1
            data["ventas_registradas"].append({
                "id": venta_id,
                "fecha": fecha_hoy_peru().strftime("%Y-%m-%d"),
                "pedido_id": pedido_enviado["id"],
                "cliente": pedido_enviado["cliente"],
                "detalle": pedido_enviado["detalle"],
                "forma_pago": pedido_enviado["forma_pago"],
                "total": float(pedido_enviado["total"]),
            })
            guardar_datos(data)
            return redirigir_tablero(ok=f"Pedido #{pedido_id} marcado como enviado y guardado en ventas.")
    return redirigir_tablero()

@app.route("/marcar_rechazado/<origen>/<int:pedido_id>", methods=["POST"])
@requiere_licencia_y_login
def marcar_rechazado(origen, pedido_id):
    data = cargar_datos()
    clave = "pedidos_pendientes" if origen == "pendientes" else "pedidos_enviados"
    for i, p in enumerate(data[clave]):
        if p["id"] == pedido_id:
            data["pedidos_rechazados"].append(data[clave].pop(i))
            guardar_datos(data)
            return redirigir_tablero(ok=f"Pedido #{pedido_id} movido a No contesta / Ya no lo quiso.")
    return redirigir_tablero()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
