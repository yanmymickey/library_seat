# library_seat使用指南

## 使用说明：

- 不用改脚本，通过修改配置文件修改脚本参数

- 配置文件在conf文件夹下面,文件名以ini结尾就行,其他随意

- 配置文件参数说明：

  | 配置文件头        | [LIBRARY]                      | 必需,复制粘贴到第一行,下列参数顺序无所谓                     |
  | ----------------- | ------------------------------ | ------------------------------------------------------------ |
  | 用户名            | user=test                      | 给每个用户起一个名字                                         |
  | 是否抢座位        | reserve=True                   | True代表抢,否则就否则                                        |
  | 用户登录url       | user_login=http://.......      | 抓xd校园的包,提取链接,类似http://wechat.v2.traceint.com/index.php/schoolpushh5/registerLogin?sch_id= |
  | 抢座的图书馆      | lib=南204中文图书借阅一厅(2楼) | 查看xtulib.py中lib_name_dict的名称,复制粘贴,不要自己打       |
  | 抢座的位置        | seat=1,2,3,4,5                 | 要占座的位置列表,随便写几个自己喜欢的                        |
  | 抢座要不要随机    | seat_random=True               | True就每天随机,从自己的填的座位里面优先抢,理论上可以达到每天换着坐的目的,否则就否则 |
  | 抢座提前的秒数    | prems=0.1                      | 可以自己尝试改,不改也挺好用                                  |
  | 抢座的微信通知key | ftkey=                         | 没有就自己去https://sc.ftqq.com注册一个叭,不想每天收到通知提醒一下自己不香吗? |

- 建立log目录用于存放日志

- 脚本运行运行`library.sh`即可

- 配置一个每天7点20的`crontab`定时任务,挂服务器上就大功告成了

- 仅供辛苦的考研人为了要死要活的自习室学习和交流，禁止用于牟利

- 考研人加油叭