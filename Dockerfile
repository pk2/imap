FROM gliderlabs/alpine
RUN mkdir -p /scripts/imap
WORKDIR /scripts/imap
COPY requirements.txt ./
RUN apk-install qpdf py-virtualenv py-pip libffi-dev gcc python-dev openssl-dev musl-dev ca-certificates bash \
	&& virtualenv venv \
	&& . venv/bin/activate \
	&& pip install -r /scripts/imap/requirements.txt \
	&& apk del libffi-dev gcc python-dev openssl-dev musl-dev
COPY imap.py ./
CMD ["/scripts/imap/venv/bin/python","/scripts/imap/imap.py"]