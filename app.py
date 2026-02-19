import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Comidería Pro", layout="wide", page_icon="🍔")

# --- FUNCIONES DE BASE DE DATOS ---
def get_connection():
    return sqlite3.connect('negocio.db')

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Tabla de Productos
    c.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            costo REAL NOT NULL,
            precio REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    ''')

    # Tabla de Clientes
    c.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            empresa TEXT,
            deuda REAL DEFAULT 0
        )
    ''')

    # Tabla de Ventas (¡AHORA CON DETALLES!)
    c.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cliente_id INTEGER,
            total REAL NOT NULL,
            metodo_pago TEXT,
            detalles TEXT,  -- Nueva columna para guardar qué se llevó
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    ''')

    # Tabla de Abonos
    c.execute('''
        CREATE TABLE IF NOT EXISTS abonos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cliente_id INTEGER,
            monto REAL NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    ''')

    # Tabla de Gastos
    c.execute('''
        CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            descripcion TEXT,
            monto REAL NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

def ejecutar_consulta(query, params=(), fetch=False):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    data = None
    if fetch:
        data = cursor.fetchall()
    conn.commit()
    conn.close()
    return data

# Inicializamos la base de datos
init_db()

st.title("🏪 Sistema de Gestión - Comidería")

menu = ["Vender", "Inventario", "Clientes (Fiados y Abonos)", "Caja y Gastos"]
choice = st.sidebar.selectbox("Menú Principal", menu)

# --- MÓDULO VENDER (CARRITO + VUELTO) ---
# Importante: Asegúrate que 'choice' coincida con el nombre en tu lista 'menu'
if "Vender" in choice: 
    st.header("🛒 Terminal de Ventas")

    # 1. Inicializar el carrito en la memoria si no existe
    if 'carrito' not in st.session_state:
        st.session_state.carrito = []
    if 'total_acumulado' not in st.session_state:
        st.session_state.total_acumulado = 0.0

    prods = ejecutar_consulta("SELECT id, nombre, precio, stock FROM productos WHERE stock > 0", fetch=True)
    
    if not prods:
        st.warning("⚠️ No hay productos en inventario.")
    else:
        col_sel, col_cart = st.columns([1, 1])

        with col_sel:
            st.subheader("Seleccionar Productos")
            # Creamos el selector de productos
            opciones_p = {f"{p[1]} (${p[2]} | Stock: {p[3]})": p for p in prods}
            sel_p = st.selectbox("Buscar Producto:", opciones_p.keys())
            id_p, nombre_p, precio_p, stock_p = opciones_p[sel_p]
            
            cant = st.number_input("Cantidad:", min_value=1, max_value=stock_p, value=1)
            
            if st.button("➕ Agregar al Carrito", use_container_width=True):
                # Añadir producto a la lista temporal
                item = {
                    "id": id_p, 
                    "nombre": nombre_p, 
                    "cantidad": cant, 
                    "precio": precio_p, 
                    "subtotal": precio_p * cant
                }
                st.session_state.carrito.append(item)
                st.session_state.total_acumulado += item["subtotal"]
                st.toast(f"Agregado: {nombre_p}")

            if st.button("🗑️ Vaciar Carrito"):
                st.session_state.carrito = []
                st.session_state.total_acumulado = 0.0
                st.rerun()

        with col_cart:
            st.subheader("Resumen de Compra")
            if st.session_state.carrito:
                # Dibujamos la lista de lo que lleva
                for i, item in enumerate(st.session_state.carrito):
                    st.write(f"**{item['cantidad']}x** {item['nombre']} — ${item['subtotal']:,.2f}")
                
                st.divider()
                st.markdown(f"## TOTAL: **${st.session_state.total_acumulado:,.2f}**")
                
                # --- CALCULADORA DE VUELTO ---
                pago_con = st.number_input("Paga con (Billete):", min_value=0.0, step=50.0)
                if pago_con > 0:
                    vuelto = pago_con - st.session_state.total_acumulado
                    if vuelto >= 0:
                        st.success(f"💰 Vuelto a entregar: **${vuelto:,.2f}**")
                    else:
                        st.error(f"Faltan: ${abs(vuelto):,.2f}")

                st.divider()
                metodo = st.radio("Forma de pago:", ["Contado", "Crédito (Fiado)"])
                
                id_c = None
                if metodo == "Crédito (Fiado)":
                    clis = ejecutar_consulta("SELECT id, nombre, empresa FROM clientes", fetch=True)
                    if clis:
                        opciones_c = {f"{c[1]} ({c[2]})": c[0] for c in clis}
                        sel_c = st.selectbox("Asignar a Cliente:", opciones_c.keys())
                        id_c = opciones_c[sel_c]
                    else:
                        st.error("No hay clientes registrados en la base de datos.")

                if st.button("FINALIZAR VENTA 🏁", type="primary", use_container_width=True):
                    # Crear el texto resumen para el historial
                    detalles_finales = ", ".join([f"{item['cantidad']}x {item['nombre']}" for item in st.session_state.carrito])
                    
                    # 1. Guardar la venta
                    ejecutar_consulta("INSERT INTO ventas (cliente_id, total, metodo_pago, detalles) VALUES (?,?,?,?)", 
                                      (id_c, st.session_state.total_acumulado, metodo, detalles_finales))
                    
                    # 2. Descontar stock de cada producto
                    for item in st.session_state.carrito:
                        ejecutar_consulta("UPDATE productos SET stock = stock - ? WHERE id = ?", (item['cantidad'], item['id']))
                    
                    # 3. Si es fiado, subir la deuda
                    if metodo == "Crédito (Fiado)":
                        ejecutar_consulta("UPDATE clientes SET deuda = deuda + ? WHERE id = ?", (st.session_state.total_acumulado, id_c))
                    
                    # Limpiar todo para la siguiente venta
                    st.session_state.carrito = []
                    st.session_state.total_acumulado = 0.0
                    st.success("✅ ¡Venta Guardada!")
                    st.balloons()
                    st.rerun()
            else:
                st.info("El carrito está vacío. Agrega productos a la izquierda.")

