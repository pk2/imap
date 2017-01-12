#!/usr/bin/env python
# Decode encrypted pdfs in mails attachments via imap

from __future__ import unicode_literals

import logging
import logging.config
import PyPDF2
import email
import time
import csv
from datetime import datetime
from imapclient import IMAPClient, SEEN
from ConfigParser import ConfigParser
from tempfile import NamedTemporaryFile
ntf = NamedTemporaryFile()

Config = ConfigParser()
Config.read('/data/imap.conf')

HOST = Config.get('Access', 'host')
USERNAME = Config.get('Access', 'username')
PASSWORD = Config.get('Access', 'password')
SUBJECT = Config.get('Mail options', 'subject')
FILESPATH = Config.get('Files options', 'filespath')
DATAPATH = Config.get('Files options', 'datapath')

logging.config.fileConfig(DATAPATH + 'imap.conf')
logger = logging.getLogger()


def decrypt(pdf_file, password_file=FILESPATH+'pass.csv'):

    pdf = PyPDF2.PdfFileReader(open(pdf_file, 'rb'))
    newname = pdf_file[:-4] + '_decrypted.pdf'
    pdfw = PyPDF2.PdfFileWriter()
    pdfOutputFile = open(newname, 'wb')

    if not pdf.isEncrypted:
        logging.error("File not encrypted. IMAP Logout")
        server.logout()
        return False
    else:
        with open(password_file, 'rb') as csvfile:
            spamreader = csv.reader(csvfile, delimiter=str(';'), quotechar=str('|'))
            for row in spamreader:
                try:
                    writefile = pdf.decrypt(str(row[0]))
                except KeyError:
                    continue
                if writefile:
                    logging.info('File decrypted'),
                    for pageNum in range(pdf.numPages):
                        pageObj = pdf.getPage(pageNum)
                        pdfw.addPage(pageObj)
                    pdfw.write(pdfOutputFile)
                    logging.info('Save new file')
                    return newname

while True:
    server = IMAPClient(HOST, use_uid=True, ssl=True)
    server.login(USERNAME, PASSWORD)
    logging.info('IMAP Login ')

    select_info = server.select_folder('INBOX', readonly=False)

    response = server.search([u'SUBJECT', SUBJECT, 'UNSEEN', 'SINCE', datetime.today().strftime('%d-%b-%Y')])
    logging.info('Emails: %s' % len(response))
    if not response:
        logging.info('No emails.')
    else:
        for i in response:
            odp = server.fetch(i, ['BODY.PEEK[]'])
            logging.info('Fetch mail %s' % i)
            for j in odp:
                msg = email.message_from_string(odp[j]['BODY[]'])
                for part in msg.walk():
                    if not part.get_content_type() == 'application/pdf':
                        continue

                    fname = part.get_filename()
                    if fname:
                        try:
                            open(FILESPATH + str(fname), 'wb').write(part.get_payload(decode=True))
                            if decrypt(FILESPATH + str(fname)):
                                server.add_flags(j, [SEEN])
                        except IOError as e:
                            logging.error('IOError: Permission denied: %s' % fname)
    server.logout()
    logging.info('IMAP Logout')
    time.sleep(Config.getfloat('Other', 'sleeptime'))
