import re
import socket
import pymysql
import threading
from functools import wraps

DB_CONFIG = {
    'host':'localhost','user':'root','password':'123456',
    'database':'hotel_digital_library','charset':'utf8mb4'
}#数据库配置常量
def db_connection_handler(func):
    """数据库连接装饰器,自动管理连接"""
    @wraps(func)
    def wrapper(*args, **kwargs):#元组形参,字典形参
        conn = None
        try:
            conn = pymysql.connect(**DB_CONFIG)
            kwargs['conn'] = conn
            return func(*args, **kwargs)
        except pymysql.Error as e:
            print(f"数据库连接错误:{e}")
            return False
        finally:
            if conn and conn.open:
                conn.close()
    return wrapper
def handle_receive(client_socket):
    '''接收客户端传来的操作数'''
    try:
        data = client_socket.recv(1024)
        return data.decode('utf-8').strip() if data else None
    except (ConnectionResetError, OSError, UnicodeDecodeError) as e:
        print(f"接收数据错误:{e}")
        return None
def handle_send(client_socket, what_you_want_to_send):
    '''发送信息给客户端的函数'''
    try:
        if isinstance(what_you_want_to_send,(list, tuple, dict)):
            what_you_want_to_send = str(what_you_want_to_send)
        client_socket.send(what_you_want_to_send.encode('utf-8'))
    except (ConnectionResetError, OSError) as e:
        print(f"发送数据错误:{e}")
        return False
    return True
def _0_close_connection(client_socket):
    """关闭连接"""
    try:
        what_you_want_to_send = "再见,祝您一路顺风,欢迎下次光临."
        handle_send(client_socket, what_you_want_to_send)
        return True
    except Exception as e:
        handle_send(client_socket, f'关闭连接出现错误:{e}')
    finally:
        client_socket.close()
@db_connection_handler
def init_database(conn = None):
    """数据库初始化"""
    try:
        with conn.cursor() as cursor:
            #一个是管理员表managers_table,里面仅一行,包括了id,管理员名称及密码.
            cursor.execute("""CREATE TABLE IF NOT EXISTS managers_table (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(60) NOT NULL)""")
            #一个是用户表customers_table,里面有id,用户名name,余额balance一共三列
            cursor.execute("""CREATE TABLE IF NOT EXISTS customers_table
                                (id INT AUTO_INCREMENT PRIMARY KEY,
                                name VARCHAR(50) UNIQUE NOT NULL,
                                balance DECIMAL(20,2) DEFAULT 0.00,
                                is_deleted BOOLEAN DEFAULT 0,
                                 deleted_at TIMESTAMP NULL)""")
            #一个是房间表rooms_table,里面有房间room_number,状态status,用户名customer_name一共三列,状态分两种,但默认值是vacant空置
            cursor.execute("""CREATE TABLE IF NOT EXISTS rooms_table
                                (room_number VARCHAR(10) PRIMARY KEY,
                                status ENUM('vacant','occupied') DEFAULT 'vacant',
                                customer_name VARCHAR(50),
                                FOREIGN KEY (customer_name) REFERENCES customers_table(name) ON DELETE SET NULL)""")
            #初始化:管理员密码
            cursor.execute("SELECT COUNT(*) FROM managers_table")
            if cursor.fetchone()[0] == 0:
                pwd = "pass123456"
                cursor.execute("INSERT INTO managers_table (username, password) VALUES (%s, %s)", ('管理员', pwd))
            #初始化:有两个用户
            cursor.execute("SELECT COUNT(*) FROM customers_table")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO customers_table (name, balance) VALUES (%s, %s)", ('张三',300))
                cursor.execute("INSERT INTO customers_table (name, balance) VALUES (%s, %s)", ('李四',400))
            #初始化:有5个房间
            if cursor.execute("SELECT COUNT(*) FROM rooms_table") == 0:
                rooms = ['201', '202', '203', '204', '205']
                cursor.execute("INSERT INTO rooms_table (room_number,status) VALUES (%s, 'vacant')", [(r,) for r in rooms])
        conn.commit()
        return True
    except pymysql.Error as e:
        conn.rollback()
        print(f"数据库初始化错误:{e}")
        return False

if __name__ == "__main__":
    init_database()
name = ""

