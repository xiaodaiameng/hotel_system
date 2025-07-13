import re
import time
import socket
import pymysql

from hotel_system.server.admin.admin_manager import AdminManager
from hotel_system.server.core.database import db_connection_handler
from hotel_system.server.core.network import handle_send, handle_receive, close_connection
from hotel_system.server.customer.customer_manager import handle_customer_management
from hotel_system.server.room.room_manager import handle_room_management


@db_connection_handler
def auto_checkout(name,conn=None):  # 过期但未退房的房间，程序自动退房！！
    try:
        with conn.cursor() as cursor:
            cursor.execute("""SELECT room_number, check_in_time, duration_days
                              FROM rooms_table
                              WHERE customer_name = %s
                                AND status = 'occupied'
                                AND DATE_ADD(check_in_time, INTERVAL duration_days DAY) < NOW()""",
                           (name,))  # （入住时间 ＋ 间隔n天）

            expired_bookings = cursor.fetchall()
            if expired_bookings:
                for room, check_in_time, days in expired_bookings:
                    cursor.execute("UPDATE rooms_table "
                                   "SET status = 'vacant',"
                                   " customer_name = NULL,"
                                   "check_in_time = NULL,"
                                   "duration_days = NULL"
                                   "  WHERE room_number = %s", (room,))
                    conn.commit()
                    return [room[0] for room in expired_bookings]
        return []
    except pymysql.Error as e:
        conn.rollback()
        print(f'自动退房出错：{e}')
        return False

def handle_client(client_socket):
    try:
        while True:
            #避免暴力破解?  if nessary then attempts = 3 ...
            choice = handle_receive(client_socket)
            if choice is None:                              # 客户端断开
                    break
            if not choice or choice is False:
                break
            choice = choice.strip()
            if choice == '1':
                CustomerService.login(client_socket)
                break
            elif choice == '2':
                CustomerService.register(client_socket)
                break
            elif choice == '9':
                handle_admin_operations(client_socket)
                break
            elif choice == '0' or choice == "exit":
                close_connection(client_socket)
                break
            else:
                handle_send(client_socket, "无效选择，请重新输入")
    except Exception as e:
        print(f"handle_client: {e}")
    except ConnectionResetError:
        print("客户端强制断开")
    finally:
        try:
            client_socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass                                                         #?
        time.sleep(1)
        client_socket.close()
        print(f"服务端已断开客户端的连接")


def handle_admin_operations(client_socket):
    """处理管理员的各种操作"""
    # 管理员认证
    handle_send(client_socket, "管理员登录\n请输入管理员名称:")
    username = handle_receive(client_socket)
    handle_send(client_socket, "请输入密码:")
    password = handle_receive(client_socket)
    if not AdminManager.authenticate(username, password):
        handle_send(client_socket,'''****************************\n认证失败。
        1. 客户登录
        2. 客户注册
        9. 管理员登录
        0. 退出\n****************************\n请重新选择:''')
        handle_client(client_socket)
    handle_send(client_socket, "管理员登录成功")
    AdminManager.data_presentation(client_socket)
    menu = """
    管理员菜单:
    1. 客户管理
    2. 房间管理
    0. 退出
    请输入选择: """
    handle_send(client_socket, menu)
    choice = handle_receive(client_socket)
    while True:
        if choice == '1':
            if not handle_customer_management(client_socket):
                break
        elif choice == '2':
            if not handle_room_management(client_socket):
                break
        elif choice == '0':
            close_connection(client_socket)
            return True
        else:
            handle_send(client_socket, "无效的选择，请重新输入")


def handle_body_choice(choice,client_socket,name):
    if choice == '1':
        CustomerService.get_vacant_rooms(client_socket)
        return True
    elif choice == '2':
        CustomerService.book_room(client_socket, name)
        return True
    elif choice == '3':
        CustomerService.checkout_room(client_socket,name)
        return True
    elif choice == '4':
        CustomerService.recharge(client_socket, name,conn=None)
        return True
    elif choice == '5':
        CustomerService.check_balance(client_socket,name)
        return True
    elif choice == '0' or choice == "exit":
        close_connection(client_socket)
        return True
    else:
        handle_send(client_socket,"无效的body_choice,请重新输入.")
        return True

