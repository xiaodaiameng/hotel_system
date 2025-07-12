import socket
import threading

def receive_messages(client_socket):
    try:
        while True:
            try:
                server_msg = client_socket.recv(1024).decode('utf-8').strip()
                print(server_msg)
            except (ConnectionResetError,OSError) as e:
                print(f"连接断开:{e}")
                return False
    finally:
        client_socket.close()
def handle_send(client_socket, message):
    client_socket.send(message.encode('utf-8'))
def send_messages(client_socket):
    try:
        while True:
            try:
                send_to_server = input()
                handle_send(client_socket, send_to_server)
                if send_to_server.lower() == '0' or send_to_server.lower() == 'exit':
                    print("再见，祝您一路顺风。")
                    client_socket.shutdown(socket.SHUT_WR)
                    break
            except Exception as e:
                print(f"输入错误:{e}")
    finally:
        client_socket.close()

def main():
    #配置服务器地址
    SERVER_ADDRESS ='localhost'
    SERVER_PORT = 8001
    #创建会话对象(创建套接字)(局部变量)
    client_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    #建立连接
    try:
        client_socket.connect((SERVER_ADDRESS,SERVER_PORT))
        print('####连接成功.')
        #启动接收消息的线程
        recv_thread = threading.Thread(target = receive_messages, args = (client_socket,))
        #设置守护:主线程若关闭,子线程均须关闭
        recv_thread.daemon = True
        #开启
        recv_thread.start()
        send_messages(client_socket)
    except ConnectionRefusedError:
        print("无法连接到服务器,请检查服务端是否运行")
    except Exception as e:
        print(f"通信错误:{e}")
    finally:
        client_socket.close()

if __name__ == "__main__":
    main()

