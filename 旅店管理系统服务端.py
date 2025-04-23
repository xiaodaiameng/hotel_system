import re
import socket
import pymysql
import threading

#连接数据库的函数
def create_db_connection():
    try:
        conn = pymysql.connect(host='localhost',user='root',password='123456',
                               database='hotel_digital_library',charset='utf8mb4')
        return conn
    except pymysql.Error as e:
        print(f"数据库连接错误:{e}")
        return False

# 初始化数据库表结构
def init_database():
    conn = create_db_connection()
    if conn is None:
        return False
    try:
        with conn.cursor() as cursor:
            '''一个是管理员表,仅一行,包括id,管理员名称以及密码'''
            cursor.execute('''CREATE TABLE IF NOT EXISTS managers_table (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(60) NOT NULL
            )''')

            conn.commit()
            '''一个是用户表customers_table,里面有id,用户名name,余额balance一共三列'''
            cursor.execute('''CREATE TABLE IF NOT EXISTS customers_table
                                (id INT AUTO_INCREMENT PRIMARY KEY,
                                name VARCHAR(50) UNIQUE NOT NULL,
                                balance DECIMAL(20,2) DEFAULT 0.00)''')
            conn.commit()
            '''一个是房间表rooms_table,里面有房间room_number,状态status,用户名customer_name一共三列,状态分两种,但默认值是vacant空置'''
            cursor.execute('''CREATE TABLE IF NOT EXISTS rooms_table
                                (room_number VARCHAR(10) PRIMARY KEY,
                                status ENUM('vacant','occupied') DEFAULT 'vacant',
                                customer_name VARCHAR(50),
                                FOREIGN KEY (customer_name) REFERENCES customers_table(name) ON DELETE SET NULL)''')
            conn.commit()
            #初始化:管理员密码
            cursor.execute("SELECT COUNT(*) FROM managers_table")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO managers_table (username, password) VALUES (%s, %s)",('管理员','pass123456'))
                conn.commit()
            #初始化:有两个用户
            cursor.execute("SELECT COUNT(*) FROM customers_table")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO customers_table (name, balance) VALUES (%s, %s)", ('张三',300))
                cursor.execute("INSERT INTO customers_table (name, balance) VALUES (%s, %s)", ('李四',400))
                conn.commit()
            #初始化:有5个房间
            if cursor.execute("SELECT COUNT(*) FROM rooms_table") == 0:
                rooms = ['201', '202', '203', '204', '205']
                cursor.execute("INSERT INTO rooms_table (room_number,status) VALUES (%s, 'vacant')", [(r,) for r in rooms])
                conn.commit()
        return True
    except pymysql.Error as e:
        print(f"数据库初始化错误:{e}")
        return False
    finally:
        conn.close()

###############################完成后显示三个表给自己服务端看一下:
if __name__ == "__main__":
    conn = create_db_connection()
    if conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM managers_table")
            print("管理员表:\n", cursor.fetchall())
            cursor.execute("SELECT * FROM customers_table")
            print("用户表:\n", cursor.fetchall())
            cursor.execute("SELECT * FROM rooms_table")
            print("房间表:\n", cursor.fetchall())
        conn.close()

name = ""

#接收客户端传来的操作数
def handle_receive(client_socket):
    try:
        data = client_socket.recv(1024)
        if not data:
            return None
        return data.decode('utf-8').strip()
    except (ConnectionResetError, OSError):
        return None

#发送信息给客户端的函数
def handle_send(client_socket, what_you_want_to_send):
    client_socket.send(what_you_want_to_send.encode('utf-8'))

def data_presentation(client_socket):#像显示给服务端看一样显示给管理员所在的客户端
    conn = create_db_connection()
    if conn is None:
        print("数据库连接出现错误")
    else:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM managers_table")
            result1 = "管理员表:\n", cursor.fetchall()
            handle_send(client_socket,f"{result1}")
            cursor.execute("SELECT * FROM customers_table")
            result2 = "用户表:\n", cursor.fetchall()
            handle_send(client_socket,f"{result2}")
            cursor.execute("SELECT * FROM rooms_table")
            result3 = "房间表:\n", cursor.fetchall()
            handle_send(client_socket,f"{result3}")
        cursor.close()
        conn.close()