class AdminManager:
    """管理员功能封装类"""
    @staticmethod
    @db_connection_handler
    def _9_authenticate(username,password,conn=None):
        """管理员认证"""
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT password FROM managers_table WHERE username = %s", (username,))
                result = cursor.fetchone()  #result是一个元组
                if result and result[0] == password:
                    return True
        except pymysql.Error as e:
            print(f'管理员认证错误:{e}')
            return False
    @staticmethod
    @db_connection_handler
    def data_presentation(client_socket,conn=None):
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
        handle_send(client_socket,"请输入您要增删改查的类型:\t1.客户\t2.房间\t0.退出\t请选择:")
class CustomerManager:
    """客户管理功能"""
    @staticmethod
    @db_connection_handler
    def _1_modify_name(client_socket,old_name,new_name, conn=None):
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE customers_table SET name = %s WHERE name = %s", (new_name, old_name))
                conn.commit()  # 提交更改
                handle_send(client_socket, f'修改成功,当前账号名称:{new_name}.\n'
                                           f'请继续选择您要增删改查的类型：客户(输入1),房间(输入2),退出(输入0):)')
                return True
        except pymysql.Error as e:
            conn.rollback()
            handle_send(client_socket,f'修改账号错误:{e}')
            return False
    @staticmethod
    @db_connection_handler
    def _2_modify_balance(client_socket, name,amount,conn=None):
        try:
            if not re.match(r'^\d+(\.\d{1,2})?$', str(amount)):
                handle_send(client_socket,"金额格式无效（示例：100.50）,请重新选择您要修改的这位客户的内容(1修改账号，2修改余额，3注销):")
            amount = float(amount)
            with conn.cursor() as cursor:
                cursor.execute("UPDATE customers_table SET balance = %s WHERE name = %s",(amount, name))
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
    def _3_delete_customer(client_socket,**kwargs):#软删除
        conn = kwargs.get('conn')
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE customers_table SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP WHERE name = %s", (name,))
                conn.commit()  # 提交更改
                handle_send(client_socket, f'客户已标记为删除.')
                return True
        except pymysql.Error as e:
            conn.rollback()
            handle_send(client_socket, f'注销账号错误:{e}')
            return False
class RoomManager:
    """房间管理功能"""
    @staticmethod
    @db_connection_handler
    def get_vacant_rooms(client_socket,conn=None):
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT room_number FROM rooms_table WHERE status = 'vacant'")
                vacant_rooms = [row[0] for row in cursor.fetchall()]
                handle_send(client_socket,f'空闲房间:{vacant_rooms}')
                return vacant_rooms
        except pymysql.Error as e:
            handle_send(client_socket,f"查询空闲房间错误:{e}")
            return False
    @staticmethod
    @db_connection_handler
    def _1_empty_room(client_socket,conn=None):  # 房间置空
        handle_send(client_socket, "请输入您要置空的房间:")
        room = handle_receive(client_socket).strip()
        try:
            with conn.cursor() as cursor:
                # 查询该房间是否被该用户租用
                cursor.execute("SELECT room_number FROM rooms_table WHERE room_number = %s AND status = 'occupied'",(room,))
                result = cursor.fetchone()
                if not result:
                    handle_send(client_socket,"该房间未被租用或不存在.")
                    return False
                # 如果确有此事
                cursor.execute("UPDATE rooms_table SET status='vacant', customer_name=NULL WHERE room_number=%s",(room,))
                conn.commit()
                handle_send(client_socket,"置空房间成功.")
                return True
        except pymysql.Error as e:
            conn.rollback()
            handle_send(client_socket, f"置空房间错误:{e}")
    @staticmethod
    @db_connection_handler
    def _2_occupy_room(client_socket,room_number,conn=None):
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT status FROM rooms_table WHERE room_number = %s", (room_number,))
                room_status = cursor.fetchone()
                if (not room_status) or room_status[0] != 'vacant':
                    handle_send(client_socket, "该房间已被租用或不存在")
                    return False
                cursor.execute(
                "UPDATE rooms_table SET status = 'occupied', customer_name = %s WHERE room_number = %s", ('manager',room_number))
                conn.commit()
                handle_send(client_socket, "占房成功.请继续选择您要增删改查的类型")
                return True
        except pymysql.Error as e:
            conn.rollback()
            handle_send(client_socket, f'订房错误:{e}')
            return False
    @staticmethod
    @db_connection_handler
    def _3_add_room(client_socket,conn=None):#增加新可租房间
        handle_send(client_socket, "请输入您要增加的房间XXX(每次仅允许输入一个):")
        room = handle_receive(client_socket).strip()
        try:
            with conn.cursor() as cursor:
                if not re.match(r'^\d{3}$', room):  # 房间号格式验证
                    handle_send(client_socket, f"{room}房间号格式无效")
                    return False
                cursor.execute("INSERT INTO rooms_table (room_number,status) VALUES (%s,'vacant')", (room,))
                handle_send(client_socket, f"成功添加房间：{room}\n")
                conn.commit()
                handle_send(client_socket, "请继续选择您要增删改查的类型:")
                return True
        except pymysql.Error as e:
            conn.rollback()
            handle_send(client_socket, f"添加失败：{e},自动退出")
        except ValueError as ve:
            handle_send(client_socket, f"输入错误：{ve},自动退出")
    @staticmethod
    @db_connection_handler
    def _4_reduce_room(client_socket,conn):#减少可租房间
        handle_send(client_socket, "请输入不出租的房间(每次输入一个):")
        room_str = handle_receive(client_socket).strip()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT room_number FROM rooms_table WHERE room_number = %s",(room_str,))
                room_ = cursor.fetchone()
                if (not room_):
                    handle_send(client_socket, f"该房间列表中,{room_str}不存在.")
                cursor.execute("DELETE FROM rooms_table WHERE room_number = %s",(room_str,))
                conn.commit()
                cursor.execute("SELECT room_number FROM rooms_table ")
                rooms = [row[0] for row in cursor.fetchall()]
                send_list = f'操作结束,现在可租房间有{rooms},'
                cursor.execute("SELECT room_number FROM rooms_table WHERE status = 'vacant'")
                vacant_rooms = [row[0] for row in cursor.fetchall()]
                send_list += f'空闲房间有{vacant_rooms}'
                handle_send(client_socket, send_list)
                return True
        except pymysql.Error as e:
            handle_send(client_socket, f"减少房间错误:{e}")
            return False
