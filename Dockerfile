FROM python:3.7-slim


RUN mkdir /app
RUN mkdir /app/static
RUN mkdir /app/templates

VOLUME /app/config
VOLUME /app/db
VOLUME /app/users

ADD alf_db.py /app
ADD alfmin.py /app
ADD alf.py /app

ADD config/config.py.docker /app/config/config.py

ADD static /app/static
ADD templates /app/templates

ADD requirements.txt /app


WORKDIR /app
RUN pip install -r requirements.txt


EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-k", "eventlet", "alf:app"]
