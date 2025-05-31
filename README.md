[关于代码的简单说明.md](https://github.com/user-attachments/files/20367364/default.md)展开如下:
# [旅店管理系统] 代码说明

<img src="README相关图片\logo_1.png" alt="image-20250521092613420" style="zoom: 50%;" /><img src="README相关图片\logo_2.png" alt="image-20250521092728886" style="zoom: 50%;" /><img src="README相关图片\logo_3.png" alt="image-20250521093128548" style="zoom: 50%;" />

## 一 .项目概述

该项目旨在管理旅店信息,应用于实际生活.

## 二.功能列表

- [x] 管理员能够对客户或房间分别进行增删改查

- [x] 客户能够查询空房,订房,退房,充值金额,查询余额

##  三.安装指南

### 1,PyCharm

浏览器搜索PyCharm,进入网站,选择PyCharm社区版,无脑式安装.

### 2,MySQL

1. 请进入B站,观看并跟着该up主的两集视频进行操作.(高质量教程)

观看教程后,即可学会建库,建表.

<img src="README相关图片\安装指南_1.jpg" alt="安装指南_1" style="zoom:5%;" /><img src="README相关图片\安装指南_2.jpg" alt="安装指南_2" style="zoom:5%;" />

2. 以下是需要建立的库(library)和表(table):

- 注意:创建表可以在命令行启动数据库后输入代码创建,也可以在数据库软件本身提供的图形化界面点击与勾选,就是以下流程.建立过程中如果有apply选项就都要点击,是保存的意思.

(1)<img src="README相关图片\数据库图形化界面相关_1.png" alt="image-20250520022041318" style="zoom: 80%;" />

(2)<img src="README相关图片\屏幕截图 2025-05-31 120621.png" alt="image-20250520022120328" style="zoom: 50%;" />

(3)<img src="README相关图片\_3.png" alt="image-20250520022351949" style="zoom: 50%;" />

(4)<img src="README相关图片\_4.png" alt="image-20250520022429422" style="zoom: 50%;" />

3. 接着 切换模式(定义表格式/写入数据到表):

把光标移动在customers_table,各个table处, 就能看见扳手和正方形表格图标(忘记拉取图片了,此处没有示例图片):

点击正方形图标, 开始各个表内的数据初始化:

(1)<img src="README相关图片\_5.png" alt="image-20250520022728495" style="zoom:50%;" />

(2)<img src="README相关图片\_6.png" alt="image-20250520022742997" style="zoom:50%;" />

(3)<img src="README相关图片\_7.png" alt="image-20250520022754092" style="zoom:50%;" />

## 四.使用说明

### 代码运行前:

1. 

- 需要保证客户端端口号是各自主机的ipv4地址(多个客户端),若要运行请在客户端代码修改地址,而服务端的端口号是0.0.0.0,不用修改,表示服务端可以接受多个主机的连接.

2. 

- 需要保证mysql中已经创建了需要的表,
- 需要在命令行中启动数据库,输入:   mysql -u root -p   (没有分号) 回车后提示输入密码   123456  再回车,出现此界面说明MySQL已在后台成功启动:
  <img src="README相关图片\命令行.png" alt="image-20250520221130512" style="zoom: 33%;" />

注意: 各不相同的本机MySQL用户设置的密码可能不一样

## 五.番外篇:

各位师兄师姐好!在爪哇社团本次考核中,本人收获了很多,非常荣幸.

### 1. 学到的比如:

- .strip()是把字符串的前后空格消除,

- .split()是把字符串以空格或制表符或回车为界转为列表元素

- 返回值有时候可以不返回,有时候可以返回空,有时候需要return True或return False,因为代码中有函数的多次嵌套和循环

- 错误处理应严谨   例(片段):

```python
except Exception as e:
    print(f"处理客户端出错: {e}")
except ConnectionResetError:
    print("客户端强制断开")
finally:
    try:
        client_socket.shutdown(socket.SHUT_RDWR) 
    except OSError:
        pass
    client_socket.close()
    print("服务端已断开客户端连接")
```

### 2. 但是,存在的问题比如:

- 有时候连接真是个问题啊(还没学那么多,干笑.jpg),有关删除客户的数据库还没有完善. 此时代码已被提交,暂时不再修改.
- 此次代码没有使用哈希函数,因为当时使用时代码改来改去,迟迟不能认证成功,本人运行破防了,后面干脆删掉了.ai提示我哈希很重要,生产环境必须使用哈希（如bcrypt）+ 盐值加密,所以以后有心情就补进去.
- 学长建议的日志管理还没有实现,没有写入提交上来的代码里.(扶额苦哭.jpg)

### 3. 服务端代码大纲(共两页):

<img src="README相关图片\手写代码目录_1.jpg" alt="14330b0659717b17e40542bf20952c4" style="zoom: 25%;" />

---

<img src="README相关图片\手写代码目录第二页.jpg" alt="image-20250521190804881" style="zoom:25%;" />

---

## 谢谢观看.
