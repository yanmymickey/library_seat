# -*- coding: utf-8 -*
import random
import urllib.request
import http.cookiejar
import json
import re
import execjs
import time
import requests
import datetime
import threading
from xtulib import library, classroom
import argparse
import configparser
from os import path, makedirs

'''
使用说明：
1.不用改脚本，通过修改配置文件修改脚本参数
2.配置文件在conf文件夹下面,文件名以ini结尾就行,其他随意
3.参数说明：
    配置文件头: [LIBRARY]                   必需,复制粘贴到第一行,下列参数顺序无所谓
    是否抢座位: reserve=True                (True代表抢,否则就否则) 
    用户登录url:user_login=http://.......   (抓xd校园的包,提取链接,类似http://wechat.v2.traceint.com/index.php/schoolpushh5/registerLogin?sch_id=)
    抢座的图书馆:lib=南204中文图书借阅一厅(2楼)  (查看xtulib.py中lib_name_dict的名称,复制粘贴,不要自己打)
    抢座的位置:seat=1,2,3,4,5                (要占座的位置列表,随便写几个自己喜欢的) 
    抢座要不要随机:seat_random=True           (True就每天随机,从自己的填的座位里面优先抢,理论上可以达到每天换着坐的目的,否则就否则) 
    抢座提前的秒数:prems=0.1                  (可以自己尝试改,不改也挺好用) 
    抢座通知配置:user_id=                     (推送消息发送user_id)
    抢座通知配置:appid=1                      (企业微信的appid)
    抢座通知配置:token=                       (调用接口用的access_token)
4.仅供学习和交流,禁止私自牟利
建立log目录用于存放日志
5.脚本运行是运行library.sh
6.配置一个每天7点20的crontab定时任务,挂服务器上就大功告成了
7.考研人加油叭
'''

# 配置文件名称项
LIBRARY = 'LIBRARY'
reserve = 'reserve'
user_login = 'user_login'
lib = 'lib'
seat = 'seat'
seat_random = 'random'
prems = 'prems'
user = 'user'
app_id = 'app_id'
token = 'token'
user_id = 'user_id'
# 通知配置
touser = "@all"
agentId = None
access_token = None
# 抓湘大校园的包,提取链接类似http://wechat.v2.traceint.com/index.php/schoolpushh5/registerLogin?sch_id=
url_login_url = None
# 要占座的座位列表
seat_dict = {}
# 提前多少秒开抢 支持三位小数
preMs = 0.1
# 是否抢位置
RUN = True
# 是否随机位置,每天不在一个位置
ran = False
# 用户名称
user_name = 'test'
# 通知的api接口
# 默认的抢座列表
default_seat = {"南204中文图书借阅一厅(2楼)": [1, 2, 3, 4, 5, 6, 7, 8]}
# 抢座链接 根据lib_id YsjhY856两个参数确定座位
url_submit = 'http://wechat.v2.traceint.com/index.php/reserve/get/'
# 带有生成参数的js文件链接的页面链接
url_hex = "http://wechat.v2.traceint.com/index.php/reserve/layout/libid=%s.html"

# 状态
res_code = 1
moment = False
selected = False
# 构建一个CookieJar对象实例来保存cookie
cookiejar = http.cookiejar.CookieJar()
handler = urllib.request.HTTPCookieProcessor(cookiejar)
opener = urllib.request.build_opener(handler)
# 保存线程的列表
thread_id = 0
thread_list = []
# 保存hexcode
hex_dict = {}
select_seat_dict = {}


