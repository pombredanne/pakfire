#!/usr/bin/python

import logging
import os
import sys

try:
	from pakfire.cli import *
	from pakfire.i18n import _

except ImportError, e:
	# Catch ImportError and show a more user-friendly message about what
	# went wrong.

	# Try to load at least the i18n support, but when this fails as well we can
	# go with an English error message.
	try:
		from pakfire.i18n import _
	except ImportError:
		_ = lambda x: x

	# XXX Maybe we can make a more beautiful message here?!
	print _("There has been an error when trying to import one or more of the"
		" modules, that are required to run Pakfire.")
	print _("Please check your installation of Pakfire.")
	print
	print _("The error that lead to this:")
	print "  ", e
	print

	# Exit immediately.
	sys.exit(1)

basename2cls = {
	"pakfire"         : Cli,
	"pakfire-builder" : CliBuilder,
	"pakfire-server"  : CliServer,
	"builder"         : CliBuilderIntern,
}

# Get the basename of the program
basename = os.path.basename(sys.argv[0])

# Check if the program was called with a weird basename.
# If so, we exit immediately.
if not basename2cls.has_key(basename):
	sys.exit(127)

# Return code for the shell.
ret = 0

try:
	# Creating command line interface
	cli = basename2cls[basename]()

	cli.run()

except KeyboardInterrupt:
	logging.critical("Recieved keyboard interupt (Ctrl-C). Exiting.")
	ret = 1

# Catch all errors and show a user-friendly error message.
except Error, e:
	logging.critical("")
	logging.critical(_("An error has occured when running Pakfire."))
	logging.error("")

	logging.error(_("Error message:"))
	logging.error("  %s: %s" % (e.__class__.__name__, e.message))
	logging.error("")

	logging.error(_("Further description:"))
	logging.error("  %s" % e)
	logging.error("")

	ret = e.exit_code

sys.exit(ret)
