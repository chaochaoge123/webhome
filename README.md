#### 1. 虚拟环境安装
```
pip install virtualenv
pip install virtualenvwrapper
mkvirtualenv --python=/usr/bin/python3 py3
workon py3
```
#### 2.安装依赖包
```
cd /q_home(工作目录)
pip install requirements.txt
```
#### 3.初始化数据库，用户
```
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```
#### 4.启动
```
开发环境：
python manage.py runserver

生产环境(nginx+uwsgi+django)：
详见uwsgi.conf,supervisor.conf,nginx.conf等文件

# 静态资源管理：
python manage.py collectstatic
python manage.py compress

地址: https://www.qqc-home.com/
```