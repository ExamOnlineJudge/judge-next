FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PORT=5055
ENV HOST=0.0.0.0

WORKDIR /app
COPY . /app

EXPOSE 5055

CMD ["python3", "server.py"]
