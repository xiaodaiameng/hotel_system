########################该套代码没有增加管理员功能
import socket
import pymysql
import threading
# from threading import Lock
# from pymysql import cursors

#连接数据库的函数
def create_db_connection():
    try:
        conn = pymysql.connect(host='localhost',user='root',password='123456',
                               database='hotel_digital_library',charset='utf8mb4')
        return conn
    except pymysql.Error as e:
        print(f"数据库连接错误:{e}")
        return None

#初始化数据库表结构
def init_database():
    conn = create_db_connection()
    if conn is None:
        return False
    try:
        with conn.cursor() as cursor:

            '''创建两个表,一个是用户表customers_table,里面有id,用户名name,余额balance一共三列'''

            cursor.execute('''CREATE TABLE IF NOT EXISTS customers_table
                                (id INT AUTO_INCREMENT PRIMARY KEY,
                                name VARCHAR(50) UNIQUE NOT NULL,
                                balance DECIMAL(20,2) DEFAULT 0.00)''')

            '''另一个是房间表rooms_table,里面有房间room_number,状态status,用户名customer_name一共三列,状态分两种,但默认值是vacant空置'''

            cursor.execute('''CREATE TABLE IF NOT EXISTS rooms_table
                                (room_number VARCHAR(10) PRIMARY KEY,
                                status ENUM('vacant','occupied') DEFAULT 'vacant',
                                customer_name VARCHAR(50),
                                FOREIGN KEY (customer_name) REFERENCES customers_table(name) ON DELETE SET NULL)''')
            #初始化:有两个用户
            cursor.execute("SELECT COUNT(*) FROM customers_table")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO customers_table (name, balance) VALUES (%s, %s)", ('张三',300))
                cursor.execute("INSERT INTO customers_table (name, balance) VALUES (%s, %s)", ('李四',400))

            #初始化:有5个房间
            cursor.execute("SELECT COUNT(*) FROM rooms_table")
            if cursor.fetchone()[0] == 0:
                for room in ['201', '202', '203', '204', '205']:
                    cursor.execute("INSERT INTO rooms_table (room_number,status) VALUES (%s, 'vacant')", (room,))
        conn.commit()
        return True
    except pymysql.Error as e:
        print(f"数据库初始化错误:{e}")
        return False
    finally:
        conn.close()

###############################完成后显示两个表给自己服务端看一下:
conn = create_db_connection()
if conn is None:
    print("数据库连接出现错误")
else:
    table1 = "customers_table"
    table2 = "rooms_table"
    with conn.cursor() as cursor:
        cursor.execute(f"SELECT * FROM {table1}")
        rows = cursor.fetchall()
        #打印表头（列名）
        columns = [desc[0] for desc in cursor.description]
        print("\t   ".join(columns))  #用制表符分隔列名
        #打印每一行数据
        for row in rows:
            print("\t\t".join(map(str, row)))
        #第二个表用同样的操作打印出来
        cursor.execute(f"SELECT * FROM {table2}")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        print("\t\t".join(columns))
        for row in rows:
            print("\t\t\t\t".join(map(str, row)))
    #关闭游标和关闭连接
    cursor.close()
    conn.close()

name = ""

#接收客户端传来的操作数
def handle_receive(client_socket):
    return client_socket.recv(1024).decode('utf-8').strip()
#发送信息给客户端的函数
def handle_send(client_socket, what_you_want_to_send):
    client_socket.send(what_you_want_to_send.encode('utf-8'))

# 多线程时
# def input_0():
#     say_goodbye = "再见,祝您一路顺风,欢迎下次光临."
#     handle_send(say_goodbye)
#     client_socket.shutdown(socket.SHUT_DWORD)  # 优雅地关闭....
#     client_socket.close()  # 不能直接使用exit(9)退出整个服务端,仅关闭当前客户端即可

def input_0(client_socket):
    say_goodbye = "再见,祝您一路顺风,欢迎下次光临."
    handle_send(client_socket, say_goodbye)
    # exit(9)
    client_socket.close()


def get_1(client_socket):#查询空房 vacant_room

    conn = create_db_connection()
    if conn is None:
        handle_send(client_socket, "系统错误,请稍后再试")
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT room_number FROM rooms_table WHERE status = 'vacant'")
            vacant_rooms = [row[0] for row in cursor.fetchall()]
            send_list = f'空闲房间有{vacant_rooms}'
            handle_send(client_socket, send_list)
    except pymysql.Error as e:
        print(f"查询空闲房间出现错误:{e}")
        handle_send(client_socket, "查询空闲房间失败")
    finally:
        conn.close()

