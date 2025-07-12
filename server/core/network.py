
#要知道是引入了socket才能使用的函数！

def handle_receive(client_socket):
    """接收客户端传来的操作数"""
    try:
        data = client_socket.recv(1024)
        decoded = data.decode('utf-8').strip()
        if decoded == '0':
            return None
        return decoded if decoded else None
    except (ConnectionResetError, OSError) as e:
        print(f"连接错误: {e}")
        return False
    except UnicodeDecodeError as e:
        print(f"编码错误: {e}")
        return False

def handle_send(client_socket, what_you_want_to_send):
    """发送信息给客户端的函数"""
    try:
        if isinstance(what_you_want_to_send,(list, tuple, dict)):#检查类型是否正确
            what_you_want_to_send = str(what_you_want_to_send)
        client_socket.send(what_you_want_to_send.encode('utf-8'))
    except (ConnectionResetError, OSError) as e:
        print(f"发送数据错误:{e}")
        return False
    return True

def close_connection(client_socket):
    """关闭连接"""
    client_socket.close()
