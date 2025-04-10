#!/usr/bin/env python

import RPi.GPIO as GPIO
import pandas as pd
import time
from datetime import datetime
from mfrc522 import SimpleMFRC522
import os
import PySimpleGUI as sg

# -------------------- CONFIGURACIÓN DE ARCHIVOS ---------------------

archivo_base = 'base_datos.csv'
archivo_activo = 'registro_activo.csv'

# Asegurarse de que los archivos existen y tengan las columnas correctas
if not os.path.exists(archivo_base):
    pd.DataFrame(columns=['ID', 'ingreso', 'salida', 'tiempo_total', 'precio']).to_csv(archivo_base, index=False)

if not os.path.exists(archivo_activo):
    pd.DataFrame(columns=['ID', 'ingreso', 'salida']).to_csv(archivo_activo, index=False)

# ---------------------- LECTURA DE ARCHIVOS --------------------------

base_datos = pd.read_csv(archivo_base)
registro_activo = pd.read_csv(archivo_activo)

# ---------------------- INICIAR RFID ---------------------------------
reader = SimpleMFRC522()

# ---------------------- INTERFAZ GRÁFICA -----------------------------
layout = [
    [sg.Text("ID del usuario:", size=(20, 1)), sg.Text("", size=(20, 1), key="ID")],
    [sg.Text("Tiempo de estacionamiento:", size=(20, 1)), sg.Text("", size=(20, 1), key="Tiempo")],
    [sg.Text("Precio a cobrar:", size=(20, 1)), sg.Text("", size=(20, 1), key="Precio")],
    [sg.Button("Salir", size=(10, 1))]
]

# Crear la ventana
window = sg.Window("Sistema de Estacionamiento", layout, finalize=True)

# ---------------------- BUCLE PRINCIPAL ------------------------------
try:
    while True:
        event, values = window.read(timeout=100)  # Se actualiza cada 100ms

        if event == sg.WINDOW_CLOSED or event == "Salir":
            break

        print("Esperando tarjeta...")
        time.sleep(1)
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
            segundos_totales = int(tiempo_total.total_seconds())

            minutos = segundos_totales // 60
            segundos = segundos_totales % 60

            # Calcular precio basado en bloques de 1500 segundos (25 minutos)
            bloques = (segundos_totales // 1500) + 1
            precio = bloques * 0.30

            print(f"Tiempo total: {minutos} minutos y {segundos} segundos.")
            print(f"Precio a cobrar: ${precio:.2f}")
            print(" ")
            
            # Agregar la columna precio
            fila['precio'] = round(precio, 2)
            fila['tiempo_total'] = tiempo_total

            # Agregar al historial completo
            base_datos = pd.concat([base_datos, fila], ignore_index=True)

            # Eliminar del registro activo
            registro_activo = registro_activo[registro_activo['ID'] != id]

            # Actualizar la interfaz gráfica
            window["ID"].update(id)
            window["Tiempo"].update(f"{minutos} min {segundos} seg")
            window["Precio"].update(f"${precio:.2f}")

        else:
            print(f"ID {id} está ingresando.")

            nueva_fila = pd.DataFrame([{
                'ID': id,
                'ingreso': ahora,
                'salida': ''
            }])

            registro_activo = pd.concat([registro_activo, nueva_fila], ignore_index=True)

            # Actualizar la interfaz gráfica con los datos de entrada
            window["ID"].update(id)
            window["Tiempo"].update("Ingreso registrado")
            window["Precio"].update("N/A")
            time.sleep(1)

        # Guardar los archivos actualizados
        base_datos.to_csv(archivo_base, index=False)
        registro_activo.to_csv(archivo_activo, index=False)

except KeyboardInterrupt:
    GPIO.cleanup()
    print("\nPrograma detenido manualmente.")

# Cerrar ventana al terminar
window.close()
