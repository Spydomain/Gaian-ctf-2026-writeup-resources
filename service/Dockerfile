FROM python:3.12-slim
WORKDIR /opt/console
COPY app.py /opt/console/app.py
COPY data /opt/console/data
COPY entrypoint.sh /opt/console/entrypoint.sh
ENV CATALOG_DIR=/opt/console/data PORT=8000
EXPOSE 8000
ENTRYPOINT ["/bin/sh","/opt/console/entrypoint.sh"]
