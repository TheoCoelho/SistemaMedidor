from socket import socket, AF_INET, SOCK_STREAM
import threading
import time
import random
from datetime import datetime

SERVER = "localhost"
PORT = 12000

SIM_MIN = 10.0
SIM_MAX = 40.0


class SensorClient:
    def __init__(self, server: str, port: int, sensor_id: str, intervalo: float):
        self.server = server
        self.port = port
        self.sensor_id = sensor_id
        self.intervalo = intervalo
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.reader = None
        self.writer = None
        self._rodando_envio = threading.Event()
        self._rodando_envio.set()  
        self._vivo = True

    def conectar(self):
        self.sock.connect((self.server, self.port))
        self.reader = self.sock.makefile("rb")
        self.writer = self.sock.makefile("wb")

    def desconectar(self):
        try:
            self.enviar_linha("SAIR")
        except Exception:
            pass
        try:
            self.reader.close()
            self.writer.close()
        except Exception:
            pass
        self.sock.close()

    def enviar_linha(self, s: str):
        self.writer.write((s + "\n").encode())
        self.writer.flush()

    def thread_envio_periodico(self):

        while self._vivo:
            if self._rodando_envio.is_set():
                temp = random.uniform(SIM_MIN, SIM_MAX)
                ts = datetime.now().isoformat()
                msg = f"CADASTRO;{self.sensor_id};{temp:.2f};{ts}"
                try:
                    self.enviar_linha(msg)
                except Exception:
                    break
            time.sleep(self.intervalo)

    def thread_recebimento(self):
  
        while self._vivo:
            linha = self.reader.readline()
            if not linha:
                break
            print("[SERVIDOR] " + linha.decode().rstrip("\n"))

    def pausar_envio(self):
        self._rodando_envio.clear()

    def retomar_envio(self):
        self._rodando_envio.set()


def main():
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
