import socket
import threading

#双线程版,主线程发送信息给服务端,子线程接收服务端信息

def receive_messages(client_socket):
    try:
        while True:
            # 接收并打印服务端的信息
            server_msg = client_socket.recv(1024).decode('utf-8').strip()
            if not server_msg:
                print('连接已断开')
                break
            #这个就是否则,不用写else:
            print(f"\n服务端:{server_msg}")
            if "再见,祝您一路顺风,欢迎下次光临." in server_msg:
                # exit(999)
                break
    except ConnectionRefusedError:
        print("无法连接到服务器,请检查服务器是否运行")
    finally:
        client_socket.close()

def handle_send(client_socket, message):
    client_socket.send(message.encode('utf-8'))
def send_messages(client_socket):
    try:
        while True:
            # 输入回复服务端的信息
            send_to_server = input()
            if send_to_server.lower() == 'exit':
                handle_send(client_socket, send_to_server)
                break
            handle_send(client_socket, send_to_server)
    except KeyboardInterrupt:
        print("\n用户中断输入")
    finally:
        client_socket.close()

def main():
    #配置服务器地址
    SERVER_ADDRESS ='192.168.219.83'
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

        #主线程发送信息
        send_messages(client_socket)
    except ConnectionRefusedError:
        print("无法连接到服务器,请检查服务端是否运行")
    except Exception as e:
        print(f"通信错误:{e}")
    finally:
        client_socket.close()

if __name__ == "__main__":
    main()
