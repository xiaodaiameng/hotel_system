import re
import pymysql

from hotel_system.server.core.database import db_connection_handler
from hotel_system.server.core.network import handle_send, handle_receive, close_connection


def handle_customer_management(client_socket):
    """管理员对客户的管理"""
    while True:
        menu = """
        客户管理:
        1. 修改客户名称
        2. 修改客户余额
        3. 删除客户
        0. 退出
        请输入选择: """
        handle_send(client_socket, menu)
        choice = handle_receive(client_socket)
        if choice == '0':
            close_connection(client_socket)
            break
        if choice == '1':  # 修改客户名称
            CustomerManager.modify_name(client_socket)
        elif choice == '2':  # 修改客户余额
            handle_send(client_socket, "请输入客户名称:")
            name = handle_receive(client_socket)
            handle_send(client_socket, "请输入新的余额(0是退出):")
            amount = handle_receive(client_socket)
            if name and amount and re.match(r'^\d+(\.\d{1,2})?$', amount):
                CustomerManager.modify_balance(client_socket, name, float(amount))
            else:
                handle_send(client_socket, "输入无效")
        elif choice == '3':  # 删除客户
            CustomerManager.delete_customer(client_socket)
        else:
            handle_send(client_socket, "无效的选择.请重新输入:")

class CustomerManager:
    """客户管理功能"""
    @staticmethod
    @db_connection_handler
    def modify_name(client_socket,conn=None):
        try:
            with conn.cursor() as cursor:
                handle_send(client_socket,'请输入您的旧账号名称:')
                old_name = handle_receive(client_socket)
                if old_name == '0':
                    close_connection(client_socket)
                cursor.execute("SELECT name FROM customers_table WHERE name = %s and is_deleted = 0", (old_name,))
                if cursor.fetchone():
                    handle_send(client_socket, "请输入新名称:")
                    new_name = handle_receive(client_socket)
                    cursor.execute("UPDATE customers_table SET name = %s WHERE name = %s", (new_name, old_name))
                    conn.commit()  # 提交更改
                    handle_send(client_socket, f'修改成功,当前账号名称:{new_name}.')
                    return True
                else:
                    handle_send(client_socket,'抱歉.该名称不存在或已标记为删除.')
                    return None
        except pymysql.Error as e:
            conn.rollback()
            handle_send(client_socket,f'修改账号错误:{e}')
            return False
    @staticmethod
    @db_connection_handler
    def modify_balance(client_socket, name,amount,conn=None):
        try:
            if not re.match(r'^\d+(\.\d{1,2})?$', str(amount)):
                handle_send(client_socket,"金额格式无效（示例：100.50）,请重新选择您要修改的这位客户的内容(1修改账号，2修改余额，3注销):")
            amount = float(amount)
            with conn.cursor() as cursor:
                cursor.execute("UPDATE customers_table SET balance = %s WHERE name = %s and is_deleted = 0",(amount, name))
                cursor.execute("SELECT balance FROM customers_table WHERE name = %s",(name,))
                new_balance = cursor.fetchone()[0]
                conn.commit()
                handle_send(client_socket, f'修改成功。当前余额：{new_balance}元.请继续.')
                return True
        except (ValueError,pymysql.Error) as e:
            conn.rollback()
            handle_send(client_socket, f"修改余额错误: {e}")
            return False
    @staticmethod
    @db_connection_handler
    def delete_customer(client_socket,**kwargs):#软删除
        conn = kwargs.get('conn')
        try:
            with conn.cursor() as cursor:
                handle_send(client_socket, '请输入要注销的账号名称:')
                name = handle_receive(client_socket)
                cursor.execute("SELECT name FROM customers_table WHERE name = %s ", (name,))
                if cursor.fetchone():
                    cursor.execute("UPDATE customers_table SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP WHERE name = %s", (name,))
                    conn.commit()  # 提交更改
                    handle_send(client_socket, f'客户已标记为删除.')
                    return True
                else:
                    handle_send(client_socket, '抱歉.该名称不存在.')
                    return True
        except pymysql.Error as e:
            conn.rollback()
            handle_send(client_socket, f'注销账号错误:{e}')
            return False