class seat_Thread(threading.Thread):
    def __init__(self, thread_id, lib_id, seat_key, hexCode):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.lib_id = lib_id
        self.seat_key = seat_key
        self.lib_name = ""
        self.seat = ""
        self.hexCode = hexCode

    def run(self):
        self.getlib()
        print("当前工作的线程为：", self.thread_id, " 正在尝试: ", self.lib_name, " 座位号: ", self.seat, "\n", end='')
        print("reserve_seat_start", "\n", end='')
        self.reserve_seat()
        print("reserve_seat_end", "\n", end='')
        print(self.thread_id, " 线程已退出\n", end='')

    def getlib(self):
        # 获取图书馆名称和座位号
        lib = library[self.lib_id]
        self.lib_name = str(list(lib.keys())[0])
        self.seat = str(lib[self.lib_name][self.seat_key])

    # 抢座通知
    def notify_lib(self):
        text = '图书馆占座成功通知'
        desp = getTime() + " " + self.lib_name + self.seat + "占座成功"
        notify_wechat(text, desp)

    # 抢座并通知
    def reserve_seat(self):
        global RUN, res_code, moment, selected, select_seat_dict
        if not RUN:
            return
        res_html = opener.open(url_submit + self.hexCode).read().decode('utf-8')
        # print(url_submit + self.hexCode)
        res = json.loads(res_html)
        print(res, "\n", end='')
        if res['code'] == 0:
            RUN = False
            res_code = 0
            # 写入日志
            content = getTime() + " " + self.lib_name + self.seat + "占座成功\n"
            write_log(content)
            # 通知
            self.notify_lib()
        elif res['code'] == 1 and res['msg'] == '参数不正确':
            hex_dict[lib_id][seat_key] = ""
        elif res['code'] == 1 and res['msg'] == '选座中,请稍后':
            moment = True
        elif res['code'] == 1 and res['msg'] == '操作失败, 您已经预定了座位!':
            selected = True
        elif res['code'] == 1 and res['msg'] == '该座位已经被人预定了!':
            if self.seat_key in select_seat_dict[self.lib_id]:
                select_seat_dict[self.lib_id].remove(self.seat_key)


def write_log(content):
    # 创建图片和日志路径
    log_path = 'log/'
    if not path.exists(log_path):
        makedirs(log_path)
    with open(log_path + 'library.log', 'a+', encoding='utf-8') as log_file:
        log_file.seek(0, 0)
        log_file.write(content)


# 微信通知
def notify_wechat(text, desp):
    send_msg_url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}'
    data = {
        "touser": touser,
        "agentid": agentId,
        "msgtype": "textcard",
        "textcard": {
            "title": user_name + " " + text,
            "description": user_name + " " + desp,
            "url": user_login,
            "btntxt": "更多"
        },
        "duplicate_check_interval": 600
    }
    requests.post(send_msg_url, data=json.dumps(data))


def check_conf(temp_conf):
    conf_list = [reserve, user_login, lib, seat, seat_random, prems, token, app_id, user, user_id]
    conf_list.sort()
    temp_conf.sort()
    return conf_list == temp_conf


def get_args():
    parser = argparse.ArgumentParser(description='Test for argparse')
    parser.add_argument('--conf', '-c', help='用户文件配置文件路径,必要参数', required=True)
    args = parser.parse_args()
    conf_path = args.conf
    return conf_path


def read_conf(conf):
    global RUN, url_login_url, seat_dict, ran, preMs, user_name, touser, access_token, agentId
    user_name = conf.get(LIBRARY, user)
    RUN = conf.getboolean(LIBRARY, reserve)
    url_login_url = conf.get(LIBRARY, user_login)
    temp_lib_name = conf.get(LIBRARY, lib)
    temp_seat_list = conf.get(LIBRARY, seat).split(',')
    seat_dict[temp_lib_name] = temp_seat_list
    ran = conf.getboolean(LIBRARY, seat_random)
    preMs = conf.getfloat(LIBRARY, prems)
    touser = conf.get(LIBRARY, user_id)
    access_token = conf.get(LIBRARY, token)
    agentId = conf.get(LIBRARY, app_id)


def get_temp_seat(seat_dict, ran):
    temp_seat_dict = {}
    for lib_name, seat_list in seat_dict.items():
        print(lib_name, " 座位号: ", end='')
        lib = classroom[lib_name]
        lib_id = str(list(lib.keys())[0])
        seat_key_list = []
        if ran:
            random.shuffle(seat_list)
        for seat_num in seat_list:
            seat_num = str(seat_num)
            print(seat_num, " ", end='')
            seat_key = classroom[lib_name][lib_id][seat_num]
            seat_key_list.append(seat_key)
        temp_seat_dict[lib_id] = seat_key_list
    return temp_seat_dict


def init_seat_dict(seat_dict=None, ran=False):
    if not seat_dict:
        print('--------------未选择座位,将使用默认座位-----------')
        seat_dict = default_seat
    print('--------本次选择座位列表---------')
    temp_seat_dict = get_temp_seat(seat_dict, ran)
    return temp_seat_dict