# --- MÓDULO INVENTARIO ---
elif "Inventario" in choice:
    st.header("📦 Control de Inventario")
    
    with st.expander("➕ Agregar Nuevo Producto"):
        c1, c2, c3, c4 = st.columns(4)
        n = c1.text_input("Nombre del Producto")
        co = c2.number_input("Costo (Lo que te cuesta)", min_value=0.0)
        pr = c3.number_input("Venta (Al público)", min_value=0.0)
        stk = c4.number_input("Stock Inicial", min_value=0)
        
        if st.button("Guardar Producto"):
            ejecutar_consulta("INSERT INTO productos (nombre, costo, precio, stock) VALUES (?,?,?,?)", (n, co, pr, stk))
            st.success(f"{n} agregado.")
            st.rerun()

    st.subheader("Stock Actual")
    data_p = ejecutar_consulta("SELECT id, nombre, costo, precio, stock FROM productos", fetch=True)
    df_p = pd.DataFrame(data_p, columns=["ID", "Producto", "Costo", "Venta", "Stock"])
    st.dataframe(df_p, use_container_width=True)

# --- MÓDULO CLIENTES ---
elif "Clientes" in choice:
    st.header("👥 Gestión de Clientes y Fiados")
    tab1, tab2, tab3 = st.tabs(["💰 Cobrar Deudas", "👤 Registrar Cliente", "📜 Historial"])

    with tab1:
        deudores = ejecutar_consulta("SELECT id, nombre, empresa, deuda FROM clientes WHERE deuda > 0", fetch=True)
        if deudores:
            dict_d = {f"{d[1]} ({d[2]}) - Debe: ${d[3]:,.2f}": d for d in deudores}
            sel_d = st.selectbox("Selecciona Cliente que va a pagar:", dict_d.keys())
            datos_c = dict_d[sel_d]
            
            col_p1, col_p2 = st.columns(2)
            monto_pago = col_p1.number_input("Monto del Abono:", min_value=0.0, max_value=float(datos_c[3]))
            
            if col_p1.button("Registrar Abono"):
                ejecutar_consulta("UPDATE clientes SET deuda = deuda - ? WHERE id = ?", (monto_pago, datos_c[0]))
                ejecutar_consulta("INSERT INTO abonos (cliente_id, monto) VALUES (?,?)", (datos_c[0], monto_pago))
                st.success("Pago registrado")
                st.rerun()
            
            if col_p2.button("LIQUIDAR TODA LA DEUDA ✅"):
                # Opción Pro: Pagar todo de un solo clic
                ejecutar_consulta("INSERT INTO abonos (cliente_id, monto) VALUES (?,?)", (datos_c[0], datos_c[3]))
                ejecutar_consulta("UPDATE clientes SET deuda = 0 WHERE id = ?", (datos_c[0],))
                st.success(f"Cuenta de {datos_c[1]} saldada.")
                st.balloons()
                st.rerun()
        else:
            st.info("No hay clientes con deudas pendientes. ¡Excelente!")

    with tab2:
        with st.form("nuevo_cliente"):
            nombre_c = st.text_input("Nombre Completo")
            empresa_c = st.text_input("Empresa/Referencia")
            if st.form_submit_button("Guardar Cliente"):
                ejecutar_consulta("INSERT INTO clientes (nombre, empresa, deuda) VALUES (?,?,0)", (nombre_c, empresa_c))
                st.success("Cliente guardado.")
                st.rerun()

    with tab3:
        # Historial de ventas fiadas para control
        clis_all = ejecutar_consulta("SELECT id, nombre FROM clientes", fetch=True)
        if clis_all:
            sel_h = st.selectbox("Ver compras de:", {c[1]: c[0] for c in clis_all}.keys())
            id_h = {c[1]: c[0] for c in clis_all}[sel_h]
            ventas_h = ejecutar_consulta("SELECT fecha, detalles, total FROM ventas WHERE cliente_id = ? ORDER BY fecha DESC", (id_h,), fetch=True)
            st.table(pd.DataFrame(ventas_h, columns=["Fecha", "Artículos", "Total"]))

