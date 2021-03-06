#!/usr/bin/python
###############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2011 Pakfire development team                                 #
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

import os
import re
import shutil
import socket
import tarfile
import tempfile
import uuid

from urlgrabber.grabber import URLGrabber, URLGrabError
from urlgrabber.progress import TextMeter

import lexer
import packager

import logging
log = logging.getLogger("pakfire")

import pakfire.downloader as downloader
import pakfire.util as util

from base import Package

from pakfire.constants import *
from pakfire.i18n import _
from pakfire.system import system

class MakefileBase(Package):
	def __init__(self, pakfire, filename=None, lines=None):
		Package.__init__(self, pakfire)

		# Update environment.
		environ = self.pakfire.distro.environ
		environ.update({
			"PARALLELISMFLAGS" : "-j%d" % system.parallelism,
		})

		if filename:
			self.filename = os.path.abspath(filename)
			environ["BASEDIR"] = os.path.dirname(self.filename)

			# Open and parse the makefile.
			self.lexer = lexer.RootLexer.open(self.filename, environ=environ)

		else:
			self.filename = None
			self.lexer = lexer.RootLexer(lines, environ=environ)

	@property
	def package_filename(self):
		return PACKAGE_FILENAME_FMT % {
			"arch"    : self.arch,
			"ext"     : PACKAGE_EXTENSION,
			"name"    : self.name,
			"release" : self.release,
			"version" : self.version,
		}

	def lint(self):
		errors = []

		if not self.name:
			errors.append(_("Package name is undefined."))

		if not self.version:
			errors.append(_("Package version is undefined."))

		# XXX to do...

		return errors

	@property
	def name(self):
		return self.lexer.get_var("name")

	@property
	def epoch(self):
		epoch = self.lexer.get_var("epoch")
		if not epoch:
			return 0

		return int(epoch)

	@property
	def version(self):
		return self.lexer.get_var("version")

	@property
	def release(self):
		release = self.lexer.get_var("release")
		assert release

		tag = self.lexer.get_var("DISTRO_DISTTAG")
		assert tag

		return ".".join((release, tag))

	@property
	def summary(self):
		return self.lexer.get_var("summary")

	@property
	def description(self):
		description = self.lexer.get_var("description")

		# Replace all backslashes at the end of a line.
		return description.replace("\\\n", "\n")

	@property
	def groups(self):
		groups = self.lexer.get_var("groups").split()

		return sorted(groups)

	@property
	def url(self):
		return self.lexer.get_var("url")

	@property
	def license(self):
		return self.lexer.get_var("license")

	@property
	def maintainer(self):
		maintainer = self.lexer.get_var("maintainer")

		if not maintainer:
			maintainer = self.lexer.get_var("DISTRO_MAINTAINER")

		return maintainer

	@property
	def vendor(self):
		return self.lexer.get_var("DISTRO_VENDOR")

	@property
	def buildroot(self):
		return self.lexer.get_var("BUILDROOT")

	@property
	def sourcedir(self):
		return self.lexer.get_var("DIR_SRC")

	@property
	def build_host(self):
		return socket.gethostname()

	# XXX build_id and build_time are used to create a source package

	@property
	def build_id(self):
		# XXX todo
		# Not existant for Makefiles
		return None

	@property
	def build_time(self):
		# XXX todo
		# Not existant for Makefiles
		return None

	@property
	def supported_arches(self):
		"""
			These are the supported arches. Which means, packages of these
			architectures can be built out of this source package.
		"""
		# If the package architecture is "noarch", the package
		# needs only to be built for that.
		if self.lexer.get_var("arch", "all") == "noarch":
			return "noarch"

		return self.lexer.get_var("sup_arches", "all")


