from socket import *
import json
import matplotlib.pyplot as plt
from collections import defaultdict

serverPort = 12000
serverSocket = socket(AF_INET,SOCK_STREAM)
serverSocket.bind(('',serverPort))
serverSocket.listen(1)
print('O servidor esta pronto esperando mensagens')



def media():


# Function to calculate average temperature and generate a graph
def generate_summary_and_graph():
    try:
        with open("cadastros.json", "r") as file:
            cadastros = json.load(file)

        # Calculate average temperature per sensor
        sensor_data = defaultdict(list)
        for cadastro in cadastros:
            sensor_data[cadastro["id"]].append(float(cadastro["temperatura"]))

        averages = {sensor: sum(temps) / len(temps) for sensor, temps in sensor_data.items()}

        # Log averages to a file
        with open("summary.txt", "w") as summary_file:
            for sensor, avg_temp in averages.items():
                summary_file.write(f"Sensor ID: {sensor}, Average Temperature: {avg_temp:.2f}\n")

        # Generate a graph
        plt.bar(averages.keys(), averages.values(), color='blue')
        plt.xlabel('Sensor ID')
        plt.ylabel('Average Temperature (°C)')
        plt.title('Average Temperature per Sensor')
        plt.savefig('temperature_summary.png')
        plt.close()

    except (FileNotFoundError, json.JSONDecodeError):
        print("No data available to generate summary and graph.")

# Updated server logic
while True:
    connectionSocket, addr = serverSocket.accept()
    try:
        while True:
            try:
                data = connectionSocket.recv(1024).decode()

                if data.startswith("CADASTRO"):
                    _, id, temp, timestemp = data.split(";")
                    cadastro = {
                        "id": id,
                        "temperatura": temp,
                        "timestemp": timestemp
                    }

                    try:
                        with open("cadastros.json", "r") as file:
                            cadastros = json.load(file)
                    except (FileNotFoundError, json.JSONDecodeError):
                        cadastros = []

                    cadastros.append(cadastro)

                    with open("cadastros.json", "w") as file:
                        json.dump(cadastros, file, indent=4)

    
                    # Check temperature range and send alert if necessary
                    temp_value = float(temp)
                    if temp_value < -40 or temp_value > 35:
                        alert_message = f"ALERT: Sensor {id} reported out-of-range temperature: {temp}°C"
                        connectionSocket.send(alert_message.encode())

                        # Log alert to a file
                        with open("alerts.log", "a") as alert_file:
                            alert_file.write(alert_message + "\n")
                    else:
                        connectionSocket.send("Cadastro recebido com sucesso!".encode())

                elif data == "LISTAR_TERMOMETROS":
                    try:
                        with open("cadastros.json", "r") as file:
                            termometros = json.load(file)
                            response = "\n".join([f"ID: {t['id']}, Temperatura: {t['temperatura']}" for t in termometros])
                    except (FileNotFoundError, json.JSONDecodeError):
                        response = "Nenhum termômetro cadastrado."

                    connectionSocket.send(response.encode())

                elif data == "GERAR_RESUMO":
                    generate_summary_and_graph()
                    connectionSocket.send("Resumo e gráfico gerados com sucesso!".encode())

                else:
                    connectionSocket.send("Comando não reconhecido.".encode())
            except Exception as e:
                print(f"Erro ao processar a solicitação: {e}")
                break

    finally:
        connectionSocket.close()
