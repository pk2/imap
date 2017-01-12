FROM gliderlabs/alpine
RUN mkdir -p /scripts/imap
WORKDIR /scripts/imap
COPY requirements.txt imap.py ./
RUN apk-install py-virtualenv py-pip libffi-dev gcc python-dev openssl-dev musl-dev ca-certificates bash \
	&& virtualenv venv \
	&& . venv/bin/activate \
	&& pip install --upgrade pip \
	&& pip install -r /scripts/imap/requirements.txt \
	&& apk del libffi-dev gcc python-dev openssl-dev musl-dev

CMD ["/scripts/imap/venv/bin/python","/scripts/imap/imap.py"]