#怎么运用 class CRUD(client_socket, name, room):  # （create, read, update, delete）
def input_9(client_socket):
    try:
        handle_send(client_socket, "输入管理员名称:")
        username = handle_receive(client_socket).strip()
        if username != '管理员':
            handle_send(client_socket, "非法账号,请重新选择head_操作数:")
            return
        else:
            handle_send(client_socket, "输入密码:")
            input_pwd = handle_receive(client_socket).strip()
            if input_pwd is None:
                return
        conn = create_db_connection()
        if conn is None:
            handle_send(client_socket, "系统错误,请稍后再试")
            return
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT password FROM managers_table WHERE username = %s", (username,))
                result = cursor.fetchone()# result是一个元组

                if result and result[0] == input_pwd:
                    handle_send(client_socket, "密码正确,管理员登录成功.")
                    data_presentation(client_socket)
                    handle_send(client_socket, f"\n请输入您要增删改查的类型：客户(输入1),房间(输入2),退出(输入0)：")
                    while True:
                        # subordinate adj.从属的,次要的,下级的
                        choice = handle_receive(client_socket).strip()
                        if choice == '0':
                            input_0(client_socket)
                            return
                        elif choice == '1':
                            crud_1(client_socket)
                            break
                        elif choice == '2':
                            crud_2(client_socket)
                            break
                #########################################
                        else:
                            handle_send(client_socket,"选择无效.请重新选择(客户1,房间2,退出0):")
                else:
                    handle_send(client_socket, "密码错误.请重新在封面选择head操作数:")
                    # client_socket.close()
                    return
        except pymysql.Error as e:
            print(f'input_9()错误:{e}')
            handle_send(client_socket, "input_9()失败,请稍后再试")
        finally:
            conn.close()
    except OSError:
        print("管理员登录过程中连接断开.")

def crud_1(client_socket):
    handle_send(client_socket, "输入客户账号:")
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
                    f"请输入您要修改的内容:（1修改账号，2修改余额，3注销）")
                choice = handle_receive(client_socket)
                handle_crud1(choice, client_socket, name)
            else:
                handle_send(client_socket,"该客户不存在,请重新选择您要增删改查的类型：客户(输入1),房间(输入2),退出(输入0):)")
                while True:
                    choice = handle_receive(client_socket).strip()
                    if choice == '0':
                        input_0(client_socket)
                        return
                    elif choice == '1':
                        crud_1(client_socket)
                        break
                    elif choice == '2':
                        crud_2(client_socket)
                        break
    except Exception as e:
        print(f"crud_1()错误:{e}")
        handle_send(client_socket, f"crud_1()错误:{e}")
    finally:
        conn.close()
def m1_1(client_socket,name):#修改账号
    handle_send(client_socket, "输入新账号,确认再回车:")
    new_name = handle_receive(client_socket)

    conn = create_db_connection()
    if conn is None:
        handle_send(client_socket, "系统错误，请稍后再试")
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE customers_table SET name = %s WHERE name = %s", (new_name, name))
            conn.commit()  # 提交更改
            cursor.execute("SELECT name FROM customers_table WHERE name = %s", (new_name,))
            handle_send(client_socket, f'修改成功,当前账号名称:{new_name}.\n'
                                       f'请继续选择您要增删改查的类型：客户(输入1),房间(输入2),退出(输入0):)')
            while True:
                # subordinate adj.从属的,次要的,下级的
                choice = handle_receive(client_socket).strip()
                if choice == '0':
                    input_0(client_socket)
                    return
                elif choice == '1':
                    crud_1(client_socket)
                    break
                elif choice == '2':
                    crud_2(client_socket)
                    break
    except pymysql.Error as e:
        conn.rollback()
        print(f'修改账号错误:{e}')
        handle_send(client_socket, "修改账号失败,请稍后再试")
    finally:
        conn.close()
def m1_2(client_socket, name):#修改余额
    handle_send(client_socket,"请输入更改后的金额,整数部分不超过18位,小数部分不超过2位:")
    amount_str = handle_receive(client_socket)
    conn = create_db_connection()
    try:
        #正则验证金额格式
        if not re.match(r'^\d+(\.\d{1,2})?$', amount_str):
            handle_send(client_socket,"金额格式无效（示例：100.50）,请重新选择您要修改的这位客户的内容(1修改账号，2修改余额，3注销):")
            choice = handle_receive(client_socket)
            handle_crud1(choice, client_socket, name)
        float(amount_str)
        amount = float(amount_str)
        with conn.cursor() as cursor:
            cursor.execute("UPDATE customers_table SET balance = %s WHERE name = %s",(amount, name))
            cursor.execute("SELECT balance FROM customers_table WHERE name = %s",(name,))
            new_balance = cursor.fetchone()[0]
            conn.commit()
            handle_send(client_socket, f'修改成功。当前余额：{new_balance}元.\n请继续选择您要增删改查的类型：客户(输入1),房间(输入2),退出(输入0):)')
            while True:
                # subordinate adj.从属的,次要的,下级的
                choice = handle_receive(client_socket).strip()
                if choice == '0':
                    input_0(client_socket)
                    return
                elif choice == '1':
                    crud_1(client_socket)
                    break
                elif choice == '2':
                    crud_2(client_socket)
                    break
    except (ValueError,pymysql.Error) as e:
        conn.rollback()
        print(f"修改余额错误: {e}")
        handle_send(client_socket, "修改余额失败，请稍后再试")
    finally:
        conn.close()
