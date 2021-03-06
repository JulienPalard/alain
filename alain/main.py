# -*- coding: utf-8 -*-
from irc import IRCBot, IRCConnection as BaseConn
from ConfigObject import ConfigObject
from irc import socket
from functools import wraps
from alain.cantine import check_events
from alain.afpyro import incoming_afpyros
from alain.regexp import REGEXP
from alain import crons
from alain import rss
from alain import shell
import threading
import datetime
import random
import httplib
import types
import time
import stat
import sys
import os


class HTTPPing(object):

    def __init__(self, host, port, path, timeout=30):
        self.host, self.port, self.path = host, port, path
        self.timeout = timeout
        self.status = True
        self.reason = ''

    def ping(self):
        if self.port == 443:
            conn = httplib.HTTPSConnection(self.host, self.port)
        else:
            conn = httplib.HTTPConnection(self.host, self.port)
        try:
            conn.request('GET', self.path)
            resp = conn.getresponse()
        except Exception, e:
            self.status = False
            self.reason = str(e)
        else:
            if resp.status in (200, 302):
                self.status = True
                self.reason = ''
            else:
                self.status = False
                self.reason = '%s %s' % (resp.status, resp.reason)


class IRCConnection(BaseConn):

    def connect(self):
        """\
        Connect to the IRC server using the nickname
        """
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self._sock.connect((self.server, self.port))
        except socket.error:
            self.logger.error('Unable to connect to %s on port %d' % (
                              self.server, self.port), exc_info=1)
            sys.exit(1)

        self._sock_file = self._sock.makefile()

        self.send("USER alain %s blah :I'm Alain. The AFPy mascot" % (
                  self.server,), True)
        self.logger.info('Authing as %s' % self.nick)

        # send NICK command as soon as authing
        self.register_nick()

    def handle_ping(self, payload):
        """\
        Respond to periodic PING messages from server
        """
        self.send('PONG %s' % payload)

        def async(self):
            self.mon()
            for k in [name for name in dir(self) if name.endswith('_cron')]:
                v = getattr(self, k)
                if getattr(v, 'is_cron', False) is True:
                    v()

        t = threading.Thread(target=async, args=(self,))
        t.start()

    def ghost(self):
        if self.config.bot.password:
            nick = self.config.bot.nick
            self.send('PRIVMSG nickserv :ghost %s %s ' % (
                      nick, self.config.bot.password))
            time.sleep(2)
            self.nick = nick
            self.send('NICK %s' % self.nick)
            time.sleep(2)
            self.send(
                'PRIVMSG nickserv :identify %s' % self.config.bot.password)
        else:
            self.logger.info('No password set')

    def mon(self, verbose=False):
        for name, s in self.services:
            status = s.status
            s.ping()

            message = ''
            if status and s.status:
                message = '- %s: UP' % name
            elif status and not s.status:
                message = '- %s: FAILURE %s' % (name, s.reason)
            elif not status and s.status:
                message = '- %s: FIXED' % name

            if verbose:
                self.respond(message, self.channel)
            elif not status or not s.status:
                self.respond(message, self.channel)

    @crons.hourly(4, 20)
    def awaiting_cron(self):
        try:
            message = rss.awaiting()
        except:
            pass
        else:
            if message:
                self.respond(message, self.channel)
                return message
        return ''

    @crons.hourly(4, 40)
    def matte_cron(self):
        return self.matte()

    def matte(self, force=False):
        filename = os.path.join(self.config.bot.var, 'cantine.txt')
        try:
            results = check_events(filename)
        except:
            return ''
        else:
            if results:
                for amount, url in results:
                    if force or amount > 10:
                        line = 'Il y a %s inscrits pour %s' % (amount, url)
                        self.respond(line, self.channel)
            elif force:
                self.respond("J'ai rien", self.channel)
        return ''

    @crons.dayly(17, 42)
    def afpyro_cron(self):
        messages = self.afpyro()
        for message in messages:
            self.respond(message, self.channel)

    def afpyro(self, force=False):
        messages = []
        now = datetime.datetime.now()
        now = datetime.datetime(now.year, now.month, now.day)
        for date, link in incoming_afpyros():
            delta = date - now
            message = ''
            if delta.days == 0:
                message = 'Ca va commencer!!! %s' % link
            elif delta.days == 1:
                message = 'C\'est demain!!! %s' % link
            elif delta.days > 10 and (delta.days % 5 == 0 or force):
                message = 'Prochain afpyro dans %s jours...... *loin* %s' % (
                    delta.days, link)
            elif delta.days > 5 and (delta.days % 3 == 0 or force):
                message = 'Prochain afpyro dans %s jours... %s' % (
                    delta.days, link)
            elif delta.days > 0 and delta.days < 5:
                message = 'Prochain afpyro dans %s jours! %s' % (
                    delta.days, link)
            if message:
                messages.append(message)
        return messages


