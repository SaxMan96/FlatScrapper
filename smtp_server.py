from __future__ import print_function

import asyncore
from datetime import datetime
from smtpd import SMTPServer


class EmlServer(SMTPServer):
    no = 0

    def process_message(self, peer, mailfrom, rcpttos, data):
        filename = '%s-%d.eml' % (datetime.now().strftime('%Y%m%d%H%M%S'),
                                  self.no)
        f = open(filename, 'w')
        f.write(data)
        f.close
        print('%s saved.' % filename)
        self.no += 1


def run():
    # start the smtp server on localhost:1025
    foo = EmlServer(('localhost', 1025), None)
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    run()
