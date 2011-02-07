#!/usr/bin/python

from __future__ import division

import hashlib

from pakfire.constants import *

def version_compare_epoch(e1, e2):
	return cmp(e1, e2)

def version_compare_version(v1, v2):
	return cmp(v1, v2)

def version_compare_release(r1, r2):
	return cmp(r1, r2)

def version_compare((e1, v1, r1), (e2, v2, r2)):

	ret = version_compare_epoch(e1, e2)
	if not ret == 0:
		return ret

	ret = version_compare_version(v1, v2)
	if not ret == 0:
		return ret

	return version_compare_release(r1, r2)

def text_wrap(s, length=65):
	t = []
	s = s.split()

	l = []
	for word in s:
		l.append(word)

		if len(" ".join(l)) >= length:
			t.append(l)
			l = []

	if l:
		t.append(l)

	return [" ".join(l) for l in t]

def format_size(s):
	units = ("B", "k", "M", "G", "T")
	unit = 0

	while s >= 1024 and unit < len(units):
		s /= 1024
		unit += 1

	return "%d%s" % (int(s), units[unit])

def calc_hash1(filename):
	h = hashlib.sha1()

	f = open(filename)
	buf = f.read(BUFFER_SIZE)
	while buf:
		h.update(buf)
		buf = f.read(BUFFER_SIZE)

	f.close()
	return h.hexdigest()