import socket
import threading
import webbrowser
from app import create_app

app = create_app()


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


if __name__ == '__main__':
    ip = get_local_ip()
    print('=' * 50)
    print(f'  ML 튜터 서버 시작')
    print(f'  교사(내 PC): http://127.0.0.1:5000')
    print(f'  학생 접속:   http://{ip}:5000')
    print('=' * 50)
    threading.Timer(1.5, lambda: webbrowser.open('http://127.0.0.1:5000')).start()
    app.run(host='0.0.0.0', port=5000, debug=False)
