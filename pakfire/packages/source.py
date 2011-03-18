#!/usr/bin/python

from file import FilePackage

class SourcePackage(FilePackage):
	@property
	def arch(self):
		return "src"

	def extract(self, path):
		pass

	@property
	def requires(self):
		"""
			Return the requirements for the build.
		"""
		return self.metadata.get("PKG_REQUIRES", "").split()

