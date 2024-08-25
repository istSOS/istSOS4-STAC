FROM python:3.9-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 80
#Modify to mount the local filesystem
# VOLUME ["c:\\Users\\GeosysIOT\\Downloads\\newf\\"]


ENTRYPOINT ["python", "main.py"]


