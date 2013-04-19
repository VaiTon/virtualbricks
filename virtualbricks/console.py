#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Virtualbricks - a vde/qemu gui written in python and GTK/Glade.
Copyright (C) 2011 Virtualbricks team

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; version 2.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import sys
import hashlib
import socket
import select
from threading import Thread, Lock


class VbShellCommand(str):
    pass


class ShellCommand(str):
    pass


class RemoteHostConnectionInstance(Thread):
<<<<<<< TREE

    def __init__(self, remotehost, factory):
        self.host = remotehost
        self.factory = factory
        Thread.__init__(self)

    def run(self):
        if not self.host.connected:
            return
        self.host.post_connect_init()
        p = select.poll()
        p.register(self.host.sock, select.POLLIN | select.POLLERR |
                   select.POLLHUP | select.POLLNVAL)
        while self.host.sock and self.host.connected:
            pollret = p.poll(100)
            if (len(pollret)) == 1:
                (fd, ev) = pollret[0]
                if ev != select.POLLIN:
                    self.host.disconnect()
                else:
                    event = self.host.sock.recv(200)
                    if len(event) == 0:
                        event = self.host.sock.recv(200)
                        if len(event) == 0:
                            self.host.disconnect()
                            return
                    for eventline in event.split('\n'):
                        args = eventline.rstrip('\n').split(' ')
                        if len(args) > 0 and args[0] == 'brick-started':
                            for br in self.factory.bricks:
                                if br.name == args[1]:
                                    br.proc = True
                                    br.factory.emit("brick-started", br.name)
                                    #print "Started %s" % br.name
                                    br.run_condition = True
                                    br.post_poweron()

                        if len(args) > 0 and args[0] == 'brick-stopped':
                            for br in self.factory.bricks:
                                if br.name == args[1]:
                                    br.proc = None
                                    br.factory.emit("brick-stopped", br.name)
                                    #print "Stopped %s" % br.name
                                    br.run_condition = False
                                    br.post_poweroff()

                        if len(args) > 0 and args[0] == 'udp':
                            for br in self.factory.bricks:
                                if (br.name == args[1] and br.get_type() ==
                                    'Wire' and args[2] == 'remoteport'):
                                    br.set_remoteport(args[3])
                        self.remotehosts_changed = True


