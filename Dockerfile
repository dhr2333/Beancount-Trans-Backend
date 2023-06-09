FROM harbor.wlhiot.com:8080/library/python:3
LABEL maintainer="daihaorui <Dai_Haorui@163.com>"
ENV PYTHONUNBUFFERED 1
WORKDIR /code/beancount-trans/

ADD . .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt && pip install gunicorn[gevent]

ENTRYPOINT  ["python", "manage.py", "runserver", "0.0.0.0:8000"]