def get_2(client_socket, name):#订房
    handle_send(client_socket, "默认无限期订房,请输入您要订的房间,输入后将自动扣除卡内金额100元:")
    wanted_room = handle_receive(client_socket)
    valid_rooms = {'201', '202', '203', '204', '205'}#有效房间号
    if wanted_room not in valid_rooms:
        handle_send(client_socket, "无效房间号，应输入201-205之间的房间,请重新选择操作数:")
        return

    conn = create_db_connection()
    if conn is None:
        handle_send(client_socket, "系统错误,请稍后再试")
        return
    try:
        with conn.cursor() as cursor:

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
                conn.begin()
                cursor.execute("UPDATE customers_table SET balance = balance - %s WHERE name = %s",(price, name))
                cursor.execute("UPDATE rooms_table SET status = 'occupied', customer_name = %s WHERE room_number = %s",(name, wanted_room))
                conn.commit()#提交更改

                send_result = f'已从卡内扣除金额,订房成功,入住愉快.卡内余额:{new_balance} 元.'
                handle_send(client_socket, send_result)

    except pymysql.Error as e:
        conn.rollback()
        print(f'订房错误:{e}')
        handle_send(client_socket, "订房失败,请稍后再试")
    finally:
        conn.close()

def get_3(client_socket, name):#退房
    send_whatyou_wantto_checkout = "请输入您要退掉的房间:"
    handle_send(client_socket, send_whatyou_wantto_checkout)
    check_out_room = handle_receive(client_socket)
    print("收到客户端要退的房间： " + check_out_room)

    conn = create_db_connection()
    if conn is None:
        handle_send(client_socket, "系统错误,请稍后再试")
        return
    try:
        with conn.cursor() as cursor:
            #查询该房间是否被该用户租用
            cursor.execute("SELECT customer_name FROM rooms_table WHERE room_number = %s AND status = 'occupied'",(check_out_room,))
            result = cursor.fetchone()
            #如果结果是没有
            if not result or result[0] != name:
                handle_send(client_socket, "该房间未被您所租用或不存在.请重新输入操作数:")
                return
            #如果确有此事
            cursor.execute("UPDATE rooms_table SET status = 'vacant', customer_name = NULL WHERE room_number = %s",(check_out_room,))
            conn.commit()
            handle_send(client_socket, "退房成功.")
    except pymysql.Error as e:
        conn.rollback()
        print(f"退房错误:{e}")
        handle_send(client_socket, "退房失败,请稍后再试")
    finally:
        conn.close()


def get_4(client_socket, name):#充值
    handle_send(client_socket,"请输入您要充值的金额,整数部分不超过18位,小数部分不超过2位:")
    amount_str = handle_receive(client_socket)
    try:
        float(amount_str)
        if float(amount_str) > 0:
            amount = float(amount_str)
            conn = create_db_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("UPDATE customers_table SET balance = balance + %s WHERE name = %s",(amount, name))
                    cursor.execute("SELECT balance FROM customers_table WHERE name = %s",(name,))

                    new_balance = cursor.fetchone()[0]
                    conn.commit()
                    handle_send(client_socket, f'充值成功。当前余额：{new_balance}元')
            except pymysql.Error as e:
                conn.rollback()
                print(f"充值错误: {e}")
                handle_send(client_socket, "充值失败，请稍后再试")
            finally:
                conn.close()
        else:
            handle_send(client_socket, "充值金额不能是负数或零,请重新选择操作数:")
    except ValueError:
        handle_send(client_socket, "金额形式错误。请重新选择操作数:")

#也可以使用正则表达式判断字符串是不是数字
# import re
# amount_str = handle_receive().strip()  #去除首尾空格
# 严格校验输入格式:如果不是大于零的数字:
# if not re.fullmatch(r'^(0\.\d+|[1-9]\d*(\.\d+)?)$', amount_str):

def get_5(client_socket, name):#查询余额,以及判断用户是否正在租用房间,如果有顺便告诉他
    conn = create_db_connection()
    if conn is None:
        handle_send(client_socket, "系统错误,请稍后再试")
        return
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
    except pymysql.Error as e:
        print(f"查询余额错误:{e}")
        handle_send(client_socket, "查询余额失败")
    finally:
        conn.close()

