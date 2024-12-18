FROM python:3.9-alpine

RUN apk add --update build-base gcc postgresql-dev

WORKDIR /app

COPY . /app

RUN pip install -r requirements.txt

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
