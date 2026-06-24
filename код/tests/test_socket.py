import socket

IP = "192.168.0.110"

try:

    sock = socket.socket()

    sock.settimeout(10)

    print("Подключение...")

    sock.connect((IP, 80))

    print("Соединение установлено")

    request = (
        "GET / HTTP/1.1\r\n"
        f"Host: {IP}\r\n"
        "\r\n"
    )

    sock.send(
        request.encode()
    )

    data = sock.recv(4096)

    print("Получено:")
    print(data[:500])

    sock.close()

except Exception as e:

    print("Ошибка:")
    print(type(e).__name__)
    print(e)