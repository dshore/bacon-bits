import ConfigParser
import SQL
import datetime
from os import getenv
import socket
import re
import warnings

def timedelta(time_str):
    s = re.sub('\D', '', time_str)
    return datetime.timedelta(hours=int(s[0:2]), minutes=int(s[2:4]), seconds=int(s[4:6]))

def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        pass
    return False

class atts(object):
    def __init__(self, kwargs):
        for key, val in kwargs.items():
            assert key in self.atts, 'key: %s, is not a valid attribute' % key
            self.set(key, val)

    def set(self, key, val):
        assert key in self.atts, 'key: %s, is not a valid attribute' % key
        if not self.atts[key] == val:
            print "atts: %s setting %s => %s" % (type(self), key, str(val))
            self.atts[key] = val

    def get(self, key):
        return self.atts[key]

class comm(atts):
    def __init__(self, host, port, **kwargs):
        self.atts = {'ack': 'OK',
                     'nbytes' : 4096,
                     'timeout': 10,
                     'eol_char' : '\n'}
        
        super(comm, self).__init__(kwargs)
        warnings.simplefilter("always")

        self.host = host
        self.port = port
        self.buf = bytearray(b' ' * self.get('nbytes'))

        self.reset()

    def readline(self):
        out = ""
        while True:
            try:
                nbytes = self.socket().recv_into(self.buf)
            except socket.timeout, msg:
                warnings.warn(str(msg))
                continue
            if not nbytes:
                self.reset()
                return None
            out += str(self.buf[:nbytes])
            if out[-1] == self.get('eol_char'):
                break
        return out[:-1]

    def sendline(self, valstr):
        self.socket().send(valstr + self.get('eol_char'))
        ack = self.readline()
        return ack == self.get('ack')
        
    def reset(self):
        self.socket_ = None
        self.socket().settimeout(float(self.get('timeout')))

    def socket(self):
        if self.socket_ is None:
            for family, socktype, proto, canonname, sockaddr in socket.getaddrinfo(self.host, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM):
                try:
                    s = socket.socket(family, socktype, proto)
                except socket.error, msg:
                    continue
                try:
                    s.connect(sockaddr)
                except socket.error, msg:
                    # print "Connect except..."+str(msg)
                    s.close()
                    s = None
                    continue
                break
            if s is None:
                raise StandardError(msg)
            self.socket_ = s
        return self.socket_

class config(object, ConfigParser.SafeConfigParser):
    def __init__(self, default_cfg='mst.cfg', **kwargs):
        super(object, self).__init__()
        self.read([default_cfg, "%s/%s" % (getenv("HOME"), default_cfg)])

    def dbh(self, dbname=None, db_type='mysql'):
        self.dbh_ = None
        self.db_type = db_type

        if self.dbh_ is None:
            self.dbh_ = SQL.connection(db=self.get(db_type, "default_db"),
                                       user=self.get(db_type, "user"),
                                       passwd=self.get(db_type, "passwd"),
                                       unix_socket=self.get(db_type, "unix_socket"),
                                       type=db_type
                                       )
            if not dbname is None:
                if self.dbh_.db_exists(dbname):
                    self.dbh_.select_db(dbname)
                else:
                    warnings.warn("Could not connect to database '%s'" % (dbname))
        return self.dbh_
