"""Creaciones GMD - Python (Flask) + MySQL de XAMPP. Cada sección tiene su propio HTML en /templates."""
import csv, io, random, time, unicodedata
from datetime import date, datetime, timedelta
from decimal import Decimal
import pymysql
from flask import Flask, jsonify, request, render_template, Response
from flask.json.provider import DefaultJSONProvider
import config

MES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Setiembre', 'Octubre', 'Noviembre', 'Diciembre']
PRODUCTOS_BASE = [("Gigantografía", "m²", 25), ("Lona", "m²", 18), ("Vinil", "m²", 22), ("Sticker", "m²", 30), ("Diseño Gráfico", "servicio", 40)]
MATERIALES_BASE = ["Banner 13oz", "Lona frontlight", "Vinil adhesivo", "Sticker troquelado", "Canvas", "Sintra"]


class Prov(DefaultJSONProvider):
    @staticmethod
    def default(o):
        if isinstance(o, (date, datetime)): return o.isoformat()
        if isinstance(o, Decimal): return float(o)
        return DefaultJSONProvider.default(o)


app = Flask(__name__, static_folder="static", static_url_path="")
app.json = Prov(app)


# ---------- base de datos ----------
def conectar(con_bd=True):
    return pymysql.connect(host=config.DB_HOST, port=config.DB_PORT, user=config.DB_USER, password=config.DB_PASSWORD,
                           database=config.DB_NAME if con_bd else None, charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor)


def rows(sql, a=()):
    con = conectar()
    try:
        with con.cursor() as c:
            c.execute(sql, a)
            return list(c.fetchall())
    finally:
        con.close()


def run(sql, a=()):
    con = conectar()
    try:
        with con.cursor() as c:
            c.execute(sql, a)
            i = c.lastrowid
        con.commit()
        return i
    finally:
        con.close()


def iniciar_bd():
    con = conectar(False)
    with con.cursor() as c:
        for s in [x.strip() for x in open("schema.sql", encoding="utf-8").read().split(";") if x.strip()]:
            c.execute(s)
        c.execute("SELECT COUNT(*) n FROM productos")
        if c.fetchone()["n"] == 0:
            c.executemany("INSERT INTO productos (nombre,unidad,precio) VALUES (%s,%s,%s)", PRODUCTOS_BASE)
        c.execute("SELECT COUNT(*) n FROM materiales")
        if c.fetchone()["n"] == 0:
            c.executemany("INSERT INTO materiales (nombre) VALUES (%s)", [(m,) for m in MATERIALES_BASE])
    con.commit()
    con.close()


def log(icono, color, texto, detalle=""):
    run("INSERT INTO actividades (icono,color,texto,detalle,ts) VALUES (%s,%s,%s,%s,%s)", (icono, color, texto, detalle, int(time.time() * 1000)))


def norm(s):
    return unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode().lower()


def num(v):
    try: return float(str(v).replace(",", "."))
    except ValueError: return 0.0


@app.errorhandler(Exception)
def error(e):
    if request.path.startswith("/api"):
        code = getattr(e, "code", 500)
        return jsonify(error=str(getattr(e, "description", e))), (code if isinstance(code, int) else 500)
    raise e


# ---------- páginas (un HTML por sección) ----------
for ruta, plantilla in [("/", "inicio"), ("/publicaciones", "publicaciones"), ("/clientes", "clientes"), ("/pedidos", "pedidos"),
                        ("/productos", "productos"), ("/reportes", "reportes"), ("/configuracion", "configuracion"), ("/buscar", "buscar")]:
    app.add_url_rule(ruta, "pagina_" + plantilla, (lambda p: lambda: render_template(p + ".html", activa=p))(plantilla))

# ---------- clientes ----------
@app.get("/api/clientes")
def clientes_lista():
    return jsonify(rows("""SELECT c.*, COUNT(p.id) pedidos, COALESCE(SUM(p.total),0) total, MAX(p.fecha) ultima
                           FROM clientes c LEFT JOIN pedidos p ON p.cliente_id=c.id GROUP BY c.id ORDER BY total DESC"""))