def m1_3(client_socket):#注销账号
    handle_send(client_socket, "请输入您要注销的账号,确认再回车:")
    name = handle_receive(client_socket)
    conn = create_db_connection()
    if conn is None:
        handle_send(client_socket, "系统错误，请稍后再试")
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT name FROM customers_table WHERE name = %s", (name,))
            if cursor.fetchone():
                cursor.execute("DELETE FROM customers_table WHERE name = %s", (name,))
                conn.commit()  # 提交更改
                handle_send(client_socket, f'注销成功.')
                choice = handle_receive(client_socket)
            else:
                handle_send(client_socket,"该客户不存在,请重新输入管理员权限操作数:")
        handle_crud1(choice, client_socket, name)
    except pymysql.Error as e:
        conn.rollback()
        print(f'注销账号错误:{e}')
        handle_send(client_socket, "注销账号失败,请稍后再试")
    finally:
        conn.close()

def crud_2(client_socket):
    handle_send(client_socket, "房间置空1,无理由占房2,增加新房间3,减少可租房间4,退出0.\n请输入选择:")
    choice = handle_receive(client_socket)
    try:
            handle_crud2(choice, client_socket, "")
    except Exception as e:
        print(f"crud_2()错误:{e}")
        handle_send(client_socket, f"crud_2()错误:{e}")
def m2_1(client_socket):#房间置空
    handle_send(client_socket, "请输入您要置空的房间:")
    room = handle_receive(client_socket)
    conn = create_db_connection()
    if conn is None:
        handle_send(client_socket, "系统错误,请稍后再试")
        return
    try:
        with conn.cursor() as cursor:
            #查询该房间是否被该用户租用
            cursor.execute("SELECT room_number FROM rooms_table WHERE room_number = %s AND status = 'occupied'",(room,))
            result = cursor.fetchone()
            #如果结果是没有
            if not result:
                handle_send(client_socket, "该房间未被租用或不存在.请重新选择您要对房间进行的操作:(房间置空1,无理由占房2,增加新房间3,减少可租房间4,返回0):")
                choice = handle_receive(client_socket)
                handle_crud2(choice, client_socket, name)
                return
            #如果确有此事
            cursor.execute("UPDATE rooms_table SET status='vacant', customer_name=NULL WHERE room_number=%s", (room,))
            conn.commit()
            handle_send(client_socket, "置空房间成功.请继续选择您要增删改查的类型：客户(输入1),房间(输入2),退出(输入0):")
            while True:
                # subordinate adj.从属的,次要的,下级的
                choice = handle_receive(client_socket).strip()
                if choice == '0':
                    input_0(client_socket)
                    return
                elif choice == '1':
                    crud_1(client_socket)
                    break
                elif choice == '2':
                    crud_2(client_socket)
                    break
    except pymysql.Error as e:
        conn.rollback()
        print(f"置空房间错误:{e}")
        handle_send(client_socket, "置空房间失败,请稍后再试")
    finally:
        conn.close()
def m2_2(client_socket):#无理由占房
    handle_send(client_socket, "请输入您要占用的房间:")
    room = handle_receive(client_socket)
    conn = create_db_connection()
    if conn is None:
        handle_send(client_socket, "系统错误,请稍后再试")
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT status FROM rooms_table WHERE room_number = %s",(room,))
            room_status = cursor.fetchone()
            if (not room_status) or room_status[0] != 'vacant':
                handle_send(client_socket, "该房间已被租用或不存在,请重新输入head操作数:")
                return
            cursor.execute("UPDATE rooms_table SET status = 'occupied', customer_name = 'manager' WHERE room_number = %s",(room,))
            conn.commit()
            handle_send(client_socket, "占用房间成功.请继续选择您要增删改查的类型：客户(输入1),房间(输入2),退出(输入0):")
            while True:
                # subordinate adj.从属的,次要的,下级的
                choice = handle_receive(client_socket).strip()
                if choice == '0':
                    input_0(client_socket)
                    return
                elif choice == '1':
                    crud_1(client_socket)
                    break
                elif choice == '2':
                    crud_2(client_socket)
                    break
    except pymysql.Error as e:
        conn.rollback()
        print(f"占用房间错误:{e}")
        handle_send(client_socket, "占用房间失败,请稍后再试")
    finally:
        conn.close()