class RemoteHost:

    def __init__(self, factory, address):
        self.sock = None
        self.factory = factory
        self.addr = (address, 1050)
        self.connected = False
        self.connection = None
        self.password = ""
        self.factory.remotehosts_changed = True
        self.autoconnect = False
        self.baseimages = "/root/VM"
        self.vdepath = "/usr/bin"
        self.qemupath = "/usr/bin"
        self.bricksdirectory = "/root"
        self.lock = Lock()

    def num_bricks(self):
        r = 0
        for b in self.factory.bricks:
            if b.homehost and b.homehost.addr[0] == self.addr[0]:
                r += 1
        return r

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect(self.addr)
        except:
            return False, "Error connecting to host"
        else:
            try:
                rec = self.sock.recv(5)
            except:
                return False, "Error reading from socket"

        self.sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        if (not rec.startswith('HELO')):
            return False, "Invalid server response"
        rec = self.sock.recv(256)
        sha = hashlib.sha256()
        sha.update(self.password)
        sha.update(rec)
        hashed = sha.digest()
        self.sock.sendall(hashed)
        p = select.poll()
        p.register(self.sock, select.POLLIN)
        pollret = p.poll(2000)
        if pollret is not None and len(pollret) != 0:
            rec = self.sock.recv(4)
            if rec.startswith("OK"):
                self.connected = True
                self.factory.remotehosts_changed = True
                self.connection = RemoteHostConnectionInstance(self,
                                                               self.factory)
                self.connection.start()
                return True, "Success"
        self.factory.remotehosts_changed = True
        return False, "Authentication Failed."

    def disconnect(self):
        if self.connected:
            self.connected = False
            for b in self.factory.bricks:
                if b.homehost and b.homehost.addr[0] == self.addr[0]:
                    b.poweroff()
            self.send("reset all")
            self.sock.close()
            self.sock = None
        self.factory.remotehosts_changed = True

    def expect_OK(self):
        rec = self.recv()
        if rec is not None and rec.endswith("OK"):
            return True
        elif rec is not None and rec.endswith("FAIL"):
            return "FAIL\n"
            return False
        else:
            return "ERROR"
            return False

    def upload(self, b):
        self.lock.acquire()
        self.send_nolock("new " + b.get_type() + " " + b.name)
        self.putconfig(b)
        self.send_nolock("ACK")
        self.factory.remotehosts_changed = True
        self.lock.release()

    def putconfig(self, b):
        for (k, v) in b.cfg.iteritems():
            if k != 'homehost':
                # ONLY SEND TO SERVER STRING PARAMETERS, OBJECT WON'T BE SENT
                # TO SERVER AS A STRING!
                if isinstance(v, basestring) is True:
                    self.send_nolock(b.name + ' config ' + "%s=%s" % (k, v))
        for pl in b.plugs:
            if b.get_type() == 'Qemu':
                if pl.mode == 'vde':
                    self.send_nolock(b.name + " connect " + pl.sock.nickname)
                else:
                    print "Qemu but not VDE plug"
            elif (pl.sock is not None):
                print "Not a Qemu Plug"
        self.factory.remotehosts_changed = True

    def post_connect_init(self):
        self.send('reset all')

        basepath = self.send_and_recv("i base show")
        if basepath and len(basepath) == 1:
            self.basepath = basepath[0]

        for img in self.factory.disk_images:
            if img.host is not None and img.host.addr[0] == self.addr[0]:
                name = img.path.split("/")
                name = name[len(name) - 1]
                self.send("i add " + img.name + " " + self.basepath + "/" +
                          name)

        for b in self.factory.bricks:
            if b.homehost and b.homehost.addr == self.addr:
                    self.upload(b)

        self.send("cfg set projects " + self.factory.settings.get("projects"))

    def get_files_list(self):
        return self.send_and_recv("i files")

    def send_and_recv(self, cmd):
        self.lock.acquire()
        self.send_nolock(cmd, norecv=True)
        rec = self.recv()
        buff = ""
        while rec is not None and rec != "OK":
            buff = buff + rec
            rec = self.recv()
        self.lock.release()
        return buff

    def recv(self, size=1):

        if not self.connected:
            return ""

        if size == 1:
            p = select.poll()
            p.register(self.sock, select.POLLIN)
            buff = ""
            rec = ""
            while (p.poll(100)):
                buff = self.sock.recv(1)
                rec = rec + buff
                if buff == "\n":
                    rec = rec.rstrip("\n")
                    return rec
        #old version
        else:
            ret = ""
            ret = self.sock.recv(size)
            return ret

    def empty_socket(self):
        """remove the data present on the socket"""

        while 1:
            inputready, o, e = select.select([self.sock], [], [], 0.0)
            if len(inputready) == 0:
                break
        for s in inputready:
            s.recv(1)

    def send(self, cmd, norecv=False):
        self.lock.acquire()
        ret = False
        if self.connected:
            self.sock.sendall(cmd + '\n')
            if not norecv:
                if cmd != "ACK":
                    self.expect_OK()
                else:
                    self.recv()
        self.lock.release()
        return ret

    def send_nolock(self, cmd, norecv=False):
        ret = False
        if self.connected:
            self.sock.sendall(cmd + "\n")
            if not norecv:
                if cmd != "ACK":
                    self.expect_OK()
                else:
                    self.recv()
        return ret