class CustomerService:
    @staticmethod
    @db_connection_handler
    def login(client_socket,**kwargs):
        conn = kwargs.get('conn')
        handle_send(client_socket, "输入账号完成登录:")
        name = handle_receive(client_socket)
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT name FROM customers_table WHERE name = %s", (name,))
                if cursor.fetchone():
                    handle_send(client_socket,
                        f"登录成功\n客户:{name}\n请输入操作数(查询空房1,订房2,退房3,充值4,查询余额5,退出0):")
                else:
                    handle_send(client_socket, "您未注册,请重新选择:")
                    handle_client(client_socket)
                while True:
                    choice = handle_receive(client_socket).strip()
                    if choice == '0':
                        _0_close_connection(client_socket)
                        return
                    handle_body_choice(choice, client_socket,name)
        except pymysql.Error as e:
            handle_send(client_socket, f'登录错误:{e}')
    @staticmethod
    @db_connection_handler
    def register(client_socket, conn=None):
        handle_send(client_socket, "输入账号完成注册:")
        name = handle_receive(client_socket)
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT name FROM customers_table WHERE name = %s", (name,))
                if cursor.fetchone():
                    handle_send(client_socket,
                        f"您之前已经注册过了,登录成功\n客户:{name}\n请输入操作数(查询空房1,订房2,退房3,充值4,查询余额5,退出0):")
                else:
                    cursor.execute("INSERT INTO customers_table (name, balance) VALUES (%s, 0)", (name,))
                    conn.commit()
                    handle_send(client_socket,
                        f"注册成功,已为您自动登录.\n客户:{name}\n请输入操作数(查询空房1,订房2,退房3,充值4,查询余额5,退出0):")
            while True:
                choice = handle_receive(client_socket)
                if choice == '0':
                    _0_close_connection(client_socket)
                    break
                handle_body_choice(choice, client_socket,name)
        except pymysql.Error as e:
            conn.rollback()
            handle_send(client_socket, f"注册失败:{e}")
    @staticmethod
    @db_connection_handler
    def _1_get_vacant_rooms(client_socket,conn=None):
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT room_number FROM rooms_table WHERE status = 'vacant'")
                vacant_rooms = [row[0] for row in cursor.fetchall()]
                handle_send(client_socket,f'空闲房间:{vacant_rooms}')
                return True
        except pymysql.Error as e:
            handle_send(client_socket,f"查询空闲房间错误:{e}")
            return False
    @staticmethod
    @db_connection_handler
    def _2_book_room(client_socket, name,conn=None):
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT room_number FROM rooms_table")
                result = [row[0] for row in cursor.fetchall()]
                cursor.execute("SELECT room_number FROM rooms_table WHERE status = 'vacant'")
                vacant_rooms = [row[0] for row in cursor.fetchall()]
                handle_send(client_socket, f"房间共有{result}\n"
                                           f"空房共有{vacant_rooms}\n默认无限期订房,请输入您要订的房间,输入后将自动扣除卡内金额100元:")
                wanted_room = handle_receive(client_socket)
                cursor.execute("SELECT status FROM rooms_table WHERE room_number = %s",(wanted_room,))
                room_status = cursor.fetchone()
                if (not room_status) or room_status[0] != 'vacant':
                    handle_send(client_socket, "该房间已被租用或不存在,请重新输入操作数:")
                    return
                cursor.execute("SELECT balance FROM customers_table WHERE name = %s",(name,))
                balance = cursor.fetchone()[0]
                price = 100
                if price > balance:
                    send_inform = "余额不足,需前往充值后再订房,请输入操作数:"
                    handle_send(client_socket, send_inform)
                    return
                else:
                    new_balance = balance - price
                    cursor.execute("UPDATE customers_table SET balance = balance - %s WHERE name = %s",(price, name))
                    cursor.execute("UPDATE rooms_table SET status = 'occupied', customer_name = %s WHERE room_number = %s",(name, wanted_room))
                    conn.commit()#提交更改
                    send_result = f'已从卡内扣除金额,订房成功,入住愉快.卡内余额:{new_balance} 元.'
                    handle_send(client_socket, send_result)
            return True
        except pymysql.Error as e:
            conn.rollback()
            print(f'订房错误:{e}')
            handle_send(client_socket, "订房失败,请稍后再试")
            return False
    @staticmethod
    @db_connection_handler
    def _3_checkout_room(client_socket, name,conn=None):
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
    def _4_recharge(client_socket, name,conn=None):#充值
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
                    handle_send(client_socket, f'充值成功。当前余额：{new_balance}元')
            except pymysql.Error as e:
                conn.rollback()
                handle_send(client_socket,f"充值错误: {e}")
                return False
        else:
            handle_send(client_socket, "金额形式错误。请重新选择操作数:")
    @staticmethod
    @db_connection_handler
    def _5_check_balance(client_socket, name,conn=None):
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT balance FROM customers_table WHERE name = %s",(name,))
                balance = cursor.fetchone()[0]
                send_balance = f'卡内余额:{balance} 元'
                cursor.execute("SELECT room_number FROM rooms_table WHERE customer_name = %s",(name,))
                rented_rooms = [row[0] for row in cursor.fetchall()]
            if rented_rooms:
                send_balance += f',您当前租用的房间为:{rented_rooms}'
            handle_send(client_socket, send_balance)
            return True
        except pymysql.Error as e:
            print(f"查询余额错误:{e}")
            handle_send(client_socket, "查询余额失败")
            return False