def sudoers_command(arg):
    def wrapper(func, regexp):
        @wraps(func)
        def cmd(self, nick, message, channel, *args, **kwargs):
            if nick not in sudoers or not channel:
                return 'matin %s' % nick
            return func(self, nick, message, channel)
        cmd.regexp = regexp
        return cmd
    if isinstance(arg, basestring):
        def wait_for_func(func):
            return wrapper(func, arg)
        return wait_for_func
    else:
        return wrapper(arg, '^%s$')


def reponse(values):
    def wrapper(self, nick, message, channel):
        if not channel:
            return ''
        if isinstance(values, (list, tuple)):
            message = random.choice(values)
        else:
            message = values
        s = random.choice([float(x) / 10 for x in range(5, 15, 1)])
        time.sleep(s)
        return message % dict(nick=nick, channel=channel)
    return wrapper


class Alain(IRCBot):

    @sudoers_command
    def identify(self, nick, message, channel):
        """Recuperation de pseudo"""
        self.conn.ghost()
        return '%s: Thanks!' % nick

    @sudoers_command
    def status(self, nick, message, channel):
        """Status des services HTTP"""
        self.conn.respond('Checking services...', channel)
        self.conn.mon(verbose=True)
        return 'Done.'

    @sudoers_command
    def die(self, nick, message, channel):
        """Die"""
        self.conn.respond('+', channel)
        self.conn.send('QUIT')
        raise OSError()

    @sudoers_command
    def pyping(self, nick, message, channel):
        """ping"""
        self.conn.handle_ping(':' + nick)
        return ''

    @sudoers_command
    def clean(self, nick, message, channel):
        """Supprime les doublons dans ce que je dis"""
        filename = os.path.join(self.config.bot.var, 'messages.txt')
        messages = []
        with open(filename) as fd:
            messages = set([l for l in fd.readlines() if l.strip()])
        with open(filename, 'w') as fd:
            for message in messages:
                fd.write(message)
        return "Ca c'est fait"

    @sudoers_command('^%s .*')
    def matte(self, nick, message, channel):
        """Je matte le nombre d'inscrit à un event de la cantine
        (url|liste|rien)"""
        filename = os.path.join(self.config.bot.var, 'cantine.txt')
        message = message.split(' ', 1)[1]
        if message.startswith('http://lacantine.org/'):
            with open(filename, 'a+') as fd:
                fd.write(message.strip() + '\n')
            return 'Je matterai %s' % message
        elif message.startswith('rien'):
            with open(filename, 'w') as fd:
                fd.write('')
            return 'Je matte plus rien'
        elif message.startswith('list'):
            return self.conn.matte(force=True)
        else:
            return 'Moi pas comprendre'
        return ''

    @sudoers_command('^%s .*')
    def restart(self, nick, message, channel):
        """restart (docs|plone|members|alain)"""
        message = message.split(' ', 1)[1]
        for line in shell.restart(message):
            self.respond(line, channel)
        return ''

    def matin(self, nick, message, channel):
        """Ping"""
        return '%s: matin' % nick

    def help(self, nick, message, channel):
        """Affiche l'aide"""
        self.respond('Available commands are:', channel)
        for k, v in self.__class__.__dict__.items():
            if not k.startswith('_') and getattr(v, '__doc__', None):
                lines = [l.strip() for l in v.__doc__.split()]
                self.respond('- %s: %s' % (k, ' '.join(lines)), channel)
        return ''

    def faq(self, *args, **kwargs):
        """URL de la FAQ"""
        return 'http://www.afpy.org/docs/faq.html'

    def admins(self, *args, **kwargs):
        """Liste des gens sudoers sur py.afpy.org"""
        return ', '.join(self.sudoers)

    def afpyro(self, *args, **kwargs):
        """Date/URL du prochain afpyro"""
        messages = self.conn.afpyro(force=True)
        if messages:
            for message in messages:
                self.respond(message, self.config.bot.channel)
            return ''
        else:
            return 'Rien à boire...'

    def add_message(self, message):
        filename = os.path.join(self.config.bot.var, 'messages.txt')
        with open(filename, 'a+') as fd:
            fd.write(message + '\n')

    def get_message(self):
        filename = os.path.join(self.config.bot.var, 'messages.txt')
        pos = random.randint(0, os.stat(filename)[stat.ST_SIZE])
        with open(filename) as fd:
            fd.seek(pos)
            fd.readline()
            try:
                return fd.readline()
            except:
                return 'matin'

    def ia(self, nick, message, channel):
        if not channel:
            return ''
        for k in self.__class__.__dict__:
            if message.startswith(k):
                return ''
        self.add_message(message)
        return '%s: %s' % (nick, self.get_message())

    def command_patterns(self):
        commands = []
        for k, v in self.__class__.__dict__.items():
            if not k.startswith('_') and getattr(v, '__doc__', None):
                regexp = getattr(v, 'regexp', '^%s$') % k
                commands.append(self.ping(regexp, getattr(self, k)))
        for i, (regexp, values) in enumerate(REGEXP):
            meth = reponse(values)
            meth.__name__ = 'rep_%s' % i
            meth = types.MethodType(meth, self)
            commands.append((regexp, meth))
        return commands + [
            self.ping('(.*)', self.ia),
        ]


