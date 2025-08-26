# app/Dockerfile

FROM wiosna97/execengine-compilers:latest AS compilers

RUN apt update && apt install -y python3-pip

RUN apt-get update && apt-get install -y build-essential libpq-dev netcat-openbsd libxml2 libffi8 libssl3 libstdc++6 zlib1g libbz2-1.0 libncursesw6 systemd cgroup-tools && rm -rf /var/lib/apt/lists/*

RUN apt update && apt install -y systemd libpam-systemd curl libcap-dev libsystemd-dev \
  && cd /lib/systemd/system/sysinit.target.wants/ \
  && ls | grep -v systemd-tmpfiles-setup | xargs rm -f \
  && rm -f /etc/systemd/system/*.wants/* \
  && rm -f /lib/systemd/system/multi-user.target.wants/* \
  && rm -f /lib/systemd/system/remote-fs.target.wants/*

RUN echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/isolate.asc] http://www.ucw.cz/isolate/debian/ bookworm-isolate main" > /etc/apt/sources.list
RUN curl https://www.ucw.cz/isolate/debian/signing-key.asc >/etc/apt/keyrings/isolate.asc
RUN apt update && apt install isolate

RUN systemctl set-default multi-user.target

WORKDIR .

COPY requirements.txt .

RUN pip install --break-system-packages --upgrade pip
RUN pip install --break-system-packages -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN touch /etc/systemd.environment

COPY entrypoint.service /etc/systemd/system/
RUN ln -s /etc/systemd/system/entrypoint.service /etc/systemd/system/multi-user.target.wants/
RUN systemctl enable entrypoint.service

ENTRYPOINT ["/sbin/init"]