def handle_body_choice(choice,client_socket,name):
    if choice == '1':
        CustomerService._1_get_vacant_rooms(client_socket)
    elif choice == '2':
        CustomerService._2_book_room(client_socket, name)
    elif choice == '3':
        CustomerService._3_checkout_room(client_socket,name)
    elif choice == '4':
        CustomerService._4_recharge(client_socket, name,conn=None)
    elif choice == '5':
        CustomerService._5_check_balance(client_socket,name)
    elif choice == '0':
        _0_close_connection(client_socket)
        return True
    else:
        handle_send(client_socket,"无效的body_choice,请重新输入.")
def handle_admin_operations(client_socket):
    """处理管理员的各种操作"""
    # 管理员认证
    handle_send(client_socket, "管理员登录\n请输入管理员名称:")
    username = handle_receive(client_socket)
    handle_send(client_socket, "请输入密码:")
    password = handle_receive(client_socket)
    if not AdminManager._9_authenticate(username, password):
        handle_send(client_socket, "认证失败,请重新选择操作数")
        handle_client(client_socket)
    else:
        handle_send(client_socket, "管理员登录成功")
        #显示数据给管理员
        AdminManager.data_presentation(client_socket)
        # 显示管理员菜单
        menu = """
        管理员菜单:
        1. 客户管理
        2. 房间管理
        0. 退出
        请输入选择: """
        handle_send(client_socket, menu)
        choice = handle_receive(client_socket)
        while True:
            if choice == '1':  # 客户管理
                if not handle_admin_customer_management(client_socket):
                    break
            elif choice == '2':  # 房间管理
                if not handle_admin_room_management(client_socket):
                    break
            elif choice == '0':  # 退出
                _0_close_connection(client_socket)
                return
            else:
                handle_send(client_socket, "无效的选择，请重新输入")
