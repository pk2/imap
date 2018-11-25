#!/usr/bin/env python
# Decode encrypted pdfs in mails attachments via imap

from __future__ import unicode_literals

import logging
import logging.config
import PyPDF2
import email
import time
import csv
import os

from datetime import datetime, timedelta
from imapclient import IMAPClient, SEEN
from ConfigParser import ConfigParser
from tempfile import NamedTemporaryFile
import distutils.dir_util
ntf = NamedTemporaryFile()

Config = ConfigParser()
Config.read('/data/imap.conf')

HOST = Config.get('Access', 'host')
USERNAME = Config.get('Access', 'username')
PASSWORD = Config.get('Access', 'password')
FILESPATH = Config.get('Files options', 'filespath')
DATAPATH = Config.get('Files options', 'datapath')
EXCLUDEDFILES = Config.get('Files options', 'excludefiles')
DAYSBACK = Config.getfloat('Files options', 'daysback')

logging.config.fileConfig(DATAPATH + 'imap.conf')
logger = logging.getLogger()


def decrypt(pdf_file, password_file=FILESPATH+'pass.csv'):
    logging.info('Start decrypting')

    pdf = PyPDF2.PdfFileReader(open(pdf_file, 'rb'))
    pdfw = PyPDF2.PdfFileWriter()
    logging.info('Files opened')

    if not pdf.isEncrypted:
        logging.warning("File is not encrypted.")
        return False
    else:
        logging.info('File is encrypted')
        newname = pdf_file[:-4] + '_decrypted.pdf'
        with open(password_file, 'rb') as csvfile:
            logging.info('Opening pass DB')
            spamreader = csv.reader(csvfile, delimiter=str(';'), quotechar=str('|'))
            logging.info('Checking pass')
            for row in spamreader:
                try:
                    logging.info('Pass %s' % str(row[0]))
                    writefile = pdf.decrypt(str(row[0]))
                    logging.info('Pdf decrypt status %s' % writefile)
                except ValueError:
                    logging.info('ValueError ')
                    continue
                if writefile:
                    logging.info('File decrypted: %s' % newname),
                    for pageNum in range(pdf.numPages):
                        pageObj = pdf.getPage(pageNum)
                        pdfw.addPage(pageObj)
                    pdfw.write(open(newname, 'wb'))
                    if row[1:2]:
                        path, filename = os.path.split(newname)
                        path2 = FILESPATH + row[1]
                        distutils.dir_util.mkpath(path2)
                        logging.info('Move file to: %s' % path2)
                        os.rename(newname, path2 + '/' + filename)
                        return path2
                    logging.info('Save new file')
                    return newname
            logging.warning('No password found')
            logging.info('Close pass database')
            csvfile.close()
            return False


while True:
    server = IMAPClient(HOST, use_uid=True, ssl=True)
    server.login(USERNAME, PASSWORD)
    logging.info('IMAP Login ')

    select_info = server.select_folder('INBOX', readonly=False)

    response = server.search(['UNSEEN', 'SINCE', (datetime.today()-timedelta(days=DAYSBACK)).strftime('%d-%b-%Y')])
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
                    logging.info('Checking content type: %s' % i)
                    if not part.get_content_type() in ['application/pdf', 'application/octet-stream']:
                        continue
                    logging.info('Continue')

                    fname = part.get_filename()
                    logging.info('Found file type: %s' % fname[-3:])
                    if fname[-3:] in EXCLUDEDFILES:
                        logging.info('File excluded')
                        continue
                    else:
                        logging.info('File not excluded')
                        try:
                            logging.info('Create file')
                            FILE = FILESPATH + str(fname)
                            if os.path.exists(FILE) and os.path.getsize(FILE) > 0:
                                pass
                            else:
                                open(str(FILE), 'wb').write(part.get_payload(decode=True))
                            logging.info('Done')
                            try:
                                if decrypt(FILE):
                                    logging.info('Decrypting done')
                                    server.add_flags(j, [SEEN])
                            except (PyPDF2.utils.PdfReadError, NotImplementedError) as e:
                                logging.error('From: %s Subject: %s Data: %s' % (msg['from'], msg['Subject'], msg['Date']))
                                logging.error('Error: %s' % e)
                                continue
                            except Exception as e:
                                logging.error('Other Error From: %s Subject: %s Data: %s' % (msg['from'], msg['Subject'], msg['Date']))
                                logging.error('Error: %s' % e)
                                continue
                        except IOError as e:
                            logging.error('IOError: %s %s' % (fname, e))
    server.logout()
    logging.info('IMAP Logout')
    time.sleep(Config.getfloat('Other', 'sleeptime'))
