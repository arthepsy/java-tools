#!/usr/bin/env python
# -*- coding: utf-8 -*-

import imp

with open('ar.mvn.py', 'rb') as fp:
	mvn = imp.load_module('ar_mvn', fp, 'ar.mvn.py', ('.py', 'rb', imp.PY_SOURCE))

def test_version_parsing():
	check_version_parsing("1", 1, 0, 0, 0, None)
	check_version_parsing("1.2", 1, 2, 0, 0, None)
	check_version_parsing("1.2.3", 1, 2, 3, 0, None)
	check_version_parsing("1.2.3-1", 1, 2, 3, 1, None)
	check_version_parsing("1.2.3-alpha-1", 1, 2, 3, 0, "alpha-1")
	check_version_parsing("1.2-alpha-1", 1, 2, 0, 0, "alpha-1")
	check_version_parsing("1.2-alpha-1-20050205.060708-1", 1, 2, 0, 0, "alpha-1-20050205.060708-1")
	check_version_parsing("RELEASE", 0, 0, 0, 0, "RELEASE")
	check_version_parsing("2.0-1", 2, 0, 0, 1, None)
	
	# 0 at the beginning of a number has a special handling
	check_version_parsing("02", 0, 0, 0, 0, "02")
	check_version_parsing("0.09", 0, 0, 0, 0, "0.09")
	check_version_parsing("0.2.09", 0, 0, 0, 0, "0.2.09")
	check_version_parsing("2.0-01", 2, 0, 0, 0, "01")
	
	# version schemes not really supported: fully transformed as qualifier
	check_version_parsing("1.0.1b", 0, 0, 0, 0, "1.0.1b")
	check_version_parsing("1.0M2", 0, 0, 0, 0, "1.0M2")
	check_version_parsing("1.0RC2", 0, 0, 0, 0, "1.0RC2")
	check_version_parsing("1.1.2.beta1", 1, 1, 2, 0, "beta1")
	check_version_parsing("1.7.3.beta1", 1, 7, 3, 0, "beta1")
	check_version_parsing("1.7.3.0", 0, 0, 0, 0, "1.7.3.0")
	check_version_parsing("1.7.3.0-1", 0, 0, 0, 0, "1.7.3.0-1")
	check_version_parsing("PATCH-1193602", 0, 0, 0, 0, "PATCH-1193602")
	check_version_parsing("5.0.0alpha-2006020117", 0, 0, 0, 0, "5.0.0alpha-2006020117")
	check_version_parsing("1.0.0.-SNAPSHOT", 0, 0, 0, 0, "1.0.0.-SNAPSHOT")
	check_version_parsing("1..0-SNAPSHOT", 0, 0, 0, 0, "1..0-SNAPSHOT")
	check_version_parsing("1.0.-SNAPSHOT", 0, 0, 0, 0, "1.0.-SNAPSHOT")
	check_version_parsing(".1.0-SNAPSHOT", 0, 0, 0, 0, ".1.0-SNAPSHOT")
	
	check_version_parsing("1.2.3.200705301630", 0, 0, 0, 0, "1.2.3.200705301630")
	check_version_parsing("1.2.3-200705301630", 1, 2, 3, 0, "200705301630")

def check_version_parsing(version, major, minor, incremental, build_number, qualifier):
	av = mvn.Pom.ArtifactVersion(version)
	parsed = "'{0}' parsed as ('{1}', '{2}', '{3}', '{4}', '{5}'), ".format(version, av.get_major(), av.get_minor(), av.get_incremental(), av.get_build_number(), av.get_qualifier())
	assert major == av.get_major(), parsed + "check major version"
	assert minor == av.get_minor(), parsed + "check minor version"
	assert incremental == av.get_incremental(), parsed + "check incremental version"
	assert build_number == av.get_build_number(), parsed + "check build number .. [{0}][{1}]".format(build_number, av.get_build_number())
	assert qualifier == av.get_qualifier(), parsed + "check qualifier"
	assert major == av.get_major(), parsed + "check major version"
	#assert version == str(av), parsed + "check string value"

if __name__ == '__main__':
	test_version_parsing()
