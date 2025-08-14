from socket import socket, AF_INET, SOCK_STREAM
import threading  
import time  
import random  
from datetime import datetime  

SERVER = "localhost"
PORT = 12000

SIM_MIN = 10.0
SIM_MAX = 40.0



# Classe principal do cliente sensor
class SensorClient:
    def __init__(self, server: str, port: int, sensor_id: str, intervalo: float):
        self.server = server  # Endereço do servidor
        self.port = port  # Porta do servidor
        self.sensor_id = sensor_id  
        self.intervalo = intervalo 
        self.sock = socket(AF_INET, SOCK_STREAM) 
        self.reader = None  
        self.writer = None  
        self._rodando_envio = threading.Event()  
        self._rodando_envio.set()  # Inicialmente, envio está ativo
        self._vivo = True  # Controle de vida do cliente

    def conectar(self):
        """Estabelece conexão com o servidor."""
        self.sock.connect((self.server, self.port))
        self.reader = self.sock.makefile("rb")
        self.writer = self.sock.makefile("wb")

    def desconectar(self):
        """Encerra conexão com o servidor e fecha recursos."""
        try:
            self.enviar_linha("SAIR")  # Informa ao servidor que está saindo
        except Exception:
            pass
        try:
            self.reader.close()
            self.writer.close()
        except Exception:
            pass
        self.sock.close()

    def enviar_linha(self, s: str):
        """Envia uma linha de texto para o servidor."""
        self.writer.write((s + "\n").encode())
        self.writer.flush()

    def thread_envio_periodico(self):
        """Thread responsável por enviar leituras simuladas periodicamente."""
        while self._vivo:
            if self._rodando_envio.is_set():
                temp = random.uniform(SIM_MIN, SIM_MAX)  # Gera valor de temperatura
                ts = datetime.now().isoformat()  # Timestamp da leitura
                msg = f"CADASTRO;{self.sensor_id};{temp:.2f};{ts}"  # Monta mensagem
                try:
                    self.enviar_linha(msg)  # Envia ao servidor
                except Exception:
                    break
            time.sleep(self.intervalo)  # Aguarda próximo envio

    def thread_recebimento(self):
        """Thread responsável por receber e exibir mensagens do servidor."""
        while self._vivo:
            linha = self.reader.readline()
            if not linha:
                break
            print("[SERVIDOR] " + linha.decode().rstrip("\n"))

    def pausar_envio(self):
        """Pausa o envio automático de leituras."""
        self._rodando_envio.clear()

    def retomar_envio(self):
        """Retoma o envio automático de leituras."""
        self._rodando_envio.set()


def main():
    """Função principal: inicializa o cliente, menu de interação e controle das threads."""
    print("=== Cliente Sensor ===")
    sensor_id = input("Informe o ID do sensor: ").strip()
    while not sensor_id:
        sensor_id = input("ID não pode ser vazio. ").strip()

    try:
        intervalo = float(input("Informe o intervalo de envio em segundos: ").strip())
    except Exception:
        intervalo = 2.0
        print("Valor inválido.")

    client = SensorClient(SERVER, PORT, sensor_id, intervalo)
    client.conectar()

    # Inicia threads para envio periódico e recebimento de mensagens
    t_envio = threading.Thread(target=client.thread_envio_periodico, daemon=True)
    t_recv = threading.Thread(target=client.thread_recebimento, daemon=True)
    t_envio.start()
    t_recv.start()

    try:
        while True:
            print(
                "\n----- MENU -----\n"
                "1) Pausar envio automático\n"
                "2) Retomar envio automático\n"
                "3) LISTAR TERMÔMETROS (últimas leituras)\n"
                "4) GERAR RESUMO + GRÁFICO\n"
                "5) TIMESTAMP deste sensor\n"
                "6) Sair\n"
            )
            op = input("Escolha: ").strip()

            # Executa ação conforme opção do usuário
            if op == "1":
                client.pausar_envio()
                print("Envio automático PAUSADO.")
            elif op == "2":
                client.retomar_envio()
                print("Envio automático RETOMADO.")
            elif op == "3":
                client.enviar_linha("LISTAR_TERMOMETROS")
            elif op == "4":
                client.enviar_linha("GERAR_RESUMO")
            elif op == "5":
                client.enviar_linha(f"TIMESTAMP;{client.sensor_id}")
            elif op == "6":
                print("Encerrando...")
                client._vivo = False
                client.desconectar()
                break
            else:
                print("Opção inválida.")
    except KeyboardInterrupt:
        print("\nEncerrando por interrupção.")
        client._vivo = False
        client.desconectar()


if __name__ == "__main__":
    main()
