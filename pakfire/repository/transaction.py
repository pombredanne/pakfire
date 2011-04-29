#!/usr/bin/python

import logging
import os
import progressbar
import sys

import pakfire.packages as packages
import pakfire.util as util

from pakfire.i18n import _

PKG_DUMP_FORMAT = " %-21s %-8s %-21s %-19s %5s "

class ActionError(Exception):
	pass


class Action(object):
	def __init__(self, pakfire, pkg, deps=None):
		self.pakfire = pakfire
		self.pkg = pkg
		self.deps = deps or []

	def __cmp__(self, other):
		# XXX ugly
		return cmp(self.__repr__(), other.__repr__())

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.pkg.friendly_name)

	def remove_dep(self, dep):
		if not self.deps:
			return

		while dep in self.deps:
			logging.debug("Removing dep %s from %s" % (dep, self))
			self.deps.remove(dep)

	def run(self):
		raise NotImplementedError

	@property
	def local(self):
		"""
			Reference to local repository (database).
		"""
		return self.pakfire.repos.local


class ActionCleanup(Action):
	def gen_files(self):
		"""
			Return a list of all files that are not in the package anymore
			and so to be removed.
		"""
		files = []

		# Compare the filelist of the old and the new package and save the
		# difference.

		for f in self.pkg.old_package.filelist:
			if f in self.pkg.filelist:
				continue

			# Save absolute path.
			f = os.path.join(self.pakfire.path, f)
			files.append(f)

		return files

	def remove_files(self, message, files):
		if not files:
			return

		pb = util.make_progress(message, len(files))
		i = 0

		for f in self.gen_files():
			# Update progress if any.
			i += 1
			if pb:
				pb.update(i)

			# Skip non-existant files (mabye the user removed it already?)
			if not os.path.exists(f):
				continue

			logging.debug("Going to remove file: %s" % f)

			try:
				os.unlink(f)
			except:
				logging.critical("Could not remove file: %s. Do it manually." % f)

			# XXX remove file from database

		if pb:
			pb.finish()

	def run(self):
		files = self.gen_files()

		if not files:
			return

		self.remove_files(_("Cleanup: %s") % self.pkg.name, files)


class ActionScript(Action):
	def run(self):
		pass # XXX TBD


class ActionScriptPreIn(ActionScript):
	pass


class ActionScriptPostIn(ActionScript):
	pass


class ActionScriptPreUn(ActionScript):
	pass


class ActionScriptPostUn(ActionScript):
	pass


class ActionInstall(Action):
	type = "install"

	def extract(self, message, prefix=None):
		logging.debug("Extracting package %s" % self.pkg.friendly_name)

		if prefix is None:
			prefix = self.pakfire.path

		self.pkg.extract(message, prefix=prefix)

		# Create package in the database
		self.local.index.add_package(self.pkg)

	def run(self):
		self.extract(_("Installing: %s") % self.pkg.name)

		self.pakfire.solver.add_package(self.pkg, "installed")


class ActionUpdate(ActionInstall):
	type = "update"

	def run(self):
		self.extract(_("Updating: %s") % self.pkg.name)


class ActionRemove(ActionCleanup):
	type = "remove"

	def run(self):
		files = self.pkg.filelist

		if not files:
			return

		self.remove_files(_("Removing: %s") % self.pkg.name, files)


class Transaction(object):
	action_classes = [
		ActionInstall,
		ActionUpdate,
		ActionRemove,
	]

	def __init__(self, pakfire):
		self.pakfire = pakfire
		self.actions = []

		self.downloads = []

	@classmethod
	def from_solver(cls, pakfire, solver1, solver2):
		# Grab the original transaction object from the solver.
		_transaction = solver2.transaction()

		# Order the objects in the transaction in that way we will run the
		# installation.
		_transaction.order()

		# Create a new instance of our own transaction class.
		transaction = cls(pakfire)

		for step in _transaction.steps():
			action = step.type_s()
			pkg = solver1.id2pkg[step.solvable().id()]

			if not isinstance(pkg, packages.BinaryPackage):
				transaction.downloads.append(pkg)

			for action_cls in cls.action_classes:
				if action_cls.type == action:
					action = action_cls(pakfire, pkg)

			if not isinstance(action, Action):
				raise Exception, "Unknown action required: %s" % action

			transaction.add_action(action)

		return transaction

	def download(self):
		if not self.downloads:
			return

		i = 0
		for pkg in self.downloads:
			i += 1

			# Actually download the package.
			pkg_bin = pkg.download(text="(%2d/%02d): " % (i, len(self.downloads)))

			# Replace the package in all actions where it matches.
			actions = [a for a in self.actions if a.pkg == pkg]

			for action in actions:
				action.pkg = pkg_bin

		# Reset packages to be downloaded.
		self.downloads = []
		print

	@property
	def installs(self):
		return [a for a in self.actions if a.type == "install"]

	@property
	def removes(self):
		return [a for a in self.actions if a.type == "remove"]

	@property
	def updates(self):
		return [a for a in self.actions if a.type == "update"]

	def dump_pkg(self, pkg):
		ret = []

		name = pkg.name
		if len(name) > 21:
			ret.append(" %s" % name)
			name = ""

		ret.append(PKG_DUMP_FORMAT % (name, pkg.arch, pkg.friendly_version,
			pkg.repo.name, util.format_size(pkg.size)))

		return ret

	def dump_pkgs(self, caption, pkgs):
		if not pkgs:
			return []

		s = [caption,]
		for pkg in sorted(pkgs):
			s += self.dump_pkg(pkg)
		s.append("")
		return s

	def dump(self, logger=None):
		if not logger:
			logger = logging.getLogger()

		width = 80
		line = "=" * width

		s = []
		s.append(line)
		s.append(PKG_DUMP_FORMAT % (_("Package"), _("Arch"), _("Version"), _("Repository"), _("Size")))
		s.append(line)

		s += self.dump_pkgs(_("Installing:"), [a.pkg for a in self.installs])
		s += self.dump_pkgs(_("Updating:"), [a.pkg for a in self.updates])
		s += self.dump_pkgs(_("Removing:"), [a.pkg for a in self.removes])

		s.append(_("Transaction Summary"))
		s.append(line)

		format = "%-20s %-4d %s"

		if self.installs:
			s.append(format % (_("Install"), len(self.installs), _("Package(s)")))
		
		if self.updates:
			s.append(format % (_("Updates"), len(self.updates), _("Package(s)")))
		
		if self.removes:
			s.append(format % (_("Remove"), len(self.removes), _("Package(s)")))

		# Calculate the size of all files that need to be downloaded this this
		# transaction.
		download_size = sum([p.size for p in self.downloads])
		if download_size:
			s.append(_("Total download size: %s") % util.format_size(download_size))
		s.append("")

		for line in s:
			logger.info(line)

	def run_action(self, action):
		try:
			action.run()
		except ActionError, e:
			logging.error("Action finished with an error: %s - %s" % (action, e))

	def add_action(self, action):
		logging.debug("New action added: %s" % action)

		self.actions.append(action)

	def remove_action(self, action):
		logging.debug("Removing action: %s" % action)

		self.actions.remove(action)
		for action in self.actions:
			action.remove_dep(action)

	def run(self):
		# Download all packages.
		self.download()

		while True:
			if not [a for a in self.actions]:
				break

			for action in self.actions:
				if action.deps:
					#logging.debug("Skipping %s which cannot be run now." % action)
					continue

				self.run_action(action)
				self.remove_action(action)