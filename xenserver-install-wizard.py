#!/usr/bin/env python

import sys, subprocess, argparse
import xapi, replace, grub, grub2, network, iptables, storage, templates, logging, hostname, toolstack
import errata
import os
from tui import Tui

def reboot():
	xapi.sync()
	print >>sys.stderr, "Triggering an immediate reboot"
	cmd = [ "/sbin/reboot" ]
	x = subprocess.call(cmd)
	if x <> 0:
		print >>sys.stderr, "FAILED: to trigger a reboot (%s)" % (" ".join(cmd))
	else:
		exit(0)

def stop_xend(tui):
	need_to_reboot = False

	print >>sys.stderr, "Permanently stopping xend"
	try:
		if subprocess.call(["chkconfig", "xend"]) <> 0:
			if subprocess.call(["chkconfig", "--level", "345", "xend", "off"]) <> 0:
				print >>sys.stderr, "FAILED: to disable xend"
	except:
		pass # no chkconfig on Debian/Ubuntu
	if os.path.exists(toolstack.etc_default_xen):
		r = toolstack.analyse(tui)
		if r:
			need_to_reboot = True
			for change in r:
				replace.file(change[0], change[1])
	if subprocess.call(["service", "xend", "stop"]) <> 0:
		print >>sys.stderr, "FAILED: to stop xend"
	return need_to_reboot

def reboot_before_continuing(args):
	if args.auto_reboot:
		reboot ()
	else:
		if args.yes_to_all:
			# surrounding automation can do more configuration before the reboot
			print >>sys.stdout, "Please reboot the machine and re-run the wizard."
			exit(2)
		if tui.yesno("Please re-run the wizard after the machine is rebooted. Would you like to reboot now?", False):
			reboot()
		else:
			print >>sys.stdout, "Please reboot the machine and re-run the wizard."
			exit(2)


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument('--yes-to-all', action='store_true')
	parser.add_argument('--reboot', dest="auto_reboot", action='store_true')
	args = parser.parse_args()

	tui = Tui(args.yes_to_all)

	r = logging.analyse(tui)
	if r:
		replace.file(r[0], r[1])
		logging.restart()
	need_to_reboot = stop_xend (tui)
        if os.path.isfile("/etc/default/grub"):
                r = grub2.analyse(tui)
        elif os.path.isfile("/boot/grub/grub.conf"):
		r = grub.analyse(tui)
        else:
                print >>sys.stderr, "No bootloader to update, skipping"
                r = False
	if r:
		need_to_reboot = True
		replace.file(r[0], r[1])
		if os.path.isfile("/etc/default/grub"):
                        grub2.update_grub_config()

	# To run the toolstack we need to reboot with Xen
	if need_to_reboot:
		reboot_before_continuing(args)

	xapi.start ()
        # If XAPI started then we don't need to reboot for any grub changes
	need_to_reboot = False

	r = network.analyse(tui)
	if r:
		need_to_reboot = True
		for change in r:
			replace.file(change[0], change[1])
	r = iptables.analyse(tui)
	if r:
		replace.file(r[0], r[1])
                iptables.restart()
	storage.analyse(tui)
	hostname.analyse(tui)
	templates.create()
	errata.analyse()
	xapi.sync()

	if need_to_reboot:
		reboot_before_continuing(args)

	print "Welcome to XenServer!"
