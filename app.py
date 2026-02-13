import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- FUNCIONES DE BASE DE DATOS ---
def ejecutar_consulta(query, params=(), fetch=False):
    conn = sqlite3.connect('negocio.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    data = None
    if fetch:
        data = cursor.fetchall()
    conn.commit()
    conn.close()
    return data

# ejemplo de cambio

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Comidería Pro", layout="wide")
st.title("🏪 Sistema de Gestión - Comidería")

menu = ["Vender", "Inventario", "Clientes (Fiados)", "Caja y Gastos"]
choice = st.sidebar.selectbox("Menú Principal", menu)

# --- SECCIÓN VENDER ---
if choice == "Vender":
    st.header("🛒 Registrar Venta")
    productos_db = ejecutar_consulta("SELECT id, nombre, precio, stock FROM productos WHERE stock > 0", fetch=True)
    
    if not productos_db:
        st.warning("No hay productos en inventario.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            opciones_prod = {f"{p[1]} (Stock: {p[3]})": p for p in productos_db}
            seleccion = st.selectbox("Selecciona Producto", opciones_prod.keys())
            prod_id, precio_unitario, stock_actual = opciones_prod[seleccion][0], opciones_prod[seleccion][2], opciones_prod[seleccion][3]
            cantidad = st.number_input("Cantidad", min_value=1, max_value=stock_actual, value=1)
            total_venta = precio_unitario * cantidad
            st.subheader(f"Total: ${total_venta}")

        with col2:
            metodo = st.radio("Método de Pago", ["Contado", "Crédito (Fiado)"])
            cliente_id = None
            if metodo == "Crédito (Fiado)":
                clientes_db = ejecutar_consulta("SELECT id, nombre, empresa FROM clientes", fetch=True)
                if not clientes_db: st.error("Registra clientes primero.")
                else:
                    opciones_cli = {f"{c[1]} ({c[2]})": c[0] for c in clientes_db}
                    cliente_id = opciones_cli[st.selectbox("Selecciona Cliente", opciones_cli.keys())]

        if st.button("Finalizar Venta"):
            ejecutar_consulta("INSERT INTO ventas (cliente_id, total, metodo_pago) VALUES (?, ?, ?)", (cliente_id, total_venta, metodo))
            ejecutar_consulta("UPDATE productos SET stock = stock - ? WHERE id = ?", (cantidad, prod_id))
            if metodo == "Crédito (Fiado)":
                ejecutar_consulta("UPDATE clientes SET deuda = deuda + ? WHERE id = ?", (total_venta, cliente_id))
            st.success("✅ Venta Guardada")
            st.balloons()

# --- SECCIÓN INVENTARIO ---
elif choice == "Inventario":
    st.header("📦 Inventario")
    with st.expander("➕ Agregar Producto"):
        n = st.text_input("Nombre")
        c = st.number_input("Costo", min_value=0.0)
        p = st.number_input("Precio", min_value=0.0)
        s = st.number_input("Stock", min_value=0)
        if st.button("Guardar"):
            ejecutar_consulta("INSERT INTO productos (nombre, costo, precio, stock) VALUES (?,?,?,?)", (n,c,p,s))
    
    prod = ejecutar_consulta("SELECT id, nombre, costo, precio, stock FROM productos", fetch=True)
    st.dataframe(pd.DataFrame(prod, columns=["ID", "Nombre", "Costo", "Precio", "Stock"]), use_container_width=True)

# --- SECCIÓN CLIENTES ---
elif choice == "Clientes (Fiados)":
    st.header("👥 Cuentas por Cobrar")
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.subheader("Nuevo Cliente")
        nc, ec = st.text_input("Nombre"), st.text_input("Empresa")
        if st.button("Registrar"):
            ejecutar_consulta("INSERT INTO clientes (nombre, empresa) VALUES (?,?)", (nc, ec))
    with col_b:
        cli = ejecutar_consulta("SELECT nombre, empresa, deuda FROM clientes", fetch=True)
        st.table(pd.DataFrame(cli, columns=["Nombre", "Empresa", "Deuda ($)"]))

# --- SECCIÓN CAJA Y GASTOS ---
elif choice == "Caja y Gastos":
    st.header("💰 Cuadre de Caja y Ganancias")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Registrar Gasto del Día")
        desc = st.text_input("Descripción del gasto (ej. Hielo, Gas)")
        monto_g = st.number_input("Monto $", min_value=0.0)
        if st.button("Guardar Gasto"):
            ejecutar_consulta("INSERT INTO gastos (descripcion, monto) VALUES (?, ?)", (desc, monto_g))
            st.warning("Gasto registrado")

    # Cálculos Financieros
    ventas_hoy = ejecutar_consulta("SELECT total, metodo_pago FROM ventas WHERE DATE(fecha) = DATE('now')", fetch=True)
    gastos_hoy = ejecutar_consulta("SELECT SUM(monto) FROM gastos WHERE DATE(fecha) = DATE('now')", fetch=True)[0][0] or 0
    
    df_v = pd.DataFrame(ventas_hoy, columns=["Total", "Método"])
    efectivo = df_v[df_v["Método"] == "Contado"]["Total"].sum()
    fiado = df_v[df_v["Método"] == "Crédito (Fiado)"]["Total"].sum()
    
    with col2:
        st.subheader("Resumen de Hoy")
        st.metric("Efectivo en Caja", f"${efectivo - gastos_hoy}")
        st.metric("Vendido en Fiados", f"${fiado}")
        st.metric("Gastos Totales", f"${gastos_hoy}")
        
    st.divider()
    st.subheader("Historial de Gastos")
    hist_g = ejecutar_consulta("SELECT fecha, descripcion, monto FROM gastos ORDER BY fecha DESC", fetch=True)
    st.dataframe(pd.DataFrame(hist_g, columns=["Fecha", "Descripción", "Monto"]), use_container_width=True)