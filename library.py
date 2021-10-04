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
    抢座的微信通知key:ftkey=                  (没有就自己去https://sc.ftqq.com注册一个叭,不想每天收到通知提醒一下自己不香吗?) 
4.仅供学习和交流,禁止私自牟利
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
ftkey = 'ftkey'
# 通知url
FTkey = None  # your-FTkey
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

# 通知的api接口
FT = "https://sc.ftqq.com/%s.send" % FTkey
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
        # code 短信 电话通知选座成功
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36'
        }
        post_data = {
            'text': '图书馆占座成功通知',
            'desp': getTime() + " " + self.lib_name + self.seat + "占座成功"
        }
        requests.post(FT, params=post_data, headers=headers)

    # 抢座并通知
    def reserve_seat(self):
        global RUN
        global res_code
        global moment
        global selected
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
            with open('library.log', 'a+') as log_file:
                log_file.write(getTime() + " " + self.lib_name + self.seat + "占座成功\n")
            # 通知
            self.notify_lib()
        elif res['code'] == 1 and res['msg'] == '参数不正确':
            hex_dict[lib_id][seat_key] = ""
        elif res['code'] == 1 and res['msg'] == '选座中,请稍后':
            moment = True
        elif res['code'] == 1 and res['msg'] == '操作失败, 您已经预定了座位!':
            selected = True


def check_conf(temp_conf):
    conf_list = [reserve, user_login, lib, seat, seat_random, prems, ftkey]
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
    global RUN, url_login_url, seat_dict, ran, preMs, FTkey
    RUN = conf.get(LIBRARY, reserve)
    url_login_url = conf.get(LIBRARY, user_login)
    temp_lib_name = conf.get(LIBRARY, lib)
    temp_seat_list = conf.get(LIBRARY, seat).split(',')
    seat_dict[temp_lib_name] = temp_seat_list
    ran = conf.get(LIBRARY, seat_random)
    preMs = conf.get(LIBRARY, prems)
    FTkey = conf.get(LIBRARY, ftkey)


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
        print(url_hex_lib)
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
    m = int(datetime.datetime.now().strftime('%M'))
    # 秒
    s = int(datetime.datetime.now().strftime('%S'))
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
read_conf(conf)
# print(RUN, url_login_url, seat_dict, ran, preMs, FTkey)
select_seat_dict = init_seat_dict(seat_dict, ran)
init_hex_dict()
# 程序休眠到抢座开始的preMs时刻
# login()
sleep_to_time()
start_time = time.time()
# RUN = False
while RUN and not selected:
    end_time = time.time()
    if end_time - start_time < 180:
        if moment:
            time.sleep(1)
        for lib_id in select_seat_dict:
            if selected:
                break
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
    with open('library.log', 'a+', encoding='utf-8') as log_file:
        log_file.seek(0, 0)
        if selected:
            log_file.write(nowtime + "占座失败,已占座\n")
        else:
            log_file.write(nowtime + "占座失败\n")
print('--------------prepare for tomorrow---------------')