class Makefile(MakefileBase):
	@property
	def uuid(self):
		if self.filename:
			hash1 = util.calc_hash1(self.filename)

			# Return UUID version 5 (SHA1 hash)
			return "%8s-%4s-5%3s-%4s-%11s" % \
				(hash1[0:8], hash1[9:13], hash1[14:17], hash1[18:22], hash1[23:34])

		return "" # XXX What to do here?

	@property
	def path(self):
		if self.filename:
			return os.path.dirname(self.filename)

	@property
	def arch(self):
		return "src"

	@property
	def packages(self):
		pkgs = []

		for lexer in self.lexer.packages:
			name = lexer.get_var("_name")

			pkg = MakefilePackage(self.pakfire, name, lexer)
			pkgs.append(pkg)

		return pkgs

	@property
	def source_dl(self):
		dls = []

		if self.pakfire.distro.source_dl:
			dls.append(self.pakfire.distro.source_dl)

		for dl in self.lexer.get_var("source_dl").split():
			dls.append(dl)

		return dls

	def download(self):
		"""
			Download all external sources and return a list with the local
			copies.
		"""
		# Download source files.
		grabber = downloader.SourceDownloader(self.pakfire,
			mirrors=self.source_dl)

		return grabber.download(self.sources)

	def dist(self, resultdir):
		"""
			Create a source package.
		"""
		p = packager.SourcePackager(self.pakfire, self)
		return p.run(resultdir)

	def dump(self, *args, **kwargs):
		dump = MakefileBase.dump(self, *args, **kwargs)
		dump = dump.splitlines()

		#dump += ["", _("Containing the following binary packages:"),]
		#
		#for pkg in self.packages:
		#	_dump = pkg.dump(*args, **kwargs)
		#
		#	for line in _dump.splitlines():
		#		dump.append("  %s" % line)
		#	dump.append("")

		return "\n".join(dump)

	def get_buildscript(self, stage):
		return self.lexer.build.get_var("_%s" % stage)

	@property
	def prerequires(self):
		return []

	@property
	def requires(self):
		reqs = []

		for line in self.lexer.build.get_var("requires", "").splitlines():
			reqs += [r.strip() for r in line.split(",")]

		return self.filter_deps(reqs)

	@property
	def provides(self):
		return []

	@property
	def obsoletes(self):
		return []

	@property
	def conflicts(self):
		return []

	@property
	def recommends(self):
		return []

	@property
	def suggests(self):
		return []

	@property
	def files(self):
		if not self.filename:
			return []

		files = []
		basedir = os.path.dirname(self.filename)

		for dirs, subdirs, _files in os.walk(basedir):
			for f in _files:
				files.append(os.path.join(dirs, f))

		return files

	@property
	def sources(self):
		return self.lexer.get_var("sources").split()

	@property
	def exports(self):
		exports = {}

		# Include quality agent exports.
		exports.update(self.lexer.quality_agent.exports)

		for export in self.lexer.build.exports:
			exports[export] = self.lexer.build.get_var(export)

		return exports

	def extract(self, message=None, prefix=None):
		# XXX neeed to make this waaaaaaaaaay better.

		files = self.files

		# Load progressbar.
		pb = None
		if message:
			message = "%-10s : %s" % (message, self.friendly_name)
			pb = util.make_progress(message, len(files), eta=False)

		dir_len = len(os.path.dirname(self.filename))

		# Copy all files that belong to the package
		i = 0
		for f in files:
			if pb:
				i += 1
				pb.update(i)

			_f = f[dir_len:]
			log.debug("%s/%s" % (prefix, _f))
	
			path = "%s/%s" % (prefix, _f)

			path_dir = os.path.dirname(path)
			if not os.path.exists(path_dir):
				os.makedirs(path_dir)

			shutil.copy2(f, path)

		if pb:
			pb.finish()

		# Download source files.
		for _filename in self.download():
			filename = "%s/files/%s" % (prefix, os.path.basename(_filename))
			dirname = os.path.dirname(filename)

			if not os.path.exists(dirname):
				os.makedirs(dirname)

			shutil.copy2(_filename, filename)


class MakefilePackage(MakefileBase):
	def __init__(self, pakfire, name, lexer):
		Package.__init__(self, pakfire)

		self._name = name
		self.lexer = lexer

		# Save filelist.
		self._filelist = set()

		# Store additional dependencies in here.
		self._dependencies = {}

		# Generate a random identifier.
		self._uuid = "%s" % uuid.uuid4()

	@property
	def name(self):
		return self._name

	@property
	def arch(self):
		return self.lexer.get_var("arch", "%{DISTRO_ARCH}")

	@property
	def configfiles(self):
		return self.lexer.get_var("configfiles").split()

	@property
	def datafiles(self):
		files = self.lexer.get_var("datafiles")
		return files.split()

	@property
	def files(self):
		return self.lexer.get_var("files").split()

	@property
	def uuid(self):
		return self._uuid

	def track_dependencies(self, builder, path):
		# Build filelist with all files that have been installed.
		f = tempfile.NamedTemporaryFile(mode="w", delete=False)
		filelist = f.name

		try:
			for dir, subdirs, files in os.walk(path):
				f.write("%s\n" % dir)

				for file in files:
					file = os.path.join(dir, file)
					f.write("%s\n" % file)

					file = "/%s" % os.path.relpath(file, path)
					self._filelist.add(file)
			f.close()

			log.info(_("Searching for automatic dependencies for %s...") % self.friendly_name)

			# Search for provides.
			res = builder.run_script("find-provides", path, filelist)
			provides = set(res.splitlines())

			# Search for requires.
			res = builder.run_script("find-requires", path, filelist)
			requires = set(res.splitlines()) - provides

		finally:
			os.unlink(filelist)

		self._dependencies["provides"] = provides
		self._dependencies["requires"] = requires

		# Filter dependencies.
		for key in ("prerequires", "requires", "provides", "conflicts", "obsoletes"):
			# Make sure this is a list.
			try:
				self._dependencies[key] = list(self._dependencies[key])
			except KeyError:
				self._dependencies[key] = []

			# Filter out unwanted elements.
			self._dependencies[key] = self.filter_deps(
				self._dependencies[key], self.lexer.get_var("filter_%s" % key)
			)

	def update_prerequires(self, prerequires):
		if not prerequires:
			return

		_prerequires = self._dependencies.get("prerequires", [])
		_prerequires = set(_prerequires + prerequires)

		self._dependencies["prerequires"] = list(prerequires)

	@staticmethod
	def filter_deps(deps, filters):
		if not filters:
			return deps

		_filters = []
		filtered_deps = []

		# Compile all filters.
		for filter in filters.splitlines():
			# Convert to raw string to make escaping characters
			# easy to the user.
			try:
				filter = "%r" % filter
				_filter = re.compile(filter[1:-1])
			except re.error:
				log.warning(_("Regular experession is invalid and has been skipped: %s") % filter)
				continue

			_filters.append(_filter)

		filters = _filters

		for dep in deps:
			filtered = False
			for filter in filters:
				# Search for a match anywhere in the line.
				m = re.search(filter, dep)
				if not m:
					continue

				# Let the user know what has been done.
				log.info(_("Filter '%(pattern)s' filtered %(dep)s.") % \
					{ "pattern" : filter.pattern, "dep" : dep })

				# Yes, we found a match.
				filtered = True
				break

			if not filtered:
				filtered_deps.append(dep)

		return filtered_deps

	def get_deps(self, key):
		# Collect all dependencies that were set in the makefile by the user.
		deps = self.lexer.get_var(key).splitlines()

		# Collect all dependencies that were discovered by the tracker.
		deps += self._dependencies.get(key, [])

		# Remove duplicates and sort the data.
		deps = set(deps)
		deps = list(deps)
		deps.sort()

		# Add the UUID of the package as a provides.
		if key == "provides":
			deps.append("uuid(%s)" % self.uuid)

		return deps

	@property
	def prerequires(self):
		ret = []

		# Cache the provides and as a set for faster searching.
		provides = set(self.provides)

		for dep in self.get_deps("prerequires"):
			# Skip all prerequires that are provided by a file in this package.
			if dep.startswith("/") and dep in self._filelist:
				continue

			if dep in self.provides:
				continue

			ret.append(dep)

		return ret

	@property
	def requires(self):
		# Make sure that no self-provides are in the list
		# of requirements.
		ret = []

		# Cache the provides and as a set for faster searching.
		provides = set(self.provides)

		for dep in self.get_deps("requires"):
			# Skip requires that are provided by a file in this package.
			if dep.startswith("/") and dep in self._filelist:
				continue

			# Skip all other kinds of provides.
			if dep in provides:
				continue

			ret.append(dep)

		return ret

	@property
	def provides(self):
		return self.get_deps("provides")

	@property
	def obsoletes(self):
		return self.get_deps("obsoletes")

	@property
	def conflicts(self):
		return self.get_deps("conflicts")

	@property
	def recommends(self):
		return self.get_deps("recommends")

	@property
	def suggests(self):
		return self.get_deps("suggests")

	def get_scriptlet(self, type):
		return self.lexer.get_scriptlet(type)

	@property
	def inst_size(self):
		# The size of this is unknown.
		return 0
