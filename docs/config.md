## 配置说明:

本项目较多配置都基于环境变量，所有的环境变量如下所示:

| 环境变量名称              | 默认值                                                       | 备注                                                         |
| ------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| DJANGO_DEBUG              | False                                                        |                                                              |
| DJANGO_SECRET_KEY         | DJANGO_BLOG_CHANGE_ME                                        | 请务必修改，建议[随机生成](https://www.random.org/passwords/?num=5&len=24&format=html&rnd=new) |
| DJANGO_MYSQL_DATABASE     | djangoblog                                                   |                                                              |
| DJANGO_MYSQL_USER         | root                                                         |                                                              |
| DJANGO_MYSQL_PASSWORD     | djangoblog_123                                               |                                                              |
| DJANGO_MYSQL_HOST         | 127.0.0.1                                                    |                                                              |
| DJANGO_MYSQL_PORT         | 3306                                                         |                                                              |
| DJANGO_MEMCACHED_ENABLE   | True                                                         |                                                              |
| DJANGO_MEMCACHED_LOCATION | 127.0.0.1:11211                                              |                                                              |
| DJANGO_BAIDU_NOTIFY_URL   | http://data.zz.baidu.com/urls?site=https://www.example.org&token=CHANGE_ME | 请在[百度站长平台](https://ziyuan.baidu.com/linksubmit/index)获取接口地址 |
| DJANGO_EMAIL_TLS          | False                                                        |                                                              |
| DJANGO_EMAIL_SSL          | True                                                         |                                                              |
| DJANGO_EMAIL_HOST         | smtp.example.org                                             |                                                              |
| DJANGO_EMAIL_PORT         | 465                                                          |                                                              |
| DJANGO_EMAIL_USER         | SMTP_USER_CHANGE_ME                                          |                                                              |
| DJANGO_EMAIL_PASSWORD     | SMTP_PASSWORD_CHANGE_ME                                      |                                                              |
| DJANGO_ADMIN_EMAIL        | admin@example.org                                            |                                                              |
| DJANGO_WEROBOT_TOKEN      | DJANGO_BLOG_CHANGE_ME                                        |                                                              |
| DJANGO_ELASTICSEARCH_HOST |                                                              |                                                              |