@app.get("/api/clientes/<int:i>")
def cliente_uno(i):
    c = rows("SELECT * FROM clientes WHERE id=%s", (i,))
    if not c: return jsonify(error="No existe"), 404
    return jsonify(cliente=c[0], pedidos=rows(PED + " WHERE p.cliente_id=%s" + ORD, (i,)))


@app.post("/api/clientes")
def cliente_nuevo():
    d = request.get_json(force=True)
    if not d.get("nombre", "").strip(): return jsonify(error="Falta el nombre"), 400
    i = run("INSERT INTO clientes (nombre,telefono,correo,direccion,creado) VALUES (%s,%s,%s,%s,CURDATE())",
            (d["nombre"].strip(), d.get("telefono", ""), d.get("correo", ""), d.get("direccion", "")))
    log("👥", "#1a7dff", "Se registró un nuevo cliente", d["nombre"])
    return jsonify(id=i)


@app.put("/api/clientes/<int:i>")
def cliente_editar(i):
    d = request.get_json(force=True)
    run("UPDATE clientes SET nombre=%s,telefono=%s,correo=%s,direccion=%s WHERE id=%s",
        (d["nombre"].strip(), d.get("telefono", ""), d.get("correo", ""), d.get("direccion", ""), i))
    return jsonify(ok=True)


@app.delete("/api/clientes/<int:i>")
def cliente_borrar(i):
    if rows("SELECT COUNT(*) n FROM pedidos WHERE cliente_id=%s", (i,))[0]["n"]:
        return jsonify(error="El cliente tiene pedidos: no se puede eliminar"), 409
    run("DELETE FROM clientes WHERE id=%s", (i,))
    return jsonify(ok=True)


# ---------- pedidos (venta: cliente, medidas, material) ----------
PED = """SELECT p.id,p.cliente_id,c.nombre cliente,c.telefono,p.producto,p.ancho,p.alto,p.cantidad,p.material,p.total,p.fecha,p.estado,p.notas
         FROM pedidos p JOIN clientes c ON c.id=p.cliente_id"""
ORD = " ORDER BY p.fecha DESC, p.id DESC"


@app.get("/api/pedidos")
def pedidos_lista():
    w, a = [], []
    for campo, sql in [("desde", "p.fecha>=%s"), ("hasta", "p.fecha<=%s"), ("estado", "p.estado=%s"), ("producto", "p.producto=%s")]:
        if request.args.get(campo):
            w.append(sql); a.append(request.args[campo])
    return jsonify(rows(PED + (" WHERE " + " AND ".join(w) if w else "") + ORD, a))


@app.get("/api/pedidos/<int:i>")
def pedido_uno(i):
    r = rows(PED + " WHERE p.id=%s", (i,))
    return jsonify(r[0]) if r else (jsonify(error="No existe"), 404)


def datos_pedido(d):
    nombre = d.get("cliente", "").strip()
    if not nombre or not d.get("fecha"): raise ValueError("Falta el cliente o la fecha")
    c = rows("SELECT id FROM clientes WHERE nombre=%s", (nombre,))
    if c: cid = c[0]["id"]
    else:
        cid = run("INSERT INTO clientes (nombre,creado) VALUES (%s,CURDATE())", (nombre,))
        log("👥", "#1a7dff", "Se registró un nuevo cliente", nombre)
    mat = d.get("material", "").strip()
    if mat: run("INSERT IGNORE INTO materiales (nombre) VALUES (%s)", (mat,))
    return (cid, d["producto"], num(d.get("ancho")), num(d.get("alto")), num(d.get("cantidad")) or 1, mat,
            num(d.get("total")), d["fecha"], "C" if d.get("estado") == "C" else "P", d.get("notas", "")), nombre


@app.post("/api/pedidos")
def pedido_nuevo():
    v, nombre = datos_pedido(request.get_json(force=True))
    i = run("INSERT INTO pedidos (cliente_id,producto,ancho,alto,cantidad,material,total,fecha,estado,notas) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", v)
    log("🛒", "#ff8a1a", f"Nuevo pedido #{i:04d}", nombre)
    return jsonify(id=i)


