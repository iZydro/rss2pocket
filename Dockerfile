FROM python:3.7-alpine

ENV PYTHONUNBUFFERED 1

ADD src/ /

RUN pip install feedparser configparser boto3

CMD [ "python", "./update.py" ]
