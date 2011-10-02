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

import base

from errors import *

Pakfire = base.Pakfire

def install(requires, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.install(requires)

def resolvdep(requires, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.resolvdep(requires)

def localinstall(files, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.localinstall(files)

def remove(what, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.remove(what)

def update(pkgs, check=False, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.update(pkgs, check=check)

def info(patterns, **pakfire_args):
	# Create pakfire instance.
	pakfire = Pakfire(**pakfire_args)

	return pakfire.info(patterns)

def search(pattern, **pakfire_args):
	# Create pakfire instance.
	pakfire = Pakfire(**pakfire_args)

	return pakfire.search(pattern)

def groupinstall(group, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.groupinstall(group)

def grouplist(group, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.grouplist(group)

def _build(pkg, resultdir, **kwargs):
	pakfire = Pakfire(**kwargs)

	return pakfire._build(pkg, resultdir, **kwargs)

def build(pkg, **kwargs):
	return Pakfire.build(pkg, **kwargs)

def shell(pkg, **kwargs):
	return Pakfire.shell(pkg, **kwargs)

def dist(pkgs, resultdirs=None, **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.dist(pkgs, resultdirs=resultdirs)

def provides(patterns, **pakfire_args):
	# Create pakfire instance.
	pakfire = Pakfire(**pakfire_args)

	return pakfire.provides(patterns)

def requires(patterns, **pakfire_args):
	# Create pakfire instance.
	pakfire = Pakfire(**pakfire_args)

	return pakfire.requires(requires)

def repo_create(path, input_paths, type="binary", **pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.repo_create(path, input_paths, type=type)

def repo_list(**pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.repo_list()

def clean_all(**pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.clean_all()

def check(**pakfire_args):
	pakfire = Pakfire(**pakfire_args)

	return pakfire.check()