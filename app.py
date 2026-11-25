import calendar
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

DIAS_CORTO_ES = {
    0: "Lun",
    1: "Mar",
    2: "Mié",
    3: "Jue",
    4: "Vie",
    5: "Sáb",
    6: "Dom",
}

DIAS_LARGO_ES = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}

MESES_ES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}

def fecha_hoy_peru():
    return datetime.now(ZONA_HORARIA).date()

def generar_rango_3_anos_meses(fecha_base):
    """Genera 36 meses consecutivos (3 años) desde el mes actual."""
    meses = []
    anio = fecha_base.year
    mes = fecha_base.month
    for _ in range(36):
        clave = f"{anio:04d}-{mes:02d}"
        etiqueta = f"{MESES_ES[mes]} {anio}"
        meses.append({"clave": clave, "etiqueta": etiqueta})
        mes += 1
        if mes > 12:
            mes = 1
            anio += 1
    return meses

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
        "ventas_registradas": [],
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
    label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 5px; color: #334155; }
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
    .err { background: #fee2e2; color: #7f1d1d; border: 1px solid #fca5a5; padding: 10px 12px; border-radius: 8px; font-size: 13px; font-weight: 600; margin-bottom: 14px; }
    .ok { background: #dcfce7; color: #14532d; border: 1px solid #86efac; padding: 10px 12px; border-radius: 8px; font-size: 13px; font-weight: 600; margin-bottom: 14px; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Programa Cerrado — Licencia Vencida</h1>
    <p>El ciclo mensual del sistema ha finalizado. Para reactivarlo por otro mes, ingresa el código único de programador.</p>
    <div class="box-info"><strong>Fecha de cierre anterior:</strong> {{ fecha_cierre_texto }}</div>
    {% if error %}<div class="err">{{ error }}</div>{% endif %}
    {% if ok %}<div class="ok">{{ ok }}</div>{% endif %}
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
    label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 5px; color: #334155; }
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
    .err { background: #fee2e2; color: #7f1d1d; border: 1px solid #fca5a5; padding: 10px 12px; border-radius: 8px; font-size: 13px; font-weight: 600; margin-bottom: 14px; }
  </style>
</head>
<body>
  <div class="login-card">
    <h1>Acceso al Sistema</h1>
    <p>Ingresa tu usuario y contraseña única asignados para continuar a pedidos.</p>
    <div class="lic-tag">Licencia vigente hasta {{ fecha_cierre_texto }} ({{ dias_restantes }} días)</div>
    {% if error %}<div class="err">{{ error }}</div>{% endif %}
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

HTML_INDEX = """
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
      max-width: 1140px;
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
    .btn-balance {
      background: #2563eb;
      color: #ffffff;
      padding: 7px 14px;
      font-size: 13px;
      border-radius: 8px;
      text-decoration: none;
      font-weight: 700;
    }
    .btn-balance:hover { filter: brightness(1.08); }
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
    <div class="user-box">
      <span>Usuario: <strong>{{ usuario_actual }}</strong></span>
      <span class="pill {% if dias_restantes is not none and dias_restantes <= 5 %}alerta{% endif %}">
        Licencia vence {{ fecha_cierre_texto }} ({{ dias_restantes }}d)
      </span>
      <a href="{{ url_for('balance_mensual') }}" target="_blank" rel="noopener noreferrer" class="btn-balance">Balance</a>
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
      <span>Cancelados / No contesta</span>
      <strong>{{ rechazados|length }}</strong>
    </div>
    <div class="kpi">
      <span>Total dinero ingresado (S/)</span>
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
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
      <h2 style="margin:0;">2. Tabla de Cliente y Registro de Pedido</h2>
      <a href="{{ url_for('balance_mensual') }}" target="_blank" rel="noopener noreferrer" class="btn-balance">Balance</a>
    </div>

    <form method="post" action="{{ url_for('confirmar_pedido') }}" style="margin-top:12px;">
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
      <h3 style="margin-top:16px;">Tabla de cliente / pedido confirmado</h3>
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
                  <button type="submit" class="rechazar">Cancelar / No contesta</button>
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
                <button type="submit" class="rechazar">Cancelar / No contesta</button>
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
      <span>5. Cancelados / No contesta</span>
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
            <td><span class="badge badge-ambar">Cancelado / No contesta</span></td>
            <td><strong>{{ p.cliente }}</strong></td>
            <td>{{ p.celular }}</td>
            <td>{{ p.direccion }}</td>
            <td><span class="badge badge-pago">{{ p.forma_pago }}</span></td>
            <td>{{ p.detalle }}</td>
            <td>S/ {{ "%.2f"|format(p.total) }}</td>
          </tr>
        {% else %}
          <tr><td colspan="8">No hay pedidos cancelados o marcados como no contesta.</td></tr>
        {% endfor %}
      </table>
    </div>
  </div>

</body>
</html>
"""

HTML_BALANCE_CALENDARIO = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Balance del Mes — Calendario</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: 'Segoe UI', Arial, sans-serif;
      max-width: 1100px;
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
    .btn-volver {
      background: #334155;
      color: #f8fafc;
      padding: 7px 14px;
      border-radius: 8px;
      text-decoration: none;
      font-size: 13px;
      font-weight: 700;
      border: 1px solid #475569;
    }
    .btn-volver:hover { background: #475569; }
    .card {
      background: #ffffff;
      padding: 18px;
      border-radius: 12px;
      margin-bottom: 18px;
      box-shadow: 0 6px 18px rgba(0,0,0,.18);
      border-top: 5px solid #2563eb;
    }
    .fila { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin-bottom: 14px; }
    select {
      padding: 8px 12px;
      border-radius: 8px;
      border: 1px solid #cbd5e1;
      font-size: 14px;
      font-weight: 600;
    }

    .balance-mes-box {
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: 10px;
      padding: 14px;
      margin-bottom: 16px;
    }
    .balance-mes-box h2 { margin: 0 0 10px; font-size: 17px; color: #1e3a8a; }
    .resumen-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }
    .res-item {
      background: #ffffff;
      border: 1px solid #dbeafe;
      border-radius: 8px;
      padding: 10px 12px;
    }
    .res-item small { display: block; font-size: 11.5px; color: #64748b; font-weight: 700; }
    .res-item strong { font-size: 17px; color: #0f172a; }

    .grafico-wrap {
      background: #ffffff;
      border: 1px solid #dbeafe;
      border-radius: 8px;
      padding: 12px;
    }
    .barra-fila {
      display: grid;
      grid-template-columns: 78px 1fr 185px;
      gap: 10px;
      align-items: center;
      margin-bottom: 6px;
      font-size: 12.5px;
    }
    .barra-pista {
      background: #e2e8f0;
      border-radius: 999px;
      height: 15px;
      overflow: hidden;
    }
    .barra-relleno {
      height: 100%;
      background: #16a34a;
      border-radius: 999px;
    }

    .cal-grid {
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 8px;
      margin-top: 10px;
    }
    .cal-cabecera {
      background: #1e293b;
      color: #f8fafc;
      text-align: center;
      padding: 8px 4px;
      border-radius: 8px;
      font-size: 12.5px;
      font-weight: 700;
    }
    .cal-vacio {
      background: #f8fafc;
      border: 1px dashed #e2e8f0;
      border-radius: 10px;
      min-height: 92px;
    }
    .cal-dia-link {
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      min-height: 92px;
      padding: 8px;
      border-radius: 10px;
      text-decoration: none;
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      color: #0f172a;
      transition: transform .12s ease, border-color .12s ease, background .12s ease;
    }
    .cal-dia-link:hover {
      transform: translateY(-2px);
      border-color: #2563eb;
      background: #eff6ff;
    }
    .cal-dia-link.con-venta {
      background: #f0fdf4;
      border-color: #86efac;
    }
    .cal-dia-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12px;
      font-weight: 700;
    }
    .cal-num { font-size: 15px; font-weight: 800; color: #0f172a; }
    .cal-monto { font-size: 12.5px; font-weight: 800; color: #15803d; margin-top: 3px; }
    .cal-meta { font-size: 11px; color: #475569; line-height: 1.3; }
    .badge-hoy {
      background: #2563eb;
      color: #fff;
      padding: 1px 6px;
      border-radius: 999px;
      font-size: 10px;
    }
  </style>
</head>
<body>

  <div class="topbar">
    <h1>Balance del Mes — Calendario</h1>
    <div style="display:flex; gap:8px; align-items:center;">
      <a href="{{ url_for('index') }}" class="btn-volver">← Volver a Pedidos</a>
      <a href="{{ url_for('logout') }}" class="btn-volver">Cerrar sesión</a>
    </div>
  </div>

  <div class="card">
    <form method="get" action="{{ url_for('balance_mensual') }}" class="fila">
      <label for="mes" style="font-weight:700; font-size:14px;">Mes de balance (3 años):</label>
      <select id="mes" name="mes" onchange="this.form.submit()">
        {% for m in meses_disponibles %}
          <option value="{{ m.clave }}" {% if m.clave == mes_seleccionado %}selected{% endif %}>{{ m.etiqueta }}</option>
        {% endfor %}
      </select>
    </form>

    <div class="balance-mes-box">
      <h2>Balance del mes — {{ etiqueta_mes_seleccionado }}</h2>
      <div class="resumen-grid">
        <div class="res-item">
          <small>TOTAL DINERO INGRESADO</small>
          <strong>S/ {{ "%.2f"|format(total_mes) }}</strong>
        </div>
        <div class="res-item">
          <small>PEDIDOS ENVIADOS (MES)</small>
          <strong>{{ enviados_mes }}</strong>
        </div>
        <div class="res-item">
          <small>PEDIDOS CANCELADOS (MES)</small>
          <strong>{{ cancelados_mes }}</strong>
        </div>
      </div>

      <div class="grafico-wrap">
        <strong style="display:block; margin-bottom:8px; font-size:13px; color:#0f172a;">
          Gráfico de ventas por día en {{ etiqueta_mes_seleccionado }}
        </strong>
        {% for celda in dias_mes %}
          {% set pct = (celda.total / max_venta_dia * 100) if max_venta_dia > 0 else 0 %}
          <div class="barra-fila">
            <span><strong>{{ celda.dia_corto }} {{ celda.dia }}</strong></span>
            <div class="barra-pista">
              <div class="barra-relleno" style="width: {{ '%.1f'|format(pct) }}%;"></div>
            </div>
            <span style="text-align:right; font-weight:700;">
              S/ {{ "%.2f"|format(celda.total) }} · {{ celda.cantidad }} env · {{ celda.cancelados }} canc
            </span>
          </div>
        {% endfor %}
      </div>
    </div>

    <p style="margin:0 0 8px; font-size:13.5px; color:#475569;">
      Aprieta cualquier día del calendario para abrir una ventana nueva con las ventas guardadas de ese día:
    </p>

    <div class="cal-grid">
      {% for cab in cabeceras_dias %}
        <div class="cal-cabecera">{{ cab }}</div>
      {% endfor %}

      {% for celda in celdas_calendario %}
        {% if celda is none %}
          <div class="cal-vacio"></div>
        {% else %}
          <a href="{{ url_for('balance_dia', fecha_iso=celda.fecha) }}"
             target="_blank"
             rel="noopener noreferrer"
             class="cal-dia-link {% if celda.total > 0 %}con-venta{% endif %}">
            <div class="cal-dia-top">
              <span class="cal-num">{{ celda.dia }}</span>
              <span>{{ celda.dia_corto }}</span>
            </div>
            <div>
              <div class="cal-monto">S/ {{ "%.2f"|format(celda.total) }}</div>
              <div class="cal-meta">
                Env: {{ celda.cantidad }} · Canc: {{ celda.cancelados }}
                {% if celda.es_hoy %}<span class="badge-hoy">Hoy</span>{% endif %}
              </div>
            </div>
          </a>
        {% endif %}
      {% endfor %}
    </div>
  </div>

</body>
</html>
"""

HTML_BALANCE_DIA = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Balance del {{ fecha_titulo }}</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: 'Segoe UI', Arial, sans-serif;
      max-width: 1040px;
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
    .topbar h1 { margin: 0; font-size: 21px; }
    .btn-link {
      background: #2563eb;
      color: #ffffff;
      padding: 7px 13px;
      border-radius: 8px;
      text-decoration: none;
      font-size: 13px;
      font-weight: 700;
    }
    .btn-sec {
      background: #334155;
      color: #f8fafc;
      padding: 7px 13px;
      border-radius: 8px;
      text-decoration: none;
      font-size: 13px;
      font-weight: 700;
      border: 1px solid #475569;
    }
    .card {
      background: #ffffff;
      padding: 18px;
      border-radius: 12px;
      margin-bottom: 18px;
      box-shadow: 0 6px 18px rgba(0,0,0,.18);
      border-top: 5px solid #16a34a;
    }
    .balance-dia-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }
    .stat-box {
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-radius: 10px;
      padding: 12px 14px;
    }
    .stat-box small { display: block; font-size: 11.5px; color: #64748b; font-weight: 700; }
    .stat-box strong { font-size: 19px; color: #0f172a; }

    .grafico-dia {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 14px;
      margin-bottom: 16px;
    }
    .g-fila {
      display: grid;
      grid-template-columns: 150px 1fr 90px;
      gap: 10px;
      align-items: center;
      margin-bottom: 8px;
      font-size: 13px;
      font-weight: 600;
    }
    .g-pista {
      background: #e2e8f0;
      border-radius: 999px;
      height: 18px;
      overflow: hidden;
    }
    .g-barra { height: 100%; border-radius: 999px; }
    .g-barra.env { background: #16a34a; }
    .g-barra.canc { background: #d97706; }

    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid #e2e8f0; padding: 9px; text-align: left; font-size: 13.5px; }
    th { background: #f1f5f9; color: #0f172a; }
    .badge-pago {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 999px;
      font-size: 11.5px;
      font-weight: 700;
      background: #e0e7ff;
      color: #1d4ed8;
    }
  </style>
</head>
<body>

  <div class="topbar">
    <h1>Balance del Día — {{ fecha_titulo }}</h1>
    <div style="display:flex; gap:8px; flex-wrap:wrap;">
      <a href="{{ url_for('balance_mensual', mes=mes_clave) }}" class="btn-link">← Calendario del mes</a>
      <a href="{{ url_for('index') }}" class="btn-sec">Tablero de Pedidos</a>
    </div>
  </div>

  <div class="card">
    <div class="balance-dia-grid">
      <div class="stat-box">
        <small>TOTAL DINERO INGRESADO</small>
        <strong>S/ {{ "%.2f"|format(total_dia) }}</strong>
      </div>
      <div class="stat-box">
        <small>PEDIDOS ENVIADOS</small>
        <strong>{{ ventas_dia|length }}</strong>
      </div>
      <div class="stat-box">
        <small>PEDIDOS CANCELADOS</small>
        <strong>{{ cancelados_dia|length }}</strong>
      </div>
    </div>

    <div class="grafico-dia">
      <strong style="display:block; margin-bottom:10px; font-size:13.5px; color:#0f172a;">
        Gráfico del día: Enviados vs Cancelados ({{ fecha_titulo }})
      </strong>
      {% set pct_env = (ventas_dia|length / max_conteo * 100) if max_conteo > 0 else 0 %}
      {% set pct_canc = (cancelados_dia|length / max_conteo * 100) if max_conteo > 0 else 0 %}
      <div class="g-fila">
        <span>Pedidos enviados</span>
        <div class="g-pista"><div class="g-barra env" style="width: {{ '%.1f'|format(pct_env) }}%;"></div></div>
        <span style="text-align:right;">{{ ventas_dia|length }}</span>
      </div>
      <div class="g-fila" style="margin-bottom:0;">
        <span>Pedidos cancelados</span>
        <div class="g-pista"><div class="g-barra canc" style="width: {{ '%.1f'|format(pct_canc) }}%;"></div></div>
        <span style="text-align:right;">{{ cancelados_dia|length }}</span>
      </div>
    </div>

    <h3 style="margin:0 0 8px;">Ventas guardadas de este día</h3>
    <div class="table-wrap">
      <table>
        <tr>
          <th># Venta</th>
          <th>Pedido #</th>
          <th>Cliente</th>
          <th>Detalle</th>
          <th>Pago</th>
          <th>Monto (S/)</th>
        </tr>
        {% for v in ventas_dia %}
          <tr>
            <td>{{ v.id }}</td>
            <td>#{{ v.pedido_id }}</td>
            <td><strong>{{ v.cliente }}</strong></td>
            <td>{{ v.detalle }}</td>
            <td><span class="badge-pago">{{ v.forma_pago }}</span></td>
            <td><strong>S/ {{ "%.2f"|format(v.total) }}</strong></td>
          </tr>
        {% else %}
          <tr><td colspan="6">No hay ventas guardadas para {{ fecha_titulo }}.</td></tr>
        {% endfor %}
      </table>
    </div>

    <h3 style="margin:18px 0 8px;">Pedidos cancelados / no contesta de este día</h3>
    <div class="table-wrap">
      <table>
        <tr>
          <th>Pedido #</th>
          <th>Cliente</th>
          <th>Celular</th>
          <th>Detalle</th>
          <th>Pago</th>
          <th>Monto (S/)</th>
        </tr>
        {% for c in cancelados_dia %}
          <tr>
            <td>#{{ c.id }}</td>
            <td><strong>{{ c.cliente }}</strong></td>
            <td>{{ c.celular }}</td>
            <td>{{ c.detalle }}</td>
            <td><span class="badge-pago">{{ c.forma_pago }}</span></td>
            <td>S/ {{ "%.2f"|format(c.total) }}</td>
          </tr>
        {% else %}
          <tr><td colspan="6">No hay pedidos cancelados en {{ fecha_titulo }}.</td></tr>
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
    total_ventas_hist = round(sum(float(v.get("total", 0.0)) for v in ventas), 2)

    html = render_template_string(
        HTML_INDEX,
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
        msg_ok=request.args.get("ok", ""),
        msg_err=request.args.get("err", ""),
    )
    resp = make_response(html)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp

@app.route("/balance")
@requiere_licencia_y_login
def balance_mensual():
    data = cargar_datos()
    ventas = data.get("ventas_registradas", [])
    rechazados = data.get("pedidos_rechazados", [])
    hoy = fecha_hoy_peru()
    hoy_str = hoy.strftime("%Y-%m")
    hoy_iso = hoy.strftime("%Y-%m-%d")

    meses_disponibles = generar_rango_3_anos_meses(hoy)
    claves_validas = {m["clave"] for m in meses_disponibles}

    mes_sel = request.args.get("mes", hoy_str).strip()
    if mes_sel not in claves_validas:
        mes_sel = hoy_str

    etiqueta_mes_sel = next(m["etiqueta"] for m in meses_disponibles if m["clave"] == mes_sel)
    anio_sel, mes_num = map(int, mes_sel.split("-"))

    resumen_dia = defaultdict(lambda: {"cantidad": 0, "total": 0.0, "cancelados": 0})
    for v in ventas:
        f = v.get("fecha", "")
        if f.startswith(mes_sel):
            resumen_dia[f]["cantidad"] += 1
            resumen_dia[f]["total"] += float(v.get("total", 0.0))

    for c in rechazados:
        f = c.get("fecha_cancelado") or c.get("fecha") or hoy_iso
        if f.startswith(mes_sel):
            resumen_dia[f]["cancelados"] += 1

    primer_dia_semana, total_dias = calendar.monthrange(anio_sel, mes_num)
    celdas_calendario = [None] * primer_dia_semana
    dias_mes = []
    total_mes = 0.0
    enviados_mes = 0
    cancelados_mes = 0

    for dia_n in range(1, total_dias + 1):
        fecha_obj = datetime(anio_sel, mes_num, dia_n).date()
        fecha_iso = fecha_obj.strftime("%Y-%m-%d")
        monto_dia = round(resumen_dia[fecha_iso]["total"], 2)
        cant_dia = resumen_dia[fecha_iso]["cantidad"]
        canc_dia = resumen_dia[fecha_iso]["cancelados"]

        total_mes += monto_dia
        enviados_mes += cant_dia
        cancelados_mes += canc_dia

        item_dia = {
            "dia": dia_n,
            "fecha": fecha_iso,
            "dia_corto": DIAS_CORTO_ES[fecha_obj.weekday()],
            "cantidad": cant_dia,
            "cancelados": canc_dia,
            "total": monto_dia,
            "es_hoy": (fecha_iso == hoy_iso),
        }
        dias_mes.append(item_dia)
        celdas_calendario.append(item_dia)

    max_venta_dia = max((d["total"] for d in dias_mes), default=0.0)

    html = render_template_string(
        HTML_BALANCE_CALENDARIO,
        meses_disponibles=meses_disponibles,
        mes_seleccionado=mes_sel,
        etiqueta_mes_seleccionado=etiqueta_mes_sel,
        total_mes=round(total_mes, 2),
        enviados_mes=enviados_mes,
        cancelados_mes=cancelados_mes,
        max_venta_dia=max_venta_dia,
        dias_mes=dias_mes,
        cabeceras_dias=["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
        celdas_calendario=celdas_calendario,
    )
    resp = make_response(html)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp

@app.route("/balance/dia/<fecha_iso>")
@requiere_licencia_y_login
def balance_dia(fecha_iso):
    try:
        fecha_obj = datetime.strptime(fecha_iso, "%Y-%m-%d").date()
    except ValueError:
        return redirect(url_for("balance_mensual"))

    data = cargar_datos()
    ventas = data.get("ventas_registradas", [])
    rechazados = data.get("pedidos_rechazados", [])

    ventas_dia = sorted(
        [v for v in ventas if v.get("fecha") == fecha_iso],
        key=lambda x: x.get("id", 0),
        reverse=True,
    )
    cancelados_dia = sorted(
        [c for c in rechazados if (c.get("fecha_cancelado") or c.get("fecha")) == fecha_iso],
        key=lambda x: x.get("id", 0),
        reverse=True,
    )

    total_dia = round(sum(float(v.get("total", 0.0)) for v in ventas_dia), 2)
    max_conteo = max(len(ventas_dia), len(cancelados_dia), 1)
    fecha_titulo = f"{DIAS_LARGO_ES[fecha_obj.weekday()]} {fecha_obj.day} de {MESES_ES[fecha_obj.month]} {fecha_obj.year}"
    mes_clave = fecha_obj.strftime("%Y-%m")

    html = render_template_string(
        HTML_BALANCE_DIA,
        fecha_titulo=fecha_titulo,
        mes_clave=mes_clave,
        ventas_dia=ventas_dia,
        cancelados_dia=cancelados_dia,
        total_dia=total_dia,
        max_conteo=max_conteo,
    )
    resp = make_response(html)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
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
            fecha_envio = fecha_hoy_peru().strftime("%Y-%m-%d")
            pedido_enviado["fecha_enviado"] = fecha_envio
            data["pedidos_enviados"].append(pedido_enviado)
            venta_id = data["contador_id"]
            data["contador_id"] += 1
            data["ventas_registradas"].append({
                "id": venta_id,
                "fecha": fecha_envio,
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
            pedido_canc = data[clave].pop(i)
            pedido_canc["fecha_cancelado"] = fecha_hoy_peru().strftime("%Y-%m-%d")
            data["pedidos_rechazados"].append(pedido_canc)
            guardar_datos(data)
            return redirigir_tablero(ok=f"Pedido #{pedido_id} movido a Cancelados / No contesta.")
    return redirigir_tablero()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