sudoers = (
    'ccomb',
    'gawel',
    'ogrisel',
    'jpcw',
    'tarek',
    'NelleV',
    'arthru',
    'feth',
    'bmispelon',
)

services = (
    ('www', HTTPPing('www.afpy.org', 80, '/')),
    ('membres', HTTPPing('www.afpy.org', 80, '/membres/login')),
    ('hg', HTTPPing('hg.afpy.org', 443, '/')),
    ('afpyro', HTTPPing('afpyro.afpy.org', 80, '/faq.html')),
    ('pycon', HTTPPing('www.pycon.fr', 80, '/2013/')),
    ('logs', HTTPPing('logs.afpy.org', 80, '/')),
    ('fld', HTTPPing('front-de-liberation-des-developpeurs.org', 80, '/')),
)


def main():
    config = ConfigObject(defaults=dict(here=os.getcwd()))
    config.read(os.path.expanduser('~/.alainrc'))
    conn = IRCConnection('irc.freenode.net', 6667, config.bot.nick + '_',
                         verbosity=config.bot.verbosity.as_int(),
                         logfile=config.bot.logfile or None)
    conn.config = config
    conn.channel = config.bot.channel
    conn.services = services
    conn.connect()
    time.sleep(3)
    conn.ghost()
    bot = Alain(conn)
    bot.config = config
    bot.channel = config.bot.channel
    bot.sudoers = sudoers
    bot.messages = []
    conn.join(config.bot.channel)
    time.sleep(2)
    conn.respond('matin', config.bot.channel)
    try:
        conn.enter_event_loop()
    except Exception, e:
        conn.logger.exception(e)