# --- MÓDULO CAJA Y REPORTES ---
elif "Caja" in choice:
    st.header("📊 Reporte de Ventas y Ganancias")
    
    # Filtro por fecha
    fecha_busqueda = st.date_input("Selecciona un día para ver el reporte:", datetime.now())
    fecha_str = fecha_busqueda.strftime("%Y-%m-%d")
    
    # Obtener ventas del día (Contado + Fiado)
    ventas_dia = ejecutar_consulta("SELECT detalles, total, metodo_pago FROM ventas WHERE fecha LIKE ?", (f"{fecha_str}%",), fetch=True)
    
    if ventas_dia:
        total_dia = sum([v[1] for v in ventas_dia])
        st.metric("Ventas Totales del Día", f"${total_dia:,.2f}")
        
        c1, c2 = st.columns(2)
        contado = sum([v[1] for v in ventas_dia if v[2] == "Contado"])
        fiado = sum([v[1] for v in ventas_dia if v[2] == "Crédito (Fiado)"])
        
        c1.write(f"💵 **Efectivo en Caja:** ${contado:,.2f}")
        c2.write(f"📝 **Vendido en Fiado:** ${fiado:,.2f}")
        
        st.divider()
        st.subheader("Desglose de Operaciones")
        df_ventas = pd.DataFrame(ventas_dia, columns=["Detalles", "Monto", "Método"])
        st.dataframe(df_ventas, use_container_width=True)
        
        # --- SECCIÓN DE GANANCIAS (MÁGICA) ---
        # Nota: Esto es un cálculo estimado basado en tus precios actuales
        st.divider()
        st.subheader("📈 Estimación de Ganancia Neta")
        st.info("Esta sección calcula cuánto dinero es 'tuyo' después de recuperar lo invertido en mercadería.")
        
        # Para un reporte real de ganancias, necesitaríamos guardar el costo al momento de la venta, 
        # pero podemos estimarlo con una aproximación del 30% si no quieres complicar la DB, 
        # o calcularlo producto por producto.
        ganancia_estimada = total_dia * 0.25 # Asumiendo un 25% de margen promedio
        st.write(f"Tu ganancia neta aproximada hoy es de: **${ganancia_estimada:,.2f}**")
        
    else:
        st.warning(f"No hay registros para el día {fecha_str}")