@app.put("/api/pedidos/<int:i>")
def pedido_editar(i):
    v, nombre = datos_pedido(request.get_json(force=True))
    run("UPDATE pedidos SET cliente_id=%s,producto=%s,ancho=%s,alto=%s,cantidad=%s,material=%s,total=%s,fecha=%s,estado=%s,notas=%s WHERE id=%s", v + (i,))
    log("✏️", "#1a7dff", f"Se editó el pedido #{i:04d}", nombre)
    return jsonify(ok=True)


@app.post("/api/pedidos/<int:i>/estado")
def pedido_estado(i):
    run("UPDATE pedidos SET estado=IF(estado='C','P','C') WHERE id=%s", (i,))
    p = rows(PED + " WHERE p.id=%s", (i,))[0]
    log("✔" if p["estado"] == "C" else "🔄", "#18c866", f"Pedido #{i:04d} " + ("completado" if p["estado"] == "C" else "en proceso"), p["cliente"])
    return jsonify(ok=True)


@app.delete("/api/pedidos/<int:i>")
def pedido_borrar(i):
    run("DELETE FROM pedidos WHERE id=%s", (i,))
    return jsonify(ok=True)


# ---------- productos, materiales, publicaciones, actividades ----------
@app.get("/api/productos")
def productos_lista():
    return jsonify(rows("SELECT p.*, (SELECT COUNT(*) FROM pedidos o WHERE o.producto=p.nombre) pedidos FROM productos p ORDER BY id"))


@app.post("/api/productos")
def producto_nuevo():
    d = request.get_json(force=True)
    run("INSERT INTO productos (nombre,unidad,precio) VALUES (%s,%s,%s)", (d["nombre"].strip(), d.get("unidad", "m²"), num(d.get("precio"))))
    log("🏷", "#18c866", "Se actualizó el inventario", d["nombre"])
    return jsonify(ok=True)


@app.put("/api/productos/<int:i>")
def producto_editar(i):
    d = request.get_json(force=True)
    viejo = rows("SELECT nombre FROM productos WHERE id=%s", (i,))[0]["nombre"]
    run("UPDATE productos SET nombre=%s,unidad=%s,precio=%s WHERE id=%s", (d["nombre"].strip(), d["unidad"], num(d["precio"]), i))
    run("UPDATE pedidos SET producto=%s WHERE producto=%s", (d["nombre"].strip(), viejo))
    return jsonify(ok=True)


@app.delete("/api/productos/<int:i>")
def producto_borrar(i):
    n = rows("SELECT COUNT(*) n FROM pedidos WHERE producto=(SELECT nombre FROM productos WHERE id=%s)", (i,))[0]["n"]
    if n: return jsonify(error="Tiene pedidos: no se puede eliminar"), 409
    run("DELETE FROM productos WHERE id=%s", (i,))
    return jsonify(ok=True)


@app.get("/api/materiales")
def materiales_lista():
    return jsonify(rows("SELECT m.*, (SELECT COUNT(*) FROM pedidos o WHERE o.material=m.nombre) pedidos FROM materiales m ORDER BY nombre"))


@app.post("/api/materiales")
def material_nuevo():
    run("INSERT IGNORE INTO materiales (nombre) VALUES (%s)", (request.get_json(force=True)["nombre"].strip(),))
    return jsonify(ok=True)


@app.delete("/api/materiales/<int:i>")
def material_borrar(i):
    run("DELETE FROM materiales WHERE id=%s", (i,))
    return jsonify(ok=True)


@app.get("/api/publicaciones")
def pubs_lista():
    return jsonify(rows("SELECT * FROM publicaciones ORDER BY fecha DESC, id DESC"))


@app.post("/api/publicaciones")
def pub_nueva():
    d = request.get_json(force=True)
    if not d.get("titulo", "").strip(): return jsonify(error="Falta el título"), 400
    run("INSERT INTO publicaciones (titulo,descripcion,categoria,fecha,estado) VALUES (%s,%s,%s,%s,%s)",
        (d["titulo"], d.get("descripcion", ""), d.get("categoria", ""), d["fecha"], d.get("estado", "Publicada")))
    log("📣", "#ff2fa8", "Se creó una nueva publicación", d["titulo"])
    return jsonify(ok=True)