=======
	def __init__(self,remotehost,factory):
		self.host = remotehost
		self.factory = factory
		Thread.__init__(self)
	def run(self):
		if not self.host.connected:
			return
		self.host.post_connect_init()
		p = select.poll()
		p.register(self.host.sock, select.POLLIN | select.POLLERR | select.POLLHUP | select.POLLNVAL)
		while self.host.sock and self.host.connected:
			pollret = p.poll(100)
			if (len(pollret)) == 1:
				(fd,ev) = pollret[0]
				if ev != select.POLLIN:
					self.host.disconnect()
				else:
					event = self.host.sock.recv(200)
					if len(event) == 0:
						event = self.host.sock.recv(200)
						if len(event) == 0:
							self.host.disconnect()
							return
					for eventline in event.split('\n'):
						args = eventline.rstrip('\n').split(' ')


						if len(args) > 0 and args[0] == 'brick-started':
							for br in self.factory.bricks:
								if br.name == args[1]:
									br.proc = True
									br.factory.emit("brick-started", br.name)
									#print "Started %s" % br.name
									br.run_condition = True
									br.post_poweron()

						if len(args) > 0 and args[0] == 'brick-stopped':
							for br in self.factory.bricks:
								if br.name == args[1]:
									br.proc = None
									br.factory.emit("brick-stopped", br.name)
									#print "Stopped %s" % br.name
									br.run_condition = False
									br.post_poweroff()

						if len(args) > 0 and args[0] == 'udp':
							for br in self.factory.bricks:
								if br.name == args[1] and br.get_type() == 'Wire' and args[2] == 'remoteport':
									br.set_remoteport(args[3])
						self.remotehosts_changed=True

class RemoteHost():
	def __init__(self, factory, address):
		self.sock = None
		self.factory = factory
		self.addr = (address,1050)
		self.connected=False
		self.connection = None
		self.password=""
		self.factory.remotehosts_changed=True
		self.autoconnect=False
		self.baseimages="/root/VM"
		self.vdepath="/usr/bin"
		self.qemupath="/usr/bin"
		self.bricksdirectory="/root"
		self.lock = Lock()

	def num_bricks(self):
		r = 0
		for b in self.factory.bricks:
			if b.homehost and b.homehost.addr[0] == self.addr[0]:
				r+=1
		return r

	def connect(self):
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.sock.connect(self.addr)
		except:
			return False,"Error connecting to host"
		else:
			try:
				rec = self.sock.recv(5)
			except:
				return False,"Error reading from socket"

		self.sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
		if (not rec.startswith('HELO')):
			return False,"Invalid server response"
		rec = self.sock.recv(256)
		sha = hashlib.sha256()
		sha.update(self.password)
		sha.update(rec)
		hashed = sha.digest()
		self.sock.sendall(hashed)
		p = select.poll()
		p.register(self.sock, select.POLLIN)
		pollret = p.poll(2000)
		if pollret is not None and len(pollret) != 0:
			rec = self.sock.recv(4)
			if rec.startswith("OK"):
				self.connected=True
				self.factory.remotehosts_changed=True
				self.connection = RemoteHostConnectionInstance(self, self.factory)
				self.connection.start()
				return True,"Success"
		self.factory.remotehosts_changed=True
		return False,"Authentication Failed."

	def disconnect(self):
		if self.connected:
			self.connected=False
			for b in self.factory.bricks:
				if b.homehost and b.homehost.addr[0] == self.addr[0]:
					b.poweroff()
			self.send("reset all")
			self.sock.close()
			self.sock = None
		self.factory.remotehosts_changed=True

	def expect_OK(self):
		rec = self.recv()
		if rec is not None and rec.endswith("OK"):
			return True
		elif rec is not None and rec.endswith("FAIL"):
			return "FAIL\n"
			return False
		else:
			return "ERROR"
			return False

	def upload(self,b):
		self.lock.acquire()
		self.send_nolock("new "+b.get_type()+" "+b.name)
		self.putconfig(b)
		self.send_nolock("ACK")
		self.factory.remotehosts_changed=True
		self.lock.release()

	def putconfig(self,b):
		for (k, v) in b.cfg.iteritems():
			if k != 'homehost':
				# ONLY SEND TO SERVER STRING PARAMETERS, OBJECT WON'T BE SENT TO SERVER AS A STRING!
				if isinstance(v, basestring) is True:
					self.send_nolock(b.name + ' config ' + "%s=%s" % (k, v))
		for pl in b.plugs:
			if b.get_type() == 'Qemu':
				if pl.mode == 'vde':
					self.send_nolock(b.name + " connect " + pl.sock.nickname)
				else:
					print "Qemu but not VDE plug"
			elif (pl.sock is not None):
				print "Not a Qemu Plug"
		self.factory.remotehosts_changed=True

	def post_connect_init(self):
		self.send('reset all')

		basepath = self.send_and_recv("i base show")
		if basepath and len(basepath) == 1:
			self.basepath = basepath[0]

		for img in self.factory.disk_images:
			if img.host is not None and img.host.addr[0] == self.addr[0]:
				name = img.path.split("/")
				name = name[len(name)-1]
				self.send("i add " + img.name + " " + self.baseimages + "/" + name)

		for b in self.factory.bricks:
			if b.homehost and b.homehost.addr == self.addr:
					self.upload(b)

		self.send("cfg set projects " + self.factory.settings.get("projects"))

	def get_files_list(self):
		return self.send_and_recv("i files")

	def send_and_recv(self, cmd):
		self.lock.acquire()
		self.send_nolock(cmd, norecv=True)
		rec = self.recv()
		buff=""
		while rec is not None and rec != "OK":
			buff=buff+rec
			rec = self.recv()
		self.lock.release()
		return buff

	def recv(self, size=1):

		if not self.connected:
			return ""

		if size==1:
			p = select.poll()
        	        p.register(self.sock, select.POLLIN)
			buff=""
			rec=""
               		while (p.poll(100)):
				buff = self.sock.recv(1)
				rec=rec+buff
				if buff == "\n":
					rec = rec.rstrip("\n")
					return rec
		#old version
		else:
			ret = ""
			ret = self.sock.recv(size)
			return ret

	def empty_socket(self):
		"""remove the data present on the socket"""
    		while 1:
		        inputready, o, e = select.select([self.sock],[],[], 0.0)
		        if len(inputready)==0: break
			for s in inputready: s.recv(1)

	def send(self, cmd, norecv=False):
		self.lock.acquire()
		ret = False
		if self.connected:
			self.sock.sendall(cmd + '\n')
			if not norecv:
				if cmd != "ACK":
					self.expect_OK()
				else:
					self.recv()
		self.lock.release()
		return ret

	def send_nolock(self, cmd, norecv=False):
		ret = False
		if self.connected:
			self.sock.sendall(cmd + "\n")
			if not norecv:
				if cmd != "ACK":
					self.expect_OK()
				else:
					self.recv()
		return ret
