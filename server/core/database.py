"""我叫模块注释，该文件包括了数据库初始化函数，用于数据库连接的装饰器函数"""

import pymysql
from functools import wraps #多次连接数据库，使用装饰器


DB_CONFIG = {
    'host':'localhost','user':'root','password':'123456',
    'database':'hoteldatabase','charset':'utf8mb4'
}#数据库配置常量

def db_connection_handler(func):
    """定义数据库连接装饰器,自动管理连接"""
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

@db_connection_handler
def init_database(conn = None):
    """数据库初始化"""
    try:
        with conn.cursor() as cursor:
            conn.begin()
            #一个是管理员表managers_table,包括了id,管理员名称及密码共三列
            cursor.execute("""CREATE TABLE IF NOT EXISTS managers_table (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(60) NOT NULL)""")
            #一个是用户表customers_table,里面有id,用户名name,余额balance,is_deleted共四列
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
                                check_in_time DATETIME DEFAULT NULL,
                                duration_days INT DEFAULT 1,
                                FOREIGN KEY (customer_name) REFERENCES customers_table(name) ON DELETE SET NULL)""")
            #初始化:管理员密码
            cursor.execute("SELECT COUNT(*) FROM managers_table")
            if cursor.fetchone()[0] == 0:
                pwd = "ok"
                cursor.execute("INSERT INTO managers_table (username, password) VALUES (%s, %s)", ('管理员', pwd))
            #初始化:有两个用户
            cursor.execute("SELECT COUNT(*) FROM customers_table")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO customers_table (name, balance) VALUES (%s, %s)", ('张三',300))
                cursor.execute("INSERT INTO customers_table (name, balance) VALUES (%s, %s)", ('李四',400))
            #初始化:有5个房间
            cursor.execute("SELECT COUNT(*) FROM rooms_table")
            room_count = cursor.fetchone()[0]
            if room_count == 0:
                rooms = ['201', '202', '203', '204', '205']
                cursor.executemany("INSERT INTO rooms_table (room_number, status) VALUES (%s, 'vacant')",[(r,) for r in rooms])
                conn.commit()
            return True
    except pymysql.Error as e:
        conn.rollback()
        print(f"数据库初始化错误:{e}")
        return False
    except Exception as e:
        conn.rollback()
        print(f"数据库初始化出现未知错误: {e}")
        return False


