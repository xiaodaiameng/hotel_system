import socket
import threading

import basicFunction
import buttons

def main():
    """程序入口"""
    # 初始化数据库
    if not basicFunction.init_database():
        print("数据库初始化失败，程序退出")
        return
    # 创建会话对象
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # 建立连接
        SERVER_ADDRESS = '0.0.0.0'
        server.bind((SERVER_ADDRESS, 8001))
        # 设置监听
        server.listen(5)
        print('####程序启动.等待客户端连接')
        while True:
            client_socket, addr = server.accept()
            print(f'新客户端连接:{addr}')
            # 创建新线程处理客户端
            client_thread = threading.Thread(target=buttons.handle_client, args=(client_socket,))
            # 设置为守护线程
            client_thread.daemon = True
            # 开启多线程
            client_thread.start()
            # 显示欢迎菜单
            welcome = """
            **************************\n欢迎来到酒店管理系统
            1. 客户登录
            2. 客户注册
            9. 管理员登录
            0. 退出\n**************************\n请输入选择: """
            basicFunction.handle_send(client_socket, welcome)
    except KeyboardInterrupt:
        print("\n服务器正在关闭...")
    except Exception as e:
        print(f"服务器错误: {e}")
    finally:
        server.close()
        print("服务器关闭")

if __name__ == "__main__":
    main()