class CustomerService:
    @staticmethod
    @db_connection_handler
    def login(client_socket,**kwargs):
        conn = kwargs.get('conn')
        handle_send(client_socket, "输入账号完成登录:")
        name = handle_receive(client_socket)
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT name FROM customers_table WHERE name = %s and is_deleted = 0", (name,))
                if cursor.fetchone():
                    welcome_msg = f"登录成功\n客户:{name}\n"
                    expired_rooms = auto_checkout(name)
                    if expired_rooms:
                        handle_send(client_socket, f"以下房间已自动退房: {', '.join(expired_rooms)}")
                    cursor.execute("""
                                   SELECT room_number,
                                          TIMESTAMPDIFF(HOUR, check_in_time, NOW()) as hours_elapsed,
                                          duration_days
                                   FROM rooms_table
                                   WHERE customer_name = %s
                                     AND status = 'occupied'
                                   """, (name,))
                    bookings = cursor.fetchall()
                    if bookings:
                        for room, hours, days in bookings:
                            remaining = (days * 24) - hours
                            welcome_msg += f"\n您订的房间 {room}: 已入住 {hours // 24}天{hours % 24}小时"
                            welcome_msg += f"\n剩余时间: {remaining // 24}天{remaining % 24}小时"
                    welcome_msg += "\n请选择操作:\n1.查询空房 2.订房 3.退房 4.充值 5.查询余额 0.退出"
                    handle_send(client_socket, welcome_msg)

                else:
                    handle_send(client_socket, '''****************************\n该账号不存在。
                1. 客户登录
                2. 客户注册
                9. 管理员登录
                0. 退出\n****************************\n请重新选择:''')
                    handle_client(client_socket)
                while True:
                    choice = handle_receive(client_socket).strip()
                    if choice == '0':
                        close_connection(client_socket)
                        return
                    handle_body_choice(choice, client_socket,name)
        except pymysql.Error as e:
            handle_send(client_socket, f'登录错误:{e}')
    @staticmethod
    @db_connection_handler
    def register(client_socket, conn=None):
        handle_send(client_socket, "请输入账号（支持汉字、字母、数字、特殊字符组合，不超过10个字符。"
                                   "不能是’0‘或’exit‘，否则直接退出）:")
        name = handle_receive(client_socket)
        if not re.fullmatch(r'^[\w\W]{1,10}$', name):
            handle_send(client_socket,
            '''****************************\n账号格式错误。
                1. 客户登录
                2. 客户注册
                9. 管理员登录
                0. 退出\n****************************\n请重新选择:''')
            handle_client(client_socket)
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT name FROM customers_table WHERE name = %s", (name,))
                if cursor.fetchone():
                    handle_send(client_socket,
                                '''****************************\n该账号已存在。
                        1. 客户登录
                        2. 客户注册
                        9. 管理员登录
                        0. 退出\n****************************\n请重新选择:''')
                    handle_client(client_socket)

                else:
                    handle_send(client_socket, f"您输入的账号是：{name}\n确认注册吗？(Y/N)")
                    confirm = handle_receive(client_socket).upper()
                    if confirm == 'Y':
                        cursor.execute("INSERT INTO customers_table (name, balance) VALUES (%s, 0)", (name,))
                        conn.commit()
                        handle_send(client_socket,
                                    f'****************\n注册成功。\n客户:{name}\n'
                                    f'\n\t查询空房1\n\t订房2\n\t退房3\n\t充值4\n\t查询余额5\n\t退出0\n**************\n请选择:')
                        return
                    elif confirm == 'N':
                        handle_send(client_socket,
                                    '''****************************\n已取消注册。
                            1. 客户登录
                            2. 客户注册
                            9. 管理员登录
                            0. 退出\n****************************\n请重新选择:''')
                        handle_client(client_socket)

                    else:
                        handle_send(client_socket,
                                    '''****************************\n输入无效。
                            1. 客户登录
                            2. 客户注册
                            9. 管理员登录
                            0. 退出\n****************************\n请重新选择:''')
                        handle_client(client_socket)

            while True:
                choice = handle_receive(client_socket)
                if choice == '0':
                    close_connection(client_socket)
                    break
                handle_body_choice(choice, client_socket,name)
        except pymysql.Error as e:
            conn.rollback()
            handle_send(client_socket, f"数据库错误，注册失败:{e}")
    @staticmethod
    @db_connection_handler
    def get_vacant_rooms(client_socket,conn=None):
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT room_number FROM rooms_table")
                result = [row[0] for row in cursor.fetchall()]
                cursor.execute("SELECT room_number FROM rooms_table WHERE status = 'vacant'")
                vacant_rooms = [row[0] for row in cursor.fetchall()]
                handle_send(client_socket,f'****************\n所有房间：{result}\n空闲房间:{vacant_rooms}\n'
                                          f'\n\t查询空房1\n\t订房2\n\t退房3\n\t充值4\n\t查询余额5\n\t退出0\n**************\n请选择:')
                return True
        except pymysql.Error as e:
            handle_send(client_socket,f"查询空闲房间错误:{e}")
            return False
    @staticmethod
    @db_connection_handler
    def book_room(client_socket, name,conn=None):
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT room_number FROM rooms_table WHERE status = 'vacant'")
                vacant_rooms = [row[0] for row in cursor.fetchall()]
                if not vacant_rooms:
                    handle_send(client_socket,"当前没有可用房间。")
                    return True
                handle_send(client_socket, f"空房有{vacant_rooms}\n请输入您要订的房间,输入后将自动扣除卡内金额100元:")
                wanted_room = handle_receive(client_socket)
                if not re.match(r'^\d{3}$', wanted_room):
                    handle_send(client_socket,"")
                    handle_send(client_socket, f'****************\n房间号必须是三位数字。\n\n\t查询空房1\n\t订房2\n\t退房3\n\t充值4\n\t查询余额5\n\t退出0\n**************\n请选择:')
                    return False
                cursor.execute("SELECT status FROM rooms_table WHERE room_number = %s",(wanted_room,))
                room_status = cursor.fetchone()
                if (not room_status) or room_status[0] != 'vacant':
                    handle_send(client_socket, '****************\n该房间已被租用或不存在。\n\n\t查询空房1\n\t订房2\n\t退房3\n\t充值4\n\t查询余额5\n\t退出0\n**************\n请选择:')
                    return False
                handle_send(client_socket,"请输入天数（1-30）：")
                days = int(handle_receive(client_socket))
                if not 1<= days <= 30:
                    handle_send(client_socket, '****************\n天数必须在1-30之间。\n\n\t查询空房1\n\t订房2\n\t退房3\n\t充值4\n\t查询余额5\n\t退出0\n**************\n请选择:')
                    return False
                cursor.execute("SELECT balance FROM customers_table WHERE name = %s",(name,))
                balance = cursor.fetchone()[0]
                price = 100 * days
                if price > balance:
                    handle_send(client_socket, f'****************\n余额不足,需要{price}元，当前余额{balance}元\n\n\t查询空房1\n\t订房2\n\t退房3\n\t充值4\n\t查询余额5\n\t退出0\n**************\n请选择:')
                    return False
                cursor.execute("UPDATE rooms_table SET status = 'occupied', customer_name = %s,check_in_time = NOW(),"
                               "duration_days = %s WHERE room_number = %s",(name,days, wanted_room))
                cursor.execute("UPDATE customers_table SET balance = balance - %s WHERE name = %s",(price, name))
                conn.commit()#提交更改
                send_result = f'订房成功,入住愉快.\n房间:{wanted_room} 花费:{price} 元.'
                handle_send(client_socket, send_result)
            return True
        except (pymysql.Error, ValueError) as e:
            conn.rollback()
            print(f'订房错误:{e}')
            handle_send(client_socket, "订房失败.")
            return False

    @staticmethod
    @db_connection_handler
    def checkout_room(client_socket, name,conn=None):
        send_whatyou_wantto_checkout = "请输入您要退掉的房间:"
        handle_send(client_socket, send_whatyou_wantto_checkout)
        check_out_room = handle_receive(client_socket)
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT customer_name FROM rooms_table WHERE room_number = %s AND status = 'occupied'",(check_out_room,))
                result = cursor.fetchone()
                #如果结果是没有
                if not result or result[0] != name:
                    handle_send(client_socket, "该房间未被您所租用或不存在.请重新输入操作数:")
                    return False
                #如果确有此事
                cursor.execute("UPDATE rooms_table SET status = 'vacant', customer_name = NULL WHERE room_number = %s",(check_out_room,))
                conn.commit()
                handle_send(client_socket, "退房成功.")
            return True
        except pymysql.Error as e:
            conn.rollback()
            handle_send(client_socket,f"退房错误:{e}")
            return False
    @staticmethod
    @db_connection_handler
    def recharge(client_socket, name,conn=None):#充值
        handle_send(client_socket,"请输入您要充值的金额,0 < 输入金额 <= 10000,且小数点后不超过两位:")
        amount_str = handle_receive(client_socket)
        pattern = re.compile(r'^(0*[1-9]\d{0,3}(\.\d{1,2})?|10000(\.0{1,2})?)$')
        if pattern.match(amount_str):
            try:
                amount = float(amount_str)
                with conn.cursor() as cursor:
                    cursor.execute("UPDATE customers_table SET balance = balance + %s WHERE name = %s",(amount, name))
                    cursor.execute("SELECT balance FROM customers_table WHERE name = %s",(name,))
                    new_balance = cursor.fetchone()[0]
                    conn.commit()
                    handle_send(client_socket, f'****************\n充值成功。当前余额：{new_balance}元。\n'
                                          f'\n\t查询空房1\n\t订房2\n\t退房3\n\t充值4\n\t查询余额5\n\t退出0\n**************\n请选择:')
            except pymysql.Error as e:
                conn.rollback()
                handle_send(client_socket,f"充值错误: {e}")
                return False
        else:
            handle_send(client_socket, "****************\n金额形式错误。\n\t查询空房1\n\t订房2\n\t"
                                       "退房3\n\t充值4\n\t查询余额5\n\t退出0\n**************\n请选择:")
            return True
    @staticmethod
    @db_connection_handler
    def check_balance(client_socket, name,conn=None):
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT balance FROM customers_table WHERE name = %s",(name,))
                balance = cursor.fetchone()[0]
                send_balance = f'****************\n卡内余额:{balance} 元'
                cursor.execute("SELECT room_number FROM rooms_table WHERE customer_name = %s",(name,))
                rented_rooms = [row[0] for row in cursor.fetchall()]
            if rented_rooms:
                send_balance += (f'您当前租用的房间为:{rented_rooms}'
                                 f'\n\t查询空房1\n\t订房2\n\t退房3\n\t充值4\n\t查询余额5\n\t退出0\n**************\n请选择:')
            handle_send(client_socket, send_balance)
            return True
        except pymysql.Error as e:
            print(f"查询余额错误:{e}")
            handle_send(client_socket, "查询余额失败")
            return False
