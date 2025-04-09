#!/usr/bin/env python

import webbrowser
import requests
import RPi.GPIO as GPIO
import pandas as pd
import time
from datetime import datetime
from mfrc522 import SimpleMFRC522
import os
#import PYSimplegui as sg

# -------------------- DATOS PARA PAYPHONE ---------------------
PAYPHONE_TOKEN = "v9EODbA3Yq99l19se0vV-7VYEBJzbfE3HCNQmCm8TWPFtVK0S7gGHRz3wQs4mPqb7bY2InjjTZNDKy_PpBJO4qymE1R5Nt8mfrhwmBkMF_Kus8hY18tG0QdmYC3SUO8fD1YeiYZVHJmNo3AfL_HUBPdOoSWnfbn5hpFohEa7VJUI03eXiT2ToYCH6dtw_d9e9iBis0nlrl9_5r4mHE5KK1uay-daapObVmBUu1uAL8VtDf5WXYWGIP5bQgoI5C05PoqpSKj67qCkhAfqHwerEGjikssYgKotkXDKpencN37tBMc8w9ZAokDVdKVdCHld2Sw4kQ"

# -------------------- CONFIGURACIÓN DE ARCHIVOS ---------------------

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
            precio = ((minutos // 25)+1)*0.30

            print(f"Precio a cobrar: ${precio:.2f}")
            
            
            # ----------------- PAYPHONE ----------------------------------
            headers = {
                "Authorization": f"Bearer {PAYPHONE_TOKEN}",
                "Content-Type": "application/json"
            }

            payload = {
            "amount": int(precio * 100),  # en centavos
            "amountWithoutTax": int(precio * 100),
            "tax": 0,
            "service": 0,
            "tip": 0,
            "clientTransactionId": str(id),
            "phoneNumber": "",  # Si lo tienes guardado
            "email": "",        # Opcional
            "responseUrl": "https://tu-sitio.com/respuesta",  # o tu localhost para pruebas
            "expirationMinutes": 5
            }

            try:
             response = requests.post("https://pay.payphonetodoesposible.com/api/button", headers=headers, json=payload)
             if response.status_code == 200:
                link_pago = response.json().get("paymentUrl")
                print(f"Link de pago: {link_pago}")
                webbrowser.open(link_pago)
             else:
                print("Error generando el link de pago:", response.text)

            except Exception as e:
             print("Excepción al generar link de pago:", str(e))
            
            

            # Agregar la columna precio
            fila['precio'] = precio
            fila['tiempo_total'] = tiempo_total

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
