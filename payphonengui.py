#!/usr/bin/env python

import webbrowser
import requests
import RPi.GPIO as GPIO
import pandas as pd
import time
from datetime import datetime
from mfrc522 import SimpleMFRC522
import os
import PySimpleGUI as sg

# -------------------- DATOS PARA PAYPHONE ---------------------
PAYPHONE_TOKEN = "WIqw9NblfUOZ92_WpuHzRLy0lvVVU7XdZY0Q7wieeE5muupcMX7us-qn7u3M2toEGfIch83Q8n179l33upNBhsXDntb1hQCzBL02BNYFyyNtd4J1WXC162M5ir47vNGs1CDP7DOJFwwAolOTTzMc236QHBZ6-bFWWfeZCHxamfxXiE_0NPJZwp4zvUhjaJIXebCx5HvitKZtmFX16kWxSBoZe05-R6PnD__aTLb2XU2gOLfz5Hs0UWLn0ooMuISVZxBOk8v0x3OmUgautY_ta-utTG3N22An4X5sav68bRwSS6doQv3rA2KG_vPyIZTdbsVWFg"

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
            precio = ((segundos_totales // 1500) + 1) * 0.30

            print(f"Tiempo total: {minutos} minutos y {segundos} segundos.")
            print(f"Precio a cobrar: ${precio:.2f}")
            print(" ")
            
            # ----------------- PAYPHONE ----------------------------------
            headers = {
                "Authorization": f"Bearer {PAYPHONE_TOKEN}",
                "Content-Type": "application/json"
            }

            payload = {
            "phoneNumber": "0983392763",
            "countryCode": "593",
            "amount": int(precio * 100),
            "amountWithoutTax": int(precio * 100),
            "currency": "USD",
            "clientTransactionId": str(id),
            "storeId": "7cf25dcf-b2a1-478d-b2ab-181be82593c6",
            "email": "tyminobra@outlook.es",        # Opcional
            "expirationMinutes": 5,
            }

            try:
             response = requests.post("https://pay.payphonetodoesposible.com/api/Sale", headers=headers, json=payload)
             if response.status_code == 200:
                link_pago = response.json().get("paymentUrl")
                print(f"Link de pago: {link_pago}")
                webbrowser.open(link_pago)
             else:
                print("Error generando el link de pago:", response.text)

            except Exception as e:
             print("Excepción al generar link de pago:", str(e))            
            
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
            window["Precio"].update(" ")

        # Guardar los archivos actualizados
        base_datos.to_csv(archivo_base, index=False)
        registro_activo.to_csv(archivo_activo, index=False)

except KeyboardInterrupt:
    GPIO.cleanup()
    print("\nPrograma detenido manualmente.")

# Cerrar ventana al terminar
window.close()
