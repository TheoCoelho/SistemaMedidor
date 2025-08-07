from socket import *
serverName = 'localhost'
serverPort = 12000
clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect((serverName,serverPort))

while True:
    menu = input("-----MENU----- \n" \
    "1: CADASTRO \n" \
    "2: LISTAR TERMÔMETROS\n" \
    "3: TIMESTAMP\n" \
    "4: TEMPERATURA MEDIA" \
    "5: SAIR\n")

    if menu == "1":
        id = input("ID:")
        temp = input("Temperatura atual:")
        timestemp = input("Tempo de releitura:")
        data = f"CADASTRO;{id};{temp};{timestemp}"
        clientSocket.send(data.encode())
        response = clientSocket.recv(1024)
        print('Resposta do servidor:', response.decode())

    elif menu == "2":
        clientSocket.send("LISTAR_TERMOMETROS".encode())
        response = clientSocket.recv(1024)
        print("Lista de termômetros:", response.decode())

    elif menu == "3":
        clientSocket.send("TIMESTAMP".encode())
        response = clientSocket.recv(1024)
        print("Timestamp recebido do servidor:", response.decode())
    elif menu == "4":
        clientSocket.send
        

    elif menu == "5":
        print("Saindo do programa...")
        clientSocket.close()
        break

    else:
        print("Opção inválida")



