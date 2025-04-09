#!/usr/bin/env python

import RPi.GPIO as GPIO
import pandas as pd
import time
from datetime import datetime
from mfrc522 import SimpleMFRC522
import os

# --------------------- CONFIGURACIÓN DE ARCHIVOS ---------------------

archivo_base = 'base_datos.csv'
archivo_activo = 'registro_activo.csv'

# Asegurarse de que los archivos existen y tengan las columnas correctas
if not os.path.exists(archivo_base):
    pd.DataFrame(columns=['ID', 'ingreso', 'salida', 'precio']).to_csv(archivo_base, index=False)

if not os.path.exists(archivo_activo):
    pd.DataFrame(columns=['ID', 'ingreso', 'salida']).to_csv(archivo_activo, index=False)

# ---------------------- LECTURA DE ARCHIVOS --------------------------

base_datos = pd.read_csv(archivo_base)
registro_activo = pd.read_csv(archivo_activo)

# ---------------------- INICIAR RFID ---------------------------------
reader = SimpleMFRC522()

# ---------------------- BUCLE PRINCIPAL ------------------------------
try:
    while True:
        print("Esperando tarjeta...")
        id, text = reader.read()
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Verificar si el ID ya está en el registro activo (es salida)
        if id in registro_activo['ID'].values:
            print(f"ID {id} está saliendo.")

            # Obtener fila del ID
            fila = registro_activo.loc[registro_activo['ID'] == id].copy()
            fila['salida'] = ahora

            # Calcular tiempo en el parqueadero
            hora_ingreso_str = fila.iloc[0]['ingreso']
            hora_ingreso = datetime.strptime(hora_ingreso_str, "%Y-%m-%d %H:%M:%S")
            hora_salida = datetime.strptime(ahora, "%Y-%m-%d %H:%M:%S")

            tiempo_total = hora_salida - hora_ingreso
            minutos = int(tiempo_total.total_seconds() // 60)
            segundos = int(tiempo_total.total_seconds() % 60)

            print(f"Tiempo total: {minutos} minutos y {segundos} segundos.")

            # Calcular precio
            if minutos >= 25:
                precio = ((minutos // 25) + 1) * 0.30
            else:
                precio = 0.25

            print(f"Precio a cobrar: ${precio:.2f}")

            # Agregar la columna precio
            fila['precio'] = precio

            # Agregar al historial completo
            base_datos = pd.concat([base_datos, fila], ignore_index=True)

            # Eliminar del registro activo
            registro_activo = registro_activo[registro_activo['ID'] != id]

        else:
            print(f"ID {id} está ingresando.")

            nueva_fila = pd.DataFrame([{
                'ID': id,
                'ingreso': ahora,
                'salida': ''
            }])

            registro_activo = pd.concat([registro_activo, nueva_fila], ignore_index=True)

        # Guardar los archivos actualizados
        base_datos.to_csv(archivo_base, index=False)
        registro_activo.to_csv(archivo_activo, index=False)

        print("\n--- Estado actual del parqueo ---")
        print(registro_activo)
        print("---------------------------------\n")

        time.sleep(1)

except KeyboardInterrupt:
    GPIO.cleanup()
    print("\nPrograma detenido manualmente.")