def m2_3(client_socket, name):#增加新可租房间
    handle_send(client_socket, "请输入您要增加的新房间,如有多个用空格隔开:")
    rooms = handle_receive(client_socket).split()
    conn = create_db_connection()
    if not conn:
        handle_send(client_socket, "在m2_3发生系统错误")
        return
    try:
        with conn.cursor() as cursor:
            for room in rooms:
                if not re.match(r'^\d{3}$', room):  # 房间号格式验证
                    handle_send(client_socket, f"{room}房间号格式无效")
                    continue
                cursor.execute("INSERT INTO rooms_table (room_number,status) VALUES (%s,'vacant')", (room,))
                handle_send(client_socket, f"成功添加房间：{room}\n")
            conn.commit()
            handle_send(client_socket, "请继续选择您要增删改查的类型：客户(输入1),房间(输入2),退出(输入0):")
            while True:
                # subordinate adj.从属的,次要的,下级的
                choice = handle_receive(client_socket).strip()
                if choice == '0':
                    input_0(client_socket)
                    return
                elif choice == '1':
                    crud_1(client_socket)
                    break
                elif choice == '2':
                    crud_2(client_socket)
                    break
    except pymysql.Error as e:
        conn.rollback()
        handle_send(client_socket, f"添加失败：{e},自动退出")
    except ValueError as ve:
        handle_send(client_socket, f"输入错误：{ve},自动退出")
    finally:
        conn.close()
def m2_4(client_socket):#减少可租房间
    handle_send(client_socket, "请输入不出租的房间,如有多个用空格隔开:")
    room_str = handle_receive(client_socket)
    # new_room_list = []
    # for room in room_str.split():#以空格为分隔符
    #     for char in room:
    #         new_room_list.append(char)

    #直接使用去空格法
    new_room_list = room_str.split()

    conn = create_db_connection()
    if conn is None:
        handle_send(client_socket, "系统错误,请稍后再试")
        return
    try:
        with conn.cursor() as cursor:
            for room in new_room_list:#删除
                cursor.execute("SELECT room_number FROM rooms_table WHERE room_number = %s",(room,))
                room_ = cursor.fetchone()
                if (not room_):
                    handle_send(client_socket, f"该房间列表中,{room}不存在.")
                cursor.execute("DELETE FROM rooms_table WHERE room_number = %s",(room,))
            conn.commit()
            cursor.execute("SELECT room_number FROM rooms_table ")
            rooms = [row[0] for row in cursor.fetchall()]
            send_list = f'操作结束,现在可租房间有{rooms},'
            cursor.execute("SELECT room_number FROM rooms_table WHERE status = 'vacant'")
            vacant_rooms = [row[0] for row in cursor.fetchall()]
            send_list += f'空闲房间有{vacant_rooms},请重新输入head操作数:'
            handle_send(client_socket, send_list)
    except pymysql.Error as e:
        print(f"减少房间错误:{e}")
        handle_send(client_socket, "减少房间失败")
    finally:
        conn.close()

# crud_1()内部选项:1修改账号，2修改余额，3注销
def handle_crud1(choice,client_socket, name):
    switch = {
        '0':lambda:input_0(client_socket),
        '1':lambda: m1_1(client_socket,name),
        '2':lambda: m1_2(client_socket, name),
        '3':lambda: m1_3(client_socket),
    }
    func = switch.get(choice,lambda:handle_send(client_socket, "无效的选项，请重新选择head_choice:") )
    func()

def handle_crud2(choice,client_socket, name):
    switch = {
        '0':lambda:input_0(client_socket),
        '1':lambda: m2_1(client_socket),
        '2':lambda: m2_2(client_socket),
        '3':lambda: m2_3(client_socket, name),
        '4':lambda: m2_4(client_socket),
    }
    func = switch.get(choice,lambda:handle_send(client_socket, "无效的选项，请重新输入:") )
    func()

def handle_manager_body_choice(choice, client_socket):
    switch = {
        '0':lambda:input_0(client_socket),
        '1':lambda: crud_1(client_socket),
        '2':lambda: crud_2(client_socket),
    }
    func = switch.get(choice,lambda: handle_send(client_socket,"无效的选项，请重新输入:"))
    func()

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
    conn = create_db_connection()
    if conn is None:
        handle_send(client_socket, "系统错误,请稍后再试")
        return
    try:
        conn.begin()
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
                        #############################################
                        return
                    handle_body_choice(choice,client_socket, name)
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
                    "\t\t1登录\n\t\t2注册\n\t\t0退出\n\t\t9管理员\n或输入 exit 强制断开连接.\n"+26*"*"+
                    "\n请输入操作数:")
        while True:
            choice = handle_receive(client_socket).strip()
            if choice is None:
                print("客户断开连接")
                break
            elif choice == '1':
                handle_login(client_socket)
            elif choice == '2':
                handle_register(client_socket)
            elif choice == '0':
                input_0(client_socket)
            elif choice == '9':
                input_9(client_socket)
            else:
                handle_send(client_socket, "无效的head_choice,请重新输入.")
    except Exception as e:
        print(f"handle_client()出错:{e}")
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