@app.put("/api/publicaciones/<int:i>")
def pub_editar(i):
    d = request.get_json(force=True)
    run("UPDATE publicaciones SET titulo=%s,descripcion=%s,categoria=%s,fecha=%s,estado=%s WHERE id=%s",
        (d["titulo"], d.get("descripcion", ""), d.get("categoria", ""), d["fecha"], d.get("estado", "Publicada"), i))
    return jsonify(ok=True)


@app.delete("/api/publicaciones/<int:i>")
def pub_borrar(i):
    run("DELETE FROM publicaciones WHERE id=%s", (i,))
    return jsonify(ok=True)


@app.get("/api/actividades")
def actividades():
    return jsonify(rows("SELECT icono i,color col,texto t,detalle s,ts FROM actividades ORDER BY id DESC LIMIT %s", (int(request.args.get("limite", 20)),)))


# ---------- inicio ----------
@app.get("/api/dashboard")
def dashboard():
    N = 30 if request.args.get("dias") == "30" else 7
    hoy = date.today()
    ym = hoy.strftime("%Y-%m")
    ped = rows("SELECT producto,total,fecha,estado FROM pedidos")
    prods = [p["nombre"] for p in rows("SELECT nombre FROM productos ORDER BY id LIMIT 5")]
    ser = {p: [0] * 7 for p in prods}
    total = previo = 0
    for o in ped:
        a = (hoy - o["fecha"]).days
        if a < 0: continue
        if a < N:
            total += float(o["total"])
            if o["producto"] in ser: ser[o["producto"]][6 - (a * 7 // N)] += float(o["total"])
        elif a < 2 * N:
            previo += float(o["total"])
    mes = [o for o in ped if o["fecha"].strftime("%Y-%m") == ym]
    return jsonify(
        publicaciones=rows("SELECT COUNT(*) n FROM publicaciones")[0]["n"], clientes=rows("SELECT COUNT(*) n FROM clientes")[0]["n"],
        proceso=sum(o["estado"] == "P" for o in ped), completados=sum(o["estado"] == "C" for o in ped),
        mes_pub=rows("SELECT COUNT(*) n FROM publicaciones WHERE DATE_FORMAT(fecha,'%%Y-%%m')=%s", (ym,))[0]["n"],
        mes_cli=rows("SELECT COUNT(*) n FROM clientes WHERE DATE_FORMAT(creado,'%%Y-%%m')=%s", (ym,))[0]["n"],
        mes_proceso=sum(o["estado"] == "P" for o in mes), mes_completados=sum(o["estado"] == "C" for o in mes),
        total=total, previo=previo, series=[{"n": p, "v": ser[p]} for p in prods],
        etiquetas=[(hoy - timedelta(days=(6 - i) * N // 7)).strftime("%d/%m") for i in range(7)],
        recientes=rows(PED + ORD + " LIMIT 8"),
        destacados=rows("SELECT c.id,c.nombre,COUNT(p.id) pedidos FROM clientes c JOIN pedidos p ON p.cliente_id=c.id GROUP BY c.id ORDER BY pedidos DESC LIMIT 5"),
        actividades=rows("SELECT icono i,color col,texto t,detalle s,ts FROM actividades ORDER BY id DESC LIMIT 4"))


# ---------- búsqueda ----------
def buscar(q):
    toks = norm(q).split()
    ped, cli = [], []
    for o in rows(PED + ORD):
        f = o["fecha"]
        hay = norm(" ".join([o["cliente"], o["telefono"] or "", o["producto"], o["material"] or "", o["notas"] or "", f.strftime("%d/%m/%Y"), str(f),
                             MES[f.month - 1], str(f.year), f"{float(o['ancho']):g}x{float(o['alto']):g}", f"{float(o['ancho']):g} x {float(o['alto']):g}",
                             f"#{o['id']:04d}", f"{o['id']:04d}", "completado" if o["estado"] == "C" else "en proceso"]))
        if all(t in hay for t in toks): ped.append(o)
    for c in rows("SELECT * FROM clientes"):
        if all(t in norm(c["nombre"] + " " + (c["telefono"] or "") + " " + (c["correo"] or "")) for t in toks): cli.append(c)
    return ped, cli


@app.get("/api/buscar")
def api_buscar():
    ped, cli = buscar(request.args.get("q", ""))
    return jsonify(pedidos=ped, clientes=cli)


# ---------- reportes ----------
@app.get("/api/reportes")
def reportes():
    anio = int(request.args.get("anio", date.today().year))
    m = {r["m"]: r for r in rows("""SELECT MONTH(fecha) m, COUNT(*) n, SUM(total) v, SUM(CASE WHEN estado='C' THEN total ELSE 0 END) c
                                    FROM pedidos WHERE YEAR(fecha)=%s GROUP BY MONTH(fecha)""", (anio,))}
    mensual = [{"mes": MES[i], "pedidos": int(m[i + 1]["n"]) if i + 1 in m else 0, "ventas": float(m[i + 1]["v"]) if i + 1 in m else 0,
                "cobrado": float(m[i + 1]["c"]) if i + 1 in m else 0} for i in range(12)]
    anual = rows("SELECT YEAR(fecha) anio, COUNT(*) pedidos, SUM(total) ventas FROM pedidos GROUP BY YEAR(fecha) ORDER BY anio")
    anios = sorted({a["anio"] for a in anual} | {date.today().year}, reverse=True)
    prods = rows("SELECT producto, COUNT(*) pedidos, SUM(total) ventas FROM pedidos WHERE YEAR(fecha)=%s GROUP BY producto", (anio,))
    return jsonify(anio=anio, anios=anios, mensual=mensual, anual=anual, productos=prods)


# ---------- CSV (descargas reales) ----------
def csv_resp(filas, nombre):
    s = io.StringIO()
    csv.writer(s).writerows(filas)
    return Response("\ufeff" + s.getvalue(), mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": f"attachment; filename={nombre}"})


def filas_pedidos(L):
    r = [["N° pedido", "Fecha", "Año", "Mes", "Cliente", "Teléfono", "Producto", "Ancho (m)", "Alto (m)", "Área total (m²)", "Cantidad", "Material", "Total (S/)", "Estado", "Notas"]]
    for o in L:
        r.append([f"{o['id']:04d}", o["fecha"].strftime("%d/%m/%Y"), o["fecha"].year, MES[o["fecha"].month - 1], o["cliente"], o["telefono"], o["producto"],
                  o["ancho"], o["alto"], round(float(o["ancho"] * o["alto"] * o["cantidad"]), 2), o["cantidad"], o["material"], o["total"],
                  "Completado" if o["estado"] == "C" else "En proceso", o["notas"]])
    return r


@app.get("/api/csv/<tipo>")
def csv_descarga(tipo):
    if tipo == "pedidos":
        return csv_resp(filas_pedidos(rows(PED + ORD)), "pedidos-gmd.csv")
    if tipo == "buscar":
        return csv_resp(filas_pedidos(buscar(request.args.get("q", ""))[0]), "busqueda-gmd.csv")
    if tipo == "cliente":
        return csv_resp(filas_pedidos(rows(PED + " WHERE p.cliente_id=%s" + ORD, (request.args.get("id"),))), "cliente-gmd.csv")
    if tipo == "clientes":
        r = [["Cliente", "Teléfono", "Correo", "Dirección", "Cliente desde", "Pedidos", "Total comprado (S/)", "Última compra"]]
        for c in rows("SELECT c.*, COUNT(p.id) n, COALESCE(SUM(p.total),0) t, MAX(p.fecha) u FROM clientes c LEFT JOIN pedidos p ON p.cliente_id=c.id GROUP BY c.id"):
            r.append([c["nombre"], c["telefono"], c["correo"], c["direccion"], c["creado"], c["n"], c["t"], c["u"] or ""])
        return csv_resp(r, "clientes-gmd.csv")
    if tipo == "mensual":
        r = [["Año", "Mes", "Pedidos", "Ventas (S/)", "Cobrado completados (S/)"]]
        for x in rows("""SELECT YEAR(fecha) a, MONTH(fecha) m, COUNT(*) n, SUM(total) v, SUM(CASE WHEN estado='C' THEN total ELSE 0 END) c
                         FROM pedidos GROUP BY YEAR(fecha), MONTH(fecha) ORDER BY a, m"""):
            r.append([x["a"], MES[x["m"] - 1], x["n"], x["v"], x["c"]])
        return csv_resp(r, "ganancias-por-mes-gmd.csv")
    if tipo == "anual":
        r = [["Año", "Pedidos", "Ventas (S/)"]] + [[x["a"], x["n"], x["v"]] for x in rows("SELECT YEAR(fecha) a, COUNT(*) n, SUM(total) v FROM pedidos GROUP BY YEAR(fecha) ORDER BY a")]
        return csv_resp(r, "ganancias-por-anio-gmd.csv")
    return jsonify(error="Tipo desconocido"), 404


# ---------- datos de ejemplo / borrar ----------
@app.post("/api/borrar")
def borrar():
    for t in ["pedidos", "clientes", "publicaciones", "actividades"]: run(f"DELETE FROM {t}")
    return jsonify(ok=True)


@app.post("/api/demo")
def demo():
    borrar()
    r = random.Random(42)
    hoy = date.today()
    nombres = ["Empresa ABC", "Juan Pérez", "Maribel Torres", "Taller Sol", "Luis García", "Patricia Rojas", "Carlos Mendoza", "DecoPrint", "Ana Quispe",
               "Bodega Don Pepe", "Farmacia Salud", "Colegio Los Andes", "Pollería El Sabor", "Gym Titan", "Inmobiliaria Lima", "Café Aroma", "Ferretería Central", "Boutique Luna"]
    ids = [run("INSERT INTO clientes (nombre,telefono,creado) VALUES (%s,%s,%s)", (n, "9" + str(r.randint(10000000, 99999999)), hoy - timedelta(days=r.randint(0, 650)))) for n in nombres]
    prods = rows("SELECT * FROM productos")
    mats = {"Gigantografía": "Banner 13oz", "Lona": "Lona frontlight", "Vinil": "Vinil adhesivo", "Sticker": "Sticker troquelado"}
    for k in range(80):
        p = r.choice(prods); z = r.choice([(1, 1), (2, 1), (3, 1), (2, 2), (3, 2), (4, 2), (6, 3), (1.5, 1)]); q = r.randint(1, 4)
        m2 = p["unidad"] == "m²"
        age = r.randint(0, 25 if k < 12 else 660)
        run("INSERT INTO pedidos (cliente_id,producto,ancho,alto,cantidad,material,total,fecha,estado) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (r.choice(ids), p["nombre"], z[0] if m2 else 0, z[1] if m2 else 0, q, mats.get(p["nombre"], "Digital"),
             round(float(p["precio"]) * (z[0] * z[1] * q if m2 else q), 2), hoy - timedelta(days=age), "P" if age < 18 and r.random() < .6 else "C"))
    for k in range(24):
        run("INSERT INTO publicaciones (titulo,descripcion,categoria,fecha) VALUES (%s,%s,%s,%s)",
            (["Promoción lonas publicitarias", "Gigantografías para eventos", "Vinil decorativo", "Stickers personalizados", "Diseño de logos", "Banners para tiendas"][k % 6],
             "Trabajo de gran formato con la mejor calidad.", prods[k % 5]["nombre"], hoy - timedelta(days=r.randint(0, 300))))
    log("🏷", "#18c866", "Se cargaron datos de ejemplo")
    return jsonify(ok=True)


if __name__ == "__main__":
    try:
        iniciar_bd()
    except pymysql.err.OperationalError as e:
        raise SystemExit(f"\nNo se pudo conectar a MySQL ({e}).\nAbre XAMPP y pulsa START en MySQL, luego vuelve a ejecutar.\n")
    print(f"Sistema listo: http://localhost:{config.APP_PORT}")
    app.run(host=config.APP_HOST, port=config.APP_PORT)
