#!/usr/bin/python
###############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2012 Pakfire development team                                 #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU General Public License as published by        #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU General Public License for more details.                                #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
#                                                                             #
###############################################################################

import datetime
import gpgme
import io
import os

import logging
log = logging.getLogger("pakfire")

from constants import *
from i18n import _
from system import system

class Keyring(object):
	def __init__(self, pakfire):
		self.pakfire = pakfire
		
		# Configure the environment.
		os.environ["GNUPGHOME"] = self.path
		self.create_path()

		# Initialize context.
		self.ctx = gpgme.Context()
		self.ctx.armor = True

	def __del__(self):
		del os.environ["GNUPGHOME"]

	@property
	def path(self):
		return KEYRING_DIR

	def create_path(self):
		if os.path.exists(self.path):
			os.chmod(self.path, 700)
		else:
			os.makedirs(self.path, 700)

		filename = os.path.join(self.path, "gnupg.conf")

		if os.path.exists(filename):
			os.chmod(filename, 600)
			return

		# Create a default gnupg.conf.
		f = open(filename, "w")
		f.write("# This is a default gnupg configuration file created by\n")
		f.write("# Pakfire %s.\n" % PAKFIRE_VERSION)
		f.close()

		os.chmod(filename, 600)

	def dump_key(self, keyfp):
		key = self.get_key(keyfp, secret=False)
		if not key:
			return ["  " + _("Not in key store: %s") % keyfp, ""]

		ret = []
		for uid in key.uids:
			ret.append(uid.uid)

		ret.append("  " + _("Fingerprint: %s") % keyfp)

		key_priv = self.get_key(keyfp, secret=True)
		if key_priv:
			ret.append("    " + _("Private key available!"))
		ret.append("")

		for subkey in key.subkeys:
			ret.append("  " + _("Subkey: %s") % subkey.keyid)
			if subkey.expired:
				ret.append("    %s" % _("This key has expired!"))

			if subkey.secret:
				ret.append("    %s" % _("This is a secret key."))

			created = datetime.datetime.fromtimestamp(subkey.timestamp)
			ret.append("    %s" % _("Created: %s") % created)
			if subkey.expires:
				expires = datetime.datetime.fromtimestamp(subkey.expires)
				ret.append("    %s" % _("Expires: %s") % expires)
			else:
				ret.append("    %s" % _("This key does not expire."))

			if subkey.pubkey_algo == gpgme.PK_RSA:
				ret.append("    RSA/%s" % subkey.length)

			ret.append("")

		return ret

	def get_keys(self):
		"""
			Returns all keys that are known to the system.
		"""
		return [k.subkeys[0].keyid for k in self.ctx.keylist(None, False)]

	def get_key(self, keyid, secret=False):
		try:
			return self.ctx.get_key(keyid, secret)
		except gpgme.GpgmeError:
			return None

	def get_host_key_id(self):
		return self.pakfire.config.get("signatures", "host_key", None)

	def get_host_key(self, secret=False):
		key_id = self.get_host_key_id()

		if key_id:
			key = self.get_key(key_id, secret=secret)
			return key_id

	def gen_key(self, realname, email):
		args = {
			"realname" : realname,
			"email"    : email,
		}

		params = """
			<GnupgKeyParms format="internal">
				Key-Type: RSA
				Key-Usage: sign
				Key-Length: 4096
				Name-Real: %(realname)s
				Name-Email: %(email)s
				Expire-Date: 0
			</GnupgKeyParms>
		""" % args

		log.info(_("Generating new key for %(realname)s <%(email)s>...") % args)
		log.info(_("This may take a while..."))

		# Generate the key.
		result = self.ctx.genkey(params)

		# Dump the recently generated key.
		for line in self.dump_key(result.fpr):
			log.info(line)

		# Return the fingerprint of the generated key.
		return result.fpr

	def import_key(self, keyfile):
		ret = []

		f = open(keyfile, "rb")
		res = self.ctx.import_(f)
		f.close()

		log.info(_("Successfully imported %s.") % keyfile)

	def export_key(self, keyid, keyfile):
		keydata = io.BytesIO()
		self.ctx.export(keyid, keydata)

		f = open(keyfile, "wb")
		f.write(keydata.getvalue())
		f.close()

	def delete_key(self, keyid):
		key = self.ctx.get_key(keyid)
		self.ctx.delete(key, True)

	def list_keys(self):
		ret = []

		# Search for the host key and show it.
		host_key = self.get_host_key(secret=True)
		if host_key:
			ret.append(_("Host key:"))
			ret += ["  %s" % l for l in self.dump_key(host_key)]
		else:
			host_key_id = self.get_host_key_id()
			if host_key_id:
				host_key = self.get_host_key(secret=False)
				if host_key:
					ret.append(_("WARNING! Host key with ID %s configured, but the secret key is missing!") \
						% host_key_id)
				else:
					ret.append(_("WARNING! Host key with ID %s configured, but not found!") % host_key_id)
			else:
				ret.append(_("No host key available or configured."))

		# List all other keys.
		for key in self.get_keys():
			# Skip the host key.
			if key == host_key:
				continue

			ret += self.dump_key(key)

		return ret

	def sign(self, keyid, cleartext):
		key = self.ctx.get_key(keyid, True)
		assert key, "Key was not found or no secret key installed."

		self.ctx.signers = [key,]

		cleartext = io.BytesIO(cleartext)
		signature = io.BytesIO()

		self.ctx.sign(cleartext, signature, gpgme.SIG_MODE_DETACH)

		return signature.getvalue()

	def verify(self, signature, cleartext):
		assert signature, "Empty signature?"

		signature = io.BytesIO(signature)
		cleartext = io.BytesIO(cleartext)

		# Verify the data.
		sigs = self.ctx.verify(signature, cleartext, None)

		return sigs
