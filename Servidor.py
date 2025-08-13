from socket import socket, AF_INET, SOCK_STREAM
import threading
import json
import csv
from collections import defaultdict
from datetime import datetime
import os
import matplotlib.pyplot as plt

HOST = ""
PORT = 12000

MIN_OK = 15.0
MAX_OK = 35.0

json_lock = threading.Lock()
csv_lock = threading.Lock()

CADASTROS_JSON = "cadastros.json"
DADOS_CSV = "dados.csv"
ALERTS_LOG = "alerts.log"
SUMMARY_TXT = "summary.txt"
SUMMARY_PNG = "temperature_summary.png"


last_reading = {}
last_reading_lock = threading.Lock()


def garantir_arquivos():
    if not os.path.exists(CADASTROS_JSON):
        with open(CADASTROS_JSON, "w", encoding="utf-8") as f:
            json.dump([], f, indent=4, ensure_ascii=False)

    if not os.path.exists(DADOS_CSV):
        with open(DADOS_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "temperatura", "timestamp"])  # cabeçalho

    if not os.path.exists(ALERTS_LOG):
        open(ALERTS_LOG, "a", encoding="utf-8").close()


def salvar_cadastro(id_sensor: str, temp: float, ts: str):
    # Atualiza JSON
    with json_lock:
        try:
            with open(CADASTROS_JSON, "r", encoding="utf-8") as f:
                cadastros = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            cadastros = []

        cadastros.append({"id": id_sensor, "temperatura": temp, "timestamp": ts})

        with open(CADASTROS_JSON, "w", encoding="utf-8") as f:
            json.dump(cadastros, f, indent=4, ensure_ascii=False)

    # Atualiza CSV
    with csv_lock, open(DADOS_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([id_sensor, f"{temp:.2f}", ts])

    with last_reading_lock:
        last_reading[id_sensor] = {"temperatura": temp, "timestamp": ts}


def registrar_alerta(msg: str):
    print(msg)
    with open(ALERTS_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} {msg}\n")


def generate_summary_and_graph():
    """Calcula médias por sensor"""
    try:
        with json_lock, open(CADASTROS_JSON, "r", encoding="utf-8") as f:
            cadastros = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        cadastros = []

    if not cadastros:
        with open(SUMMARY_TXT, "w", encoding="utf-8") as f:
            f.write("Sem dados para resumo.\n")
        # Garante que arquivo antigo de gráfico não confunda
        if os.path.exists(SUMMARY_PNG):
            os.remove(SUMMARY_PNG)
        return "Sem dados para gerar resumo."

    sensor_data = defaultdict(list)
    for c in cadastros:
        try:
            sensor_data[c["id"]].append(float(c["temperatura"]))
        except Exception:
            pass

    averages = {sid: (sum(vals) / len(vals)) for sid, vals in sensor_data.items() if vals}

    with open(SUMMARY_TXT, "w", encoding="utf-8") as f:
        f.write("Média de temperatura por sensor:\n")
        for sid, media in sorted(averages.items()):
            linha = f"Sensor {sid}: {media:.2f} °C"
            print(linha)
            f.write(linha + "\n")

    try:
        plt.figure()
        plt.bar(list(averages.keys()), list(averages.values()))
        plt.xlabel("Sensor ID")
        plt.ylabel("Temperatura média (°C)")
        plt.title("Temperatura média por sensor")
        plt.tight_layout()
        plt.savefig(SUMMARY_PNG)
        plt.close()
    except Exception as e:
        print(f"Falha ao gerar gráfico: {e}")

    return f"Resumo gerado. Arquivos: {SUMMARY_TXT} e {SUMMARY_PNG}"


def processar_linha(cmd: str, writer) -> None:

    if not cmd:
        return

    if cmd.startswith("CADASTRO;"):
        try:
            _, id_sensor, temp_str, ts = cmd.split(";", 3)
            temp_val = float(temp_str)
        except Exception:
            resposta = "ERRO: Formato inválido. Use CADASTRO;id;temperatura;timestampISO"
            writer.write((resposta + "\n").encode())
            writer.flush()
            return

        salvar_cadastro(id_sensor, temp_val, ts)

        if temp_val < MIN_OK or temp_val > MAX_OK:
            alerta = f"ALERTA: Sensor {id_sensor} fora do intervalo ({temp_val:.2f} °C)"
            registrar_alerta(alerta)
            writer.write((alerta + "\n").encode())
        else:
            writer.write(("OK: Cadastro recebido.\n").encode())
        writer.flush()
        return

    if cmd == "LISTAR_TERMOMETROS":
        with last_reading_lock:
            if not last_reading:
                writer.write(("Nenhum termômetro cadastrado.\n").encode())
                writer.flush()
                return
            linhas = []
            for sid, info in sorted(last_reading.items()):
                linhas.append(f"ID: {sid}, Temp: {info['temperatura']:.2f} °C, TS: {info['timestamp']}")
            writer.write(("\n".join(linhas) + "\n").encode())
            writer.flush()
        return

    if cmd == "GERAR_RESUMO":
        msg = generate_summary_and_graph()
        writer.write((msg + "\n").encode())
        writer.flush()
        return

    if cmd.startswith("TIMESTAMP;"):
        _, sid = cmd.split(";", 1)
        with last_reading_lock:
            if sid in last_reading:
                ts = last_reading[sid]["timestamp"]
                writer.write((f"Último timestamp de {sid}: {ts}\n").encode())
            else:
                writer.write((f"Sem leituras para {sid}\n").encode())
            writer.flush()
        return

    if cmd == "SAIR":
        writer.write(("Encerrando conexão.\n").encode())
        writer.flush()
        return

    writer.write(("Comando não reconhecido.\n").encode())
    writer.flush()


def atender_cliente(conn, addr):
   
    print(f"Cliente conectado: {addr}")
    with conn:
        reader = conn.makefile("rb")
        writer = conn.makefile("wb")
        while True:
            linha = reader.readline()
            if not linha:
                break  # cliente fechou
            cmd = linha.decode().rstrip("\n")
            if cmd == "SAIR":
                processar_linha(cmd, writer)
                break
            processar_linha(cmd, writer)
    print(f"Cliente desconectado: {addr}")


def main():
    garantir_arquivos()
    with socket(AF_INET, SOCK_STREAM) as srv:
        srv.setsockopt(1, 2, 1)  # SO_REUSEADDR
        srv.bind((HOST, PORT))
        srv.listen()
        print(f" pronto para receber sensores.")

        while True:
            conn, addr = srv.accept()
            t = threading.Thread(target=atender_cliente, args=(conn, addr), daemon=True)
            t.start()


if __name__ == "__main__":
    main()
