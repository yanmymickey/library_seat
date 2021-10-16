# -*- coding: utf-8 -*
import configparser
import re
import threading
import time
import execjs
import redis
from library_util.tool import *
from library_util.xtulib import library

'''
使用说明：
1.不用改脚本，通过修改配置文件修改脚本参数
2.配置文件在conf文件夹下面,文件名以ini结尾就行,其他随意
3.参数说明：
    配置文件头: [LIBRARY]                                               必需,复制粘贴到第一行,下列参数顺序无所谓
    是否抢座位: reserve=True                                           (True代表抢,否则就否则) 
    用户登录url:user_login=http://.......                              (抓xd校园的包,提取链接,类似http://wechat.v2.traceint.com/index.php/schoolpushh5/registerLogin?sch_id=)
    抢座的图书馆:lib=["南204中文图书借阅一厅(2楼)","南701外文图书借阅厅(7楼)"] (查看xtulib.py中lib_name_dict的名称,复制粘贴,不要自己打)
    抢座的位置:seat=[[1,2,3,4,5],[1,2,3,4,5]]                          (要占座的位置列表,随便写几个自己喜欢的) 
    抢座要不要随机:seat_random=True                                     (True就每天随机,从自己的填的座位里面优先抢,理论上可以达到每天换着坐的目的,否则就否则) 
    抢座提前的秒数:prems=0.1                                            (可以自己尝试改,不改也挺好用) 
    抢座通知配置:user_id=                                               (推送消息发送user_id)
    抢座通知配置:appid=1                                                (企业微信的appid)
    抢座通知配置:company_id=                                            (公司id,用于获取access_token)
    抢座通知配置:company_secret=                                        (应用secret,用于获取access_token)
4.仅供学习和交流,禁止私自牟利
5.建立log目录用于存放日志
6.脚本运行是运行library.sh
7.配置一个每天7点20的crontab定时任务,挂服务器上就大功告成了
8.考研人加油叭
'''

# 状态
res_code = 1
moment = False
selected = False
REDIS_OPEN = True
isNotify = True

# 保存线程的列表
thread_id = 0
thread_list = []

# 保存hexcode
hex_dict = {}
select_seat_dict = {}


class SeatThread(threading.Thread):
    def __init__(self, temp_thread_id, temp_lib_id, temp_seat_key, temp_hex_code):
        threading.Thread.__init__(self)
        self.thread_id = temp_thread_id
        self.lib_id = temp_lib_id
        self.seat_key = temp_seat_key
        self.lib_name = ""
        self.seat = ""
        self.hexCode = temp_hex_code

    def run(self):
        self.getlib()
        print("当前工作的线程为：", self.thread_id, " 正在尝试: ", self.lib_name, " 座位号: ", self.seat, "\n", end='')
        print("--------------reserve_seat_start--------------", "\n", end='')
        self.reserve_seat()
        print("--------------reserve_seat_end--------------", "\n", end='')
        print("--------------", self.thread_id, " 线程已退出--------------\n", end='')

    def getlib(self):
        # 获取图书馆名称和座位号
        temp_lib = library[self.lib_id]
        self.lib_name = str(list(temp_lib.keys())[0])
        self.seat = str(temp_lib[self.lib_name][self.seat_key])

    # 抢座通知
    def notify_lib(self):
        text = '图书馆占座成功通知'
        desp = get_time() + "\n地点: " + self.lib_name + "\n座位号: " + self.seat + "\n占座成功"
        notify_wechat(text, desp, REDIS_OPEN, redis_conn, corpid, corpsecret)

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
            temp_content = get_time() + " " + self.lib_name + self.seat + "占座成功\n"
            write_log(temp_content)
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


# 微信通知
def notify_wechat(text, desp, temp_REDIS_OPEN, temp_redis_conn, temp_corpid, temp_corpsecret):
    if not isNotify:
        return
    access_token = get_token(temp_REDIS_OPEN, temp_redis_conn, temp_corpid, temp_corpsecret)
    if access_token and len(access_token) > 0:
        send_msg_url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}'
        data = {
            "touser": touser,
            "agentid": agentId,
            "msgtype": "textcard",
            "textcard": {
                "title": user_name + " " + text,
                "description": user_name + "\n" + desp,
                "url": login_url,
                "btntxt": "more"
            },
            "duplicate_check_interval": 600
        }
        requests.post(send_msg_url, data=json.dumps(data))


