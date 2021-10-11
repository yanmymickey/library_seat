import configparser
import redis
import time
from util.tool import *

# 状态
res_code = 1
moment = False
selected = False
REDIS_OPEN = True
isNotify = True


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


# 以get方法访问登录链接，访问之后会自动保存cookie到cookiejar中
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


def get_time():
    now_timeformat = '%Y-%m-%d %H:%M:%S'
    submit_time = datetime.datetime.now().strftime(now_timeformat)
    return submit_time


def login():
    if login_url != "":
        opener.open(login_url)


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
    if not corpid or not corpsecret or not app_id:
        isNotify = False
        print("--------------没有提供完整的企业微信配置信息,将不会产生微信通知--------------")
    temp_lib_name_list = temp_conf.get(LIBRARY, lib)
    temp_seat_list = temp_conf.get(LIBRARY, seat)
    temp_lib_name_list = json.loads(temp_lib_name_list)
    temp_seat_list = json.loads(temp_seat_list)
    for temp_lib_name, temp_seat in zip(temp_lib_name_list, temp_seat_list):
        seat_dict[temp_lib_name] = temp_seat


print("--------------begin cancel seat--------------")
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
start_text = "脚本开始运行"
start_desp = get_time() + "脚本开始运行"
notify_wechat(start_text, start_desp, REDIS_OPEN, redis_conn, corpid, corpsecret)
