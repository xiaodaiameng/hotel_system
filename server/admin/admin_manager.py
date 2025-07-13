import pymysql

from hotel_system.server.core.database import db_connection_handler
from hotel_system.server.core.network import handle_send


class AdminManager:
    """管理员功能封装类"""
    @staticmethod
    @db_connection_handler
    def authenticate(username, password, conn=None):
        """管理员认证"""
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT password FROM managers_table WHERE username = %s", (username,))
                result = cursor.fetchone()  # result是一个元组
                return (result is not None and result[0] == password)
        except pymysql.Error as e:
            print(f'管理员认证错误:{e}')
            return False

    @staticmethod
    @db_connection_handler
    def data_presentation(client_socket, conn=None):
        """显示所有表数据给管理员所在客户端"""
        try:
            with conn.cursor() as cursor:
                tables={'管理员表':'managers_table','用户表':'customers_table','房间表':'rooms_table'}
                for name, table in tables.items():
                    cursor.execute(f"SELECT * FROM {table}")
                    result = cursor.fetchall()
                    handle_send(client_socket, f"{name}:\n{result}\n")

                return True
        except pymysql.Error as e:
            handle_send(client_socket, f"查询表数据错误:{e}")
            return False
    @staticmethod
    def admin_menu(client_socket):
        """管理员菜单"""
        handle_send(client_socket,"请输入您要增删改查的类型:\t1.客户\t2.房间\t0.退出\t:")