>>>>>>> MERGE-SOURCE

def CommandLineOutput(outf, data):
    if outf == sys.stdout:
        return outf.write(data + '\n')
    else:
        return outf.send(data + '\n')


def Parse(factory, command, console=sys.stdout):
    clo, c = CommandLineOutput, console
    if (command == 'q' or command == 'quit'):
        factory.quit()
    elif (command == 'h' or command == 'help'):
        clo(c,  'Base command -----------------------------------------------')
        clo(c,  'ps             List of active process')
        clo(c,  'n[ew] TYPE NAME            Create a new TYPE brick with NAME')
        clo(c,  'list           List of bricks already created')
        clo(c,  'socks          List of connections available for bricks')
        clo(c,  'conn[ections]      List of connections for each bricks')
        clo(c,  '\nBrick configuration command ------------------------------')
        clo(c,  'BRICK_NAME show    List parameters of BRICK_NAME brick')
        clo(c,  'BRICK_NAME on            Starts BRICK_NAME')
        clo(c,  'BRICK_NAME off            Stops BRICK_NAME')
        clo(c,  'BRICK_NAME remove        Delete BRICK_NAME')
        clo(c,  'BRICK_NAME config PARM=VALUE  Configure a parameter.')
        clo(c,  'BRICK_NAME connect NICK        Connect BRICK_NAME to a Sock')
        clo(c,  'BRICK_NAME disconnect        Disconnect BRICK_NAME to a sock')
        clo(c,  'BRICK_NAME help         Help about parameters of BRICK_NAME')
        return True
    elif (command == 'ps'):
        factory.proclist(console)
        return True
    elif command.startswith('reset all'):
        factory.reset_config()
        return True
    elif command.startswith('n ') or command.startswith('new '):
        if(command.startswith('n event') or (command.startswith('new event'))):
            factory.newevent(*command.split(" ")[1:])
        else:
            factory.newbrick(*command.split(" ")[1:])
        return True
    elif command == 'list':
        CommandLineOutput(console,  "Bricks:")
        for obj in factory.bricks:
            CommandLineOutput(console,  "%s %s" % (obj.get_type(), obj.name))
        CommandLineOutput(console, "")
        CommandLineOutput(console, "Events:")
        for obj in factory.events:
            CommandLineOutput(console, "%s %s" % (obj.get_type(), obj.name))
        CommandLineOutput(console,  "End of list.")
        CommandLineOutput(console, "")
        return True
    elif command.startswith('config') or command.startswith('cfg'):
        factory.set_configuration(console, *command.split(" ")[1:])
        return True
    elif command.startswith('images') or command.startswith("i"):
        factory.images_manager(console, *command.split(" ")[1:])
        return True
    elif command == 'socks':
        for s in factory.socks:
            CommandLineOutput(console,  "%s" % s.nickname,)
            if s.brick is not None:
                CommandLineOutput(console, " - port on %s %s - %d available" %
                                  (s.brick.get_type(), s.brick.name,
                                   s.get_free_ports()))
            else:
                CommandLineOutput(console,  "not configured.")
        return True

    elif command.startswith("conn") or command.startswith("connections"):
        for b in factory.bricks:
            CommandLineOutput(console, "Connections from " + b.name +
                              " brick:\n")
            for sk in b.socks:
                if b.get_type() == 'Qemu':
                    CommandLineOutput(console, '\tsock connected to ' +
                                      sk.nickname + ' with an ' + sk.model +
                                      ' (' + sk.mac + ') card\n')
            for pl in b.plugs:
                if b.get_type() == 'Qemu':
                    if pl.mode == 'vde':
                        clo(c, '\tlink connected to ' + pl.sock.nickname +
                            ' with a ' + pl.model + ' (' + pl.mac + ') card\n')
                    else:
                        clo(c, '\tuserlink connected with a ' + pl.model +
                            ' (' + pl.mac + ') card\n')
                elif (pl.sock is not None):
                    clo(c, '\tlink: ' + pl.sock.nickname + '\n')
        return True

    elif command.startswith("control ") and len(command.split(" ")) == 3:
        host = command.split(" ")[1]
        password = command.split(" ")[2]
        remote = None
        for h in factory.remote_hosts:
            if h.addr == host:
                remote = h
                break
        if not remote:
            remote = RemoteHost(factory, host)
        remote.password = password
        factory.factory.remotehosts_changed = True

        if remote.connect():
            clo(c, "Connection OK\n")
        else:
            clo(c, "Connection Failed.\n")
        return True

    elif command.startswith("udp ") and factory.TCP:
        args = command.split(" ")
        if len(args) != 4 or args[0] != 'udp':
            clo(c, "FAIL udp arguments \n")
            return False
        for b in factory.bricks:
            if b.name == args[2]:
                w = PyWire(factory, args[1])  # XXX: PyWire not defined
                w.set_remoteport(args[3])
                w.connect(b.socks[0])
                w.poweron()
                return True
            clo(c, "FAIL Brick not found: " + args[2] + "\n")
    elif command == '':
        return True
    else:
        found = None
        for obj in factory.bricks:
            if obj.name == command.split(" ")[0]:
                found = obj
                break
        if found is None:
            for obj in factory.events:
                if obj.name == command.split(" ")[0]:
                    found = obj
                    break

        if found is not None and len(command.split(" ")) > 1:
            factory.brickAction(found, command.split(" ")[1:])
            return True
        else:
            print 'Invalid console command "%s"' % command
            return False