def read_conf(temp_conf):
    global RUN, login_url, seat_dict, ran, preMs, user_name, touser, agentId, corpid, corpsecret, isNotify
    user_name = temp_conf.get(LIBRARY, user)
    RUN = temp_conf.getboolean(LIBRARY, reserve)
    login_url = temp_conf.get(LIBRARY, user_login)
    ran = temp_conf.getboolean(LIBRARY, seat_random)
    preMs = temp_conf.getfloat(LIBRARY, prems)
    touser = temp_conf.get(LIBRARY, user_id)
    agentId = temp_conf.get(LIBRARY, app_id)
    corpid = temp_conf.get(LIBRARY, company_id)
    corpsecret = temp_conf.get(LIBRARY, company_secret)
    if not corpid or not corpsecret or not agentId:
        isNotify = False
        print("--------------没有提供完整的企业微信配置信息,将不会产生微信通知--------------")
    temp_lib_name_list = temp_conf.get(LIBRARY, lib)
    temp_seat_list = temp_conf.get(LIBRARY, seat)
    temp_lib_name_list = json.loads(temp_lib_name_list)
    temp_seat_list = json.loads(temp_seat_list)
    for temp_lib_name, temp_seat in zip(temp_lib_name_list, temp_seat_list):
        seat_dict[temp_lib_name] = temp_seat


def init_hex_dict():
    for temp_lib_id in select_seat_dict:
        temp_seat_dict = {}
        for temp_seat_key in select_seat_dict[temp_lib_id]:
            temp_seat_dict[temp_seat_key] = ""
            hex_dict[temp_lib_id] = temp_seat_dict


# 刷新hexCode
def fresh_hex(temp_lib_id, temp_seat_key):
    global selected
    js_url = []
    while not js_url:
        url_hex_lib = url_hex % temp_lib_id
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
    temp_hex_code = js_obj.call("reserve_seat", temp_lib_id, temp_seat_key)
    hex_dict[temp_lib_id][temp_seat_key] = temp_hex_code


# 以get方法访问登录链接，访问之后会自动保存cookie到cookiejar中
def login():
    if login_url != "":
        opener.open(login_url)


def sleep_to_time():
    # 分
    h = int(datetime.datetime.now().strftime('%H'))
    # 分
    m = int(datetime.datetime.now().strftime('%M'))
    # 秒
    s = int(datetime.datetime.now().strftime('%S'))
    if m < 29 and h == 7:
        time.sleep(60 * 29 - 60 * m - s)
    elif m < 59 and h == 5:
        time.sleep(60 * 59 - 60 * m - s)
    login()
    s = int(datetime.datetime.now().strftime('%S'))
    time.sleep(57 - s)
    s = int(datetime.datetime.now().strftime('%S'))
    ms = time.time()
    ms = int((ms - int(ms)) * 1000) / 1000
    time.sleep(60 - s - ms - preMs)


print("--------------begin reserve seat--------------")
if REDIS_OPEN:
    try:
        redis_conn = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
        redis_conn.ping()
    except Exception as e:
        REDIS_OPEN = False
        print(e)
        print("--------------未开启redis,不使用redis--------------")
conf = configparser.RawConfigParser()
conf_path = get_args()
conf.read(conf_path, encoding='utf-8-sig')
if LIBRARY not in conf.sections():
    print('--------------配置文件格式错误--------------')
    exit()
conf_options_list = list(conf.options(LIBRARY))
if not check_conf(conf_options_list):
    print('--------------配置文件格式错误--------------')
    exit()
# 读取配置文件
try:
    read_conf(conf)
except Exception as e:
    print('--------------读取配置' + conf_path + '文件失败,配置文件格式错误--------------')
    error_text = "脚本运行错误报告"
    error_desp = get_time() + "读取配置" + conf_path + "文件失败,配置文件格式错误"
    write_log(error_desp)
    notify_wechat(error_text, error_desp, REDIS_OPEN, redis_conn, corpid, corpsecret)
    exit(3)
if not RUN:
    exit()
start_text = "脚本开始运行"
start_desp = get_time() + "占座脚本开始运行"
notify_wechat(start_text, start_desp, REDIS_OPEN, redis_conn, corpid, corpsecret)
select_seat_dict = init_seat_dict(seat_dict, ran)
init_hex_dict()
# 程序休眠到抢座开始的preMs时刻
# login()
sleep_to_time()
start_time = time.time()
count_empty_seat = 0
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
                    mythread = SeatThread(thread_id, lib_id, seat_key, hexCode)
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
    nowtime = get_time()
    content = None
    if selected:
        content = nowtime + "占座失败,已占座\n"
    elif count_empty_seat == len(select_seat_dict.keys()):
        content = nowtime + "占座失败,选的所有位置都被抢了\n"
    else:
        content = nowtime + "占座失败\n"
    write_log(content)
    failure_text = "图书馆占座失败通知"
    notify_wechat(failure_text, content, REDIS_OPEN, redis_conn, corpid, corpsecret)
print('--------------prepare for tomorrow--------------')
