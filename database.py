import sqlite3

def crear_tablas():
    conn = sqlite3.connect('negocio.db')
    cursor = conn.cursor()
    
    # Tabla de Productos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            costo REAL NOT NULL,
            precio REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    ''')

    # Tabla de Clientes (para los fiados)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            empresa TEXT,
            deuda REAL DEFAULT 0
        )
    ''')

    # Tabla de Ventas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cliente_id INTEGER,
            total REAL NOT NULL,
            metodo_pago TEXT, 
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    ''')

    # Tabla de Gastos diarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            descripcion TEXT,
            monto REAL NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    crear_tablas()
    print("¡Base de datos y tablas creadas con éxito!")