# 刷新hexCode
def fresh_hex(lib_id, seat_key):
    global selected
    js_url = []
    while not js_url:
        url_hex_lib = url_hex % lib_id
        res = opener.open(url_hex_lib).read().decode('utf-8')
        if '签到' in res:
            selected = True
            break
        js_url = re.findall('ache/layout/(.*).js"></script>', res)
        time.sleep(0.01)
    if selected:
        return
    js_url = "https://static.wechat.v2.traceint.com/template/theme2/cache/layout/" + js_url[0] + ".js"
    # 根据链接获取js文件
    js = opener.open(js_url).read().decode('utf-8')
    # 修改js函数
    js = js.replace("T.ajax_get(AJAX_URL+", "return ")
    js = js.replace("+\"&yzm=\"", ";};/*")
    js = js.replace("msg)})};", "*/")
    # 执行选座函数获取选座参数
    js_obj = execjs.compile(js)
    hexCode = js_obj.call("reserve_seat", lib_id, seat_key)
    hex_dict[lib_id][seat_key] = hexCode


def getTime():
    now_timeformat = '%Y-%m-%d %H:%M'
    submit_time = datetime.datetime.now().strftime(now_timeformat)
    return submit_time


# 以get方法访问登录链接，访问之后会自动保存cookie到cookiejar中
def login():
    opener.open(url_login_url)


def init_hex_dict():
    for lib_id in select_seat_dict:
        seat_dict = {}
        for seat_key in select_seat_dict[lib_id]:
            seat_dict[seat_key] = ""
            hex_dict[lib_id] = seat_dict


def sleep_to_time():
    # 分
    h = int(datetime.datetime.now().strftime('%H'))
    # 分
    m = int(datetime.datetime.now().strftime('%M'))
    # 秒
    s = int(datetime.datetime.now().strftime('%S'))
    if m < 29 and h == 7:
        time.sleep(60 * 29 - 60 * m - s)
    login()
    s = int(datetime.datetime.now().strftime('%S'))
    time.sleep(57 - s)
    s = int(datetime.datetime.now().strftime('%S'))
    ms = time.time()
    ms = int((ms - int(ms)) * 1000) / 1000
    time.sleep(60 - s - ms - preMs)


print("--------------begin reserve seat---------------")
conf = configparser.RawConfigParser()
conf_path = get_args()
# print(conf_path)
conf.read(conf_path, encoding='utf-8-sig')
if LIBRARY not in conf.sections():
    print('-------配置文件格式错误------')
    exit()
conf_options_list = list(conf.options(LIBRARY))
if not check_conf(conf_options_list):
    print('-------配置文件格式错误------')
    exit()
# 读取配置文件
read_conf(conf)
start_text = "脚本开始运行"
start_desp = getTime() + "脚本开始运行"
notify_wechat(start_text, start_desp)
select_seat_dict = init_seat_dict(seat_dict, ran)
init_hex_dict()
# 程序休眠到抢座开始的preMs时刻
# login()
sleep_to_time()
start_time = time.time()
count_empty_seat = 0
# if not RUN:
#     print(RUN)
# RUN = False
while RUN and not selected:
    end_time = time.time()
    if end_time - start_time < 180:
        if moment:
            time.sleep(1)
        for lib_id in select_seat_dict:
            if selected:
                break
            if not select_seat_dict[lib_id]:
                count_empty_seat += 1
                continue
            for seat_key in select_seat_dict[lib_id]:
                if hex_dict[lib_id][seat_key] == "":
                    fresh_hex(lib_id, seat_key)
                if not selected:
                    hexCode = hex_dict[lib_id][seat_key]
                    mythread = seat_Thread(thread_id, lib_id, seat_key, hexCode)
                    mythread.start()
                    thread_list.append(mythread)
                    thread_id += 1
                else:
                    break
    else:
        RUN = False
for t in thread_list:
    t.join()
if res_code == 1:
    res_code = 0
    nowtime = getTime()
    content = None
    if selected:
        content = nowtime + "占座失败,已占座\n"
    elif count_empty_seat == len(select_seat_dict.keys()):
        content = nowtime + "占座失败,选的所有位置都被抢了\n"
    else:
        content = nowtime + "占座失败\n"
    write_log(content)
    failure_text = "图书馆占座失败通知"
    notify_wechat(failure_text, content)
print('--------------prepare for tomorrow---------------')
