FROM nikolaik/python-nodejs:python3.10-nodejs20

WORKDIR /app
COPY . .

RUN pip3 install --no-cache-dir --upgrade pip \
    && pip3 install --no-cache-dir --upgrade -r requirements.txt

CMD bash start