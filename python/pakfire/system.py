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

from __future__ import division

import os

class Mountpoints(object):
	def __init__(self, pakfire, root="/"):
		self.pakfire = pakfire

		self._mountpoints = []

		# Scan for all mountpoints on the system.
		self._scan(root)

	def __iter__(self):
		return iter(self._mountpoints)

	def _scan(self, root):
		# Get the real path of root.
		root = os.path.realpath(root)

		# If root is not equal to /, we are in a chroot and
		# our root must be a mountpoint to count files.
		if not root == "/":
			mp = Mountpoint(self.pakfire, "/", root=root)
			self._mountpoints.append(mp)

		f = open("/proc/mounts")

		for line in f.readlines():
			line = line.split()

			# The mountpoint is the second argument.
			mountpoint = line[1]

			# Skip all mountpoints that are not in our root directory.
			if not mountpoint.startswith(root):
				continue

			mountpoint = os.path.relpath(mountpoint, root)
			if mountpoint == ".":
				mountpoint = "/"
			else:
				mountpoint = os.path.join("/", mountpoint)

			mp = Mountpoint(self.pakfire, mountpoint, root=root)

			if not mp in self._mountpoints:
				self._mountpoints.append(mp)

		f.close()

		# Sort all mountpoints for better searching.
		self._mountpoints.sort()

	def add_pkg(self, pkg):
		for file in pkg.filelist:
			self.add(file)

	def rem_pkg(self, pkg):
		for file in pkg.filelist:
			self.rem(file)

	def add(self, file):
		for mp in reversed(self._mountpoints):
			# Check if the file is located on this mountpoint.
			if not file.name.startswith(mp.path):
				continue

			# Add file to this mountpoint.
			mp.add(file)
			break

	def rem(self, file):
		for mp in reversed(self._mountpoints):
			# Check if the file is located on this mountpoint.
			if not file.name.startswith(mp.path):
				continue

			# Remove file from this mountpoint.
			mp.rem(file)
			break


class Mountpoint(object):
	def __init__(self, pakfire, path, root="/"):
		self.pakfire = pakfire
		self.path = path
		self.root = root

		# Cache the statvfs call of the mountpoint.
		self.__stat = None

		# Save the amount of data that is used or freed.
		self.disk_usage = 0

	def __cmp__(self, other):
		return cmp(self.fullpath, other.fullpath)

	@property
	def fullpath(self):
		path = self.path
		while path.startswith("/"):
			path = path[1:]

		return os.path.join(self.root, path)

	@property
	def stat(self):
		if self.__stat is None:
			# Find the next mountpoint, because we cannot
			# statvfs any path in the FS.
			path = os.path.realpath(self.fullpath)

			# Walk to root until we find a mountpoint.
			while not os.path.ismount(path):
				path = os.path.dirname(path)

			# See what we can get.
			self.__stat = os.statvfs(path)

		return self.__stat

	@property
	def free(self):
		return self.stat.f_bavail * self.stat.f_bsize

	@property
	def space_needed(self):
		if self.disk_usage > 0:
			return self.disk_usage

		return 0

	@property
	def space_left(self):
		return self.free - self.space_needed

	def add(self, file):
		assert file.name.startswith(self.path)

		# Round filesize to 4k blocks.
		block_size = 4096

		blocks = file.size // block_size
		if file.size % block_size:
			blocks += 1

		self.disk_usage += blocks * block_size

	def rem(self, file):
		assert file.name.startswith(self.path)

		self.disk_usage += file.size