def handle_login(client_socket):
    handle_send(client_socket, "输入账号完成登录:")
    name = handle_receive(client_socket)

    conn = create_db_connection()
    if conn is None:
        handle_send(client_socket, "系统错误,请稍后再试")
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT name FROM customers_table WHERE name = %s", (name,))
            if cursor.fetchone():
                handle_send(
                    client_socket,
                    f"登录成功\n客户:{name}\n请输入操作数(查询空房1,订房2,退房3,充值4,查询余额5,退出0):")
                while True:
                    # subordinate adj.从属的,次要的,下级的
                    choice = handle_receive(client_socket).strip()
                    if choice == '0':
                        input_0(client_socket)
                        return
                    handle_body_choice(choice,client_socket, name)
                    if choice == '0':
                        break
            else:
                handle_send(client_socket, "您未注册,请重新选择:")
    except pymysql.Error as e:
        print(f'登录错误:{e}')
        handle_send(client_socket, "登录失败,请稍后再试")
    finally:
        conn.close()

def handle_register(client_socket):
    handle_send(client_socket, "输入账号完成注册:")
    name = handle_receive(client_socket)
    conn = create_db_connection()
    if conn is None:
        handle_send(client_socket, "系统错误，请稍后再试")
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT name FROM customers_table WHERE name = %s", (name,))
            if cursor.fetchone():
                handle_send(
                    client_socket,
                    f"您之前已经注册过了,登录成功\n客户:{name}\n请输入操作数(查询空房1,订房2,退房3,充值4,查询余额5,退出0):")
            else:
                cursor.execute("INSERT INTO customers_table (name, balance) VALUES (%s, 0)", (name,))
                conn.commit()
                handle_send(
                    client_socket,
                    f"注册成功,已为您自动登录.\n客户:{name}\n请输入操作数(查询空房1,订房2,退房3,充值4,查询余额5,退出0):")
        while True:
            choice = handle_receive(client_socket)
            handle_body_choice(choice,client_socket, name)
            if choice == '0':
                break
    except pymysql.Error as e:
        conn.rollback()
        handle_send(client_socket, "注册失败,请稍后再试")
    finally:
        conn.close()
#移除递归调用，改为在每次处理完选项后，
#重新进入主循环等待新输入。需要重构代码逻辑，将主循环与业务逻辑分离

def handle_body_choice(choice,client_socket, name):
    switch = {
        '0':lambda:input_0(client_socket),
        '1':lambda: get_1(client_socket),
        '2':lambda: get_2(client_socket, name),
        '3':lambda: get_3(client_socket, name),
        '4':lambda: get_4(client_socket, name),
        '5':lambda: get_5(client_socket, name),
    }
    func = switch.get(choice,lambda:handle_send(client_socket, "无效的body_choice，请重新输入:") )
    func()

def handle_client(client_socket):
    try:
        #显示界面到客户端
        welcome = "欢迎来到旅店管理系统"
        handle_send(client_socket, welcome.center(20, '*')+"\n"+
                    "\t\t1登录\n\t\t2注册\n\t\t0退出\n或输入 exit 强制断开连接.\n"+26*"*"+
                    "\n请输入操作数:")
        while True:
            choice = handle_receive(client_socket).strip()
            if choice == '1':
                handle_login(client_socket)
            elif choice == '2':
                handle_register(client_socket)
            elif choice == '0':
                input_0(client_socket)
                #######################################不太理解
                return
            else:
                handle_send(client_socket, "无效的head_choice,请重新输入.")
    except ConnectionResetError:
        print("客户端异常断开")
    finally:
        client_socket.close()


def main():
    # socket部分
    # 创建会话对象
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 建立连接
    SERVER_ADDRESS = '192.168.219.83'
    server.bind((SERVER_ADDRESS, 8001))
    # 设置监听
    server.listen(5)
    print('####程序启动.等待客户端连接')
    while True:
        client_socket, addr = server.accept()
        print(f'新客户端连接:{addr}')

        #创建新线程处理客户端
        client_thread = threading.Thread(target = handle_client, args = (client_socket,))
        #设置为守护线程
        client_thread.daemon = True
        #开启多线程
        client_thread.start()

if __name__ == "__main__":
    main()
