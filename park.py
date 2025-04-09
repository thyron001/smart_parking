#!/usr/bin/env python

import RPi.GPIO as GPIO
import pandas as pd
import time
import keyboard
from mfrc522 import SimpleMFRC522

#csv
data = pd.read_csv('data.csv') #Se lee el archivo csv

#Leer ID

reader = SimpleMFRC522() #Se lee el RFID
try:
	while True:
		id, text = reader.read()
		clk = time.time() #Captura el tiempo cuando se pasa la tarjeta por el RFID
				  #El valor que devuelve son los segundos que pasaron desde el 1 de enero de 1970
                if id in data.loc['ID']: #Si el ID de la tarjeta ya esta en la columna 'ID' del archivo data.csv
                        salida = clk    #Entonces, el tiempo capturado resulta ser cuando sale del parqueadero. Este valor se guarda en la variable 'salida'

                else:               #Si el ID no estaba en la columna, entonces el tiempo capturado resulta ser cuando ingresa
                        ingreso = clk   #Este valor se guarda en la variable 'ingreso'

                #Diccionario para ordenar las variables con sus respectivas columnas
                new_row = {
			"ID": id, #La ID se guarda en la columna 'ID'
			"ingreso": ingreso, #La variable 'ingreso' pertenece a la columna 'Ingreso' donde va el tiempo cuando entra al parqueadero.
			"salida": salida    #La variable 'salida' pertenece a la colummna 'Salida' donde va el tiempo cuando sale del parqueadero.
		}

		#Guardar ID
                data.loc[len(data)] = new_row       #Con 'len(data)' se situa despues de la ultima fila para guardar ahi el diccionario.
                data.to_csv('data.csv',index=False) #Se sobreescribe el archivo 'data.csv' con la nueva ultima fila

                #Imprimir
                print(data)

                time.sleep(1)

except KeyboardInterrupt: #Cuando se realiza una interrupcion de teclado (como Ctrl+C) se sale del bucle, y por ende, se termina el program
	GPIO.cleanup()
