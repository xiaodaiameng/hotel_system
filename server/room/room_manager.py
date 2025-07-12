import re

import pymysql

from hotel_system.server.core.database import db_connection_handler
from hotel_system.server.core.network import handle_send, handle_receive, close_connection


def handle_room_management(client_socket):
    """管理员对房间的管理"""
    while True:
        menu = """
        房间管理:
        11.查询空闲房间
        1. 房间置空
        2. 占用房间
        3. 添加房间
        4. 移除房间
        0. 退出
        请输入选择: """
        handle_send(client_socket, menu)
        choice = handle_receive(client_socket)
        if not choice or choice == '0':
            close_connection(client_socket)
            break
        elif choice == '11': #查询空闲房间
            RoomManager.get_vacant_rooms(client_socket)
            return True
        elif choice == '1':  #房间置空
                RoomManager.empty_room(client_socket)
                return True
        elif choice == '2':  #占用房间
                RoomManager.occupy_room(client_socket)
                return True
        elif choice == '3':  #添加房间
            RoomManager.add_room(client_socket)
            return True
        elif choice == '4':  #移除房间
            RoomManager.reduce_room(client_socket)
            return True
        else:
            handle_send(client_socket, "无效的选择.请重新输入:")

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
                return True
        except pymysql.Error as e:
            handle_send(client_socket,f"查询空闲房间错误:{e}")
            return False
    @staticmethod
    @db_connection_handler
    def empty_room(client_socket,conn=None):  #房间置空
        handle_send(client_socket, "请输入您要置空的房间:")
        room = handle_receive(client_socket).strip()
        if not re.match(r'^\d{3}$', room):
            handle_send(client_socket,"房间号必须是3位数字。")
            return False
        try:
            with conn.cursor() as cursor:
                # 查询该房间是否被该用户租用
                cursor.execute("SELECT room_number FROM rooms_table WHERE room_number = %s AND status = 'occupied'",(room,))
                result = cursor.fetchone()
                if not result:
                    handle_send(client_socket,"该房间未被租用或不存在.")
                    return False
                cursor.execute("UPDATE rooms_table SET status='vacant', customer_name=NULL WHERE room_number=%s",(room,))
                conn.commit()
                handle_send(client_socket,"置空房间成功.")
                return True
        except pymysql.Error as e:
            conn.rollback()
            handle_send(client_socket, f"置空房间错误:{e}")
            return False
    @staticmethod
    @db_connection_handler
    def occupy_room(client_socket,conn=None):
        handle_send(client_socket, "请输入要占用的房间号:")
        room_number = handle_receive(client_socket)
        if not re.match(r'^\d{3}$', room_number):
            handle_send(client_socket,"房间号必须是3位数字。")
            return False
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
    def add_room(client_socket,conn=None):#增加新可租房间
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
    def reduce_room(client_socket,conn):#减少可租房间
        handle_send(client_socket, "请输入不出租的房间(每次输入一个):")
        room_str = handle_receive(client_socket).strip()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT room_number FROM rooms_table WHERE room_number = %s",(room_str,))
                room_ = cursor.fetchone()
                if not room_:
                    handle_send(client_socket, f"抱歉,该房间列表中,{room_str}不存在.")
                cursor.execute("DELETE FROM rooms_table WHERE room_number = %s",(room_str,))
                conn.commit()
                cursor.execute("SELECT room_number FROM rooms_table ")
                rooms = [row[0] for row in cursor.fetchall()]
                send_list = f'操作结束,现在可租房间有{rooms}'
                handle_send(client_socket, send_list)
                return True
        except pymysql.Error as e:
            handle_send(client_socket, f"减少房间错误:{e}")
            return False