def handle_admin_customer_management(client_socket):
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
        if not choice or choice == '0':
            return True
        if choice == '1':  # 修改客户名称
            handle_send(client_socket, "请输入要修改的客户原名称:")
            old_name = handle_receive(client_socket)
            handle_send(client_socket, "请输入新名称:")
            new_name = handle_receive(client_socket)
            if old_name and new_name:
                CustomerManager._1_modify_name(client_socket, old_name, new_name)
        elif choice == '2':  # 修改客户余额
            handle_send(client_socket, "请输入客户名称:")
            name = handle_receive(client_socket)
            handle_send(client_socket, "请输入新的余额:")
            amount = handle_receive(client_socket)
            if name and amount and re.match(r'^\d+(\.\d{1,2})?$', amount):
                CustomerManager._2_modify_balance(client_socket, name, float(amount))
            else:
                handle_send(client_socket, "输入无效")
        elif choice == '3':  # 删除客户
            handle_send(client_socket, "请输入要删除的客户名称:")
            name = handle_receive(client_socket)
            if name:
                CustomerManager._3_delete_customer(client_socket)
        else:
            handle_send(client_socket, "无效的选择.请重新输入:")
def handle_admin_room_management(client_socket):
    """管理员对房间的管理"""
    while True:
        menu = """
        房间管理:
        1. 房间置空
        2. 占用房间
        3. 添加房间
        4. 移除房间
        0. 返回
        请输入选择: """
        handle_send(client_socket, menu)

        choice = handle_receive(client_socket)
        if not choice or choice == '0':
            break

        if choice == '1':  # 房间置空
            handle_send(client_socket, "请输入要置空的房间号:")
            room_number = handle_receive(client_socket)

            if room_number:
                RoomManager._1_empty_room(client_socket, room_number)

        elif choice == '2':  # 占用房间
            handle_send(client_socket, "请输入要占用的房间号:")
            room_number = handle_receive(client_socket)
            if room_number:
                RoomManager._2_occupy_room(client_socket, room_number)

        elif choice == '3':  # 添加房间
            RoomManager._3_add_room(client_socket)

        elif choice == '4':  # 移除房间
            rooms_input = handle_receive(client_socket)
            if rooms_input:
                RoomManager._4_reduce_room(client_socket)
        else:
            handle_send(client_socket, "无效的选择.请重新输入:")

def handle_client(client_socket):
    try:
        while True:
            choice = handle_receive(client_socket)
            if not choice:
                break
            if choice == '1':  # 客户登录
                CustomerService.login(client_socket)
                break
            elif choice == '2':  # 客户注册
                CustomerService.register(client_socket)
                break
            elif choice == '9':  # 管理员登录
                handle_admin_operations(client_socket)
                break
            elif choice == '0':  # 退出
                _0_close_connection(client_socket)
                break
            else:
                handle_send(client_socket, "无效选择，请重新输入")
    except Exception as e:
        print(f"处理客户端出错: {e}")
    except ConnectionResetError:
        print("客户端强制断开")
    finally:
        try:
            client_socket.shutdown(socket.SHUT_RDWR)  # 优雅关闭连接
        except OSError:
            pass
        client_socket.close()
        print("服务端已断开客户端连接")
def main():
    """程序入口"""
    # 初始化数据库
    if not init_database():
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
            client_thread = threading.Thread(target=handle_client, args=(client_socket,))
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
            handle_send(client_socket, welcome)
    except KeyboardInterrupt:
        print("\n服务器正在关闭...")
    except Exception as e:
        print(f"服务器错误: {e}")
    finally:
        server.close()
        print("服务器关闭")

if __name__ == "__main__":
    main()
