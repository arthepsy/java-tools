#!/usr/bin/env python
# -*- coding: utf-8 -*-

import imp, pytest

with open('ar.mvn.py', 'rb') as fp:
	mvn = imp.load_module('ar_mvn', fp, 'ar.mvn.py', ('.py', 'rb', imp.PY_SOURCE))

class Test_ArtifactVersion(object):
	
	def test_version_parsing(self):
		self.check_version_parsing("1", 1, 0, 0, 0, None)
		self.check_version_parsing("1.2", 1, 2, 0, 0, None)
		self.check_version_parsing("1.2.3", 1, 2, 3, 0, None)
		self.check_version_parsing("1.2.3-1", 1, 2, 3, 1, None)
		self.check_version_parsing("1.2.3-alpha-1", 1, 2, 3, 0, "alpha-1")
		self.check_version_parsing("1.2-alpha-1", 1, 2, 0, 0, "alpha-1")
		self.check_version_parsing("1.2-alpha-1-20050205.060708-1", 1, 2, 0, 0, "alpha-1-20050205.060708-1")
		self.check_version_parsing("RELEASE", 0, 0, 0, 0, "RELEASE")
		self.check_version_parsing("2.0-1", 2, 0, 0, 1, None)
		
		# 0 at the beginning of a number has a special handling
		self.check_version_parsing("02", 0, 0, 0, 0, "02")
		self.check_version_parsing("0.09", 0, 0, 0, 0, "0.09")
		self.check_version_parsing("0.2.09", 0, 0, 0, 0, "0.2.09")
		self.check_version_parsing("2.0-01", 2, 0, 0, 0, "01")
		
		# version schemes not really supported: fully transformed as qualifier
		self.check_version_parsing("1.0.1b", 0, 0, 0, 0, "1.0.1b")
		self.check_version_parsing("1.0M2", 0, 0, 0, 0, "1.0M2")
		self.check_version_parsing("1.0RC2", 0, 0, 0, 0, "1.0RC2")
		self.check_version_parsing("1.1.2.beta1", 1, 1, 2, 0, "beta1")
		self.check_version_parsing("1.7.3.beta1", 1, 7, 3, 0, "beta1")
		self.check_version_parsing("1.7.3.0", 0, 0, 0, 0, "1.7.3.0")
		self.check_version_parsing("1.7.3.0-1", 0, 0, 0, 0, "1.7.3.0-1")
		self.check_version_parsing("PATCH-1193602", 0, 0, 0, 0, "PATCH-1193602")
		self.check_version_parsing("5.0.0alpha-2006020117", 0, 0, 0, 0, "5.0.0alpha-2006020117")
		self.check_version_parsing("1.0.0.-SNAPSHOT", 0, 0, 0, 0, "1.0.0.-SNAPSHOT")
		self.check_version_parsing("1..0-SNAPSHOT", 0, 0, 0, 0, "1..0-SNAPSHOT")
		self.check_version_parsing("1.0.-SNAPSHOT", 0, 0, 0, 0, "1.0.-SNAPSHOT")
		self.check_version_parsing(".1.0-SNAPSHOT", 0, 0, 0, 0, ".1.0-SNAPSHOT")
		
		self.check_version_parsing("1.2.3.200705301630", 0, 0, 0, 0, "1.2.3.200705301630")
		self.check_version_parsing("1.2.3-200705301630", 1, 2, 3, 0, "200705301630")
	
	def test_version_comparing(self):
		self.assert_version_equal("1", "1")
		self.assert_version_older("1", "2")
		self.assert_version_older("1.5", "2")
		self.assert_version_older("1", "2.5")
		self.assert_version_equal("1", "1.0")
		self.assert_version_equal("1", "1.0.0")
		self.assert_version_older("1.0", "1.1")
		self.assert_version_older("1.1", "1.2")
		self.assert_version_older("1.0.0", "1.1")
		self.assert_version_older("1.1", "1.2.0")
		
		self.assert_version_older("1.1.2.alpha1", "1.1.2")
		self.assert_version_older("1.1.2.alpha1", "1.1.2.beta1")
		self.assert_version_older("1.1.2.beta1", "1.2")
		
		self.assert_version_older("1.0-alpha-1", "1.0")
		self.assert_version_older("1.0-alpha-1", "1.0-alpha-2")
		self.assert_version_older("1.0-alpha-2", "1.0-alpha-15")
		self.assert_version_older("1.0-alpha-1", "1.0-beta-1")
		
		self.assert_version_older("1.0-beta-1", "1.0-SNAPSHOT")
		self.assert_version_older("1.0-SNAPSHOT", "1.0")
		self.assert_version_older("1.0-alpha-1-SNAPSHOT", "1.0-alpha-1")
		
		self.assert_version_older("1.0", "1.0-1")
		self.assert_version_older("1.0-1", "1.0-2")
		self.assert_version_equal("2.0-0", "2.0")
		self.assert_version_older("2.0", "2.0-1")
		self.assert_version_older("2.0.0", "2.0-1")
		self.assert_version_older("2.0-1", "2.0.1")
		
		self.assert_version_older("2.0.1-klm", "2.0.1-lmn")
		self.assert_version_older("2.0.1", "2.0.1-xyz")
		self.assert_version_older("2.0.1-xyz-1", "2.0.1-1-xyz")
		
		self.assert_version_older("2.0.1", "2.0.1-123")
		self.assert_version_older("2.0.1-xyz", "2.0.1-123")
		
		self.assert_version_older("1.2.3-10000000000", "1.2.3-10000000001")
		self.assert_version_older("1.2.3-1", "1.2.3-10000000001")
		self.assert_version_older("2.3.0-v200706262000", "2.3.0-v200706262130") # org.eclipse:emf:2.3.0-v200706262000
		# org.eclipse.wst.common_core.feature_2.0.0.v200706041905-7C78EK9E_EkMNfNOd2d8qq
		self.assert_version_older("2.0.0.v200706041905-7C78EK9E_EkMNfNOd2d8qq", "2.0.0.v200706041906-7C78EK9E_EkMNfNOd2d8qq")
	
	def test_version_snapshot_comparing(self):
		self.assert_version_equal("1-SNAPSHOT", "1-SNAPSHOT")
		self.assert_version_older("1-SNAPSHOT", "2-SNAPSHOT")
		self.assert_version_older("1.5-SNAPSHOT", "2-SNAPSHOT")
		self.assert_version_older("1-SNAPSHOT", "2.5-SNAPSHOT")
		self.assert_version_equal("1-SNAPSHOT", "1.0-SNAPSHOT")
		self.assert_version_equal("1-SNAPSHOT", "1.0.0-SNAPSHOT")
		self.assert_version_older("1.0-SNAPSHOT", "1.1-SNAPSHOT")
		self.assert_version_older("1.1-SNAPSHOT", "1.2-SNAPSHOT")
		self.assert_version_older("1.0.0-SNAPSHOT", "1.1-SNAPSHOT")
		self.assert_version_older("1.1-SNAPSHOT", "1.2.0-SNAPSHOT")
		
		self.assert_version_older("1.0-alpha-1-SNAPSHOT", "1.0-SNAPSHOT")
		self.assert_version_older("1.0-alpha-1-SNAPSHOT", "1.0-alpha-2-SNAPSHOT")
		self.assert_version_older("1.0-alpha-1-SNAPSHOT", "1.0-beta-1-SNAPSHOT")
		
		self.assert_version_older("1.0-beta-1-SNAPSHOT", "1.0-SNAPSHOT-SNAPSHOT")
		self.assert_version_older("1.0-SNAPSHOT-SNAPSHOT", "1.0-SNAPSHOT")
		self.assert_version_older("1.0-alpha-1-SNAPSHOT-SNAPSHOT", "1.0-alpha-1-SNAPSHOT")
		
		self.assert_version_older("1.0-SNAPSHOT", "1.0-1-SNAPSHOT")
		self.assert_version_older("1.0-1-SNAPSHOT", "1.0-2-SNAPSHOT")
		# self.assert_version_equal("2.0-0-SNAPSHOT", "2.0-SNAPSHOT")
		self.assert_version_older("2.0-SNAPSHOT", "2.0-1-SNAPSHOT")
		self.assert_version_older("2.0.0-SNAPSHOT", "2.0-1-SNAPSHOT")
		self.assert_version_older("2.0-1-SNAPSHOT", "2.0.1-SNAPSHOT")
		
		self.assert_version_older("2.0.1-klm-SNAPSHOT", "2.0.1-lmn-SNAPSHOT")
		# self.assert_version_older("2.0.1-xyz-SNAPSHOT", "2.0.1-SNAPSHOT")
		self.assert_version_older("2.0.1-SNAPSHOT", "2.0.1-123-SNAPSHOT")
		self.assert_version_older("2.0.1-xyz-SNAPSHOT", "2.0.1-123-SNAPSHOT")
	
	def test_snapshot_vs_releases(self):
		self.assert_version_older("1.0-RC1", "1.0-SNAPSHOT")
		self.assert_version_older("1.0-rc1", "1.0-SNAPSHOT")
		self.assert_version_older("1.0-rc-1", "1.0-SNAPSHOT")
	
	def test_hash_code(self):
		v1 = mvn.Pom.ArtifactVersion("1")
		v2 = mvn.Pom.ArtifactVersion("1.0")
		assert v1 == v2
		assert hash(v1) == hash(v2)
	
	def test_equals_null_safe(self):
		assert (mvn.Pom.ArtifactVersion("1") is None) == False
	
	def test_equals_type_safe(self):
		assert (mvn.Pom.ArtifactVersion("1") is "non-an-artifact-version-instance") == False
	
	def check_version_parsing(self, version, major, minor, incremental, build_number, qualifier):
		av = mvn.Pom.ArtifactVersion(version)
		parsed = "'{0}' parsed as ('{1}', '{2}', '{3}', '{4}', '{5}'), ".format(version, av.major, av.minor, av.incremental, av.build_number, av.qualifier)
		assert major == av.major, parsed + "check major version"
		assert minor == av.minor, parsed + "check minor version"
		assert incremental == av.incremental, parsed + "check incremental version"
		assert build_number == av.build_number, parsed + "check build number .. [{0}][{1}]".format(build_number, av.build_number)
		assert qualifier == av.qualifier, parsed + "check qualifier"
		assert major == av.major, parsed + "check major version"
		assert version == str(av), parsed + "check string value"
	
	def assert_version_older(self, left, right):
		assert mvn.Pom.ArtifactVersion(left).compare_to(mvn.Pom.ArtifactVersion(right)) < 0, left + " should be older than " + right 
		assert mvn.Pom.ArtifactVersion(right).compare_to(mvn.Pom.ArtifactVersion(left)) > 0, right + " should be newer than " + left 
	
	def assert_version_equal(self, left, right):
		assert mvn.Pom.ArtifactVersion(left).compare_to(mvn.Pom.ArtifactVersion(right)) == 0, left + " should be equal to " + right 
		assert mvn.Pom.ArtifactVersion(right).compare_to(mvn.Pom.ArtifactVersion(left)) == 0, right + " should be equal to " + left 

class Test_VersionComparer(object):
	def test_versions_qualifier(self):
		versions = ["1-alpha2snapshot", "1-alpha2", "1-alpha-123", "1-beta-2", "1-beta123", "1-m2", "1-m11", "1-rc", "1-cr2",
		            "1-rc123", "1-SNAPSHOT", "1", "1-sp", "1-sp2", "1-sp123", "1-abc", "1-def", "1-pom-1", "1-1-snapshot",
		            "1-1", "1-2", "1-123"]
		self.check_versions_order_list(versions)
	
	def test_versions_number(self):
		versions = ["2.0", "2-1", "2.0.a", "2.0.0.a", "2.0.2", "2.0.123", "2.1.0", "2.1-a", "2.1b", "2.1-c", "2.1-1", "2.1.0.1",
		            "2.2", "2.123", "11.a2", "11.a11", "11.b2", "11.b11", "11.m2", "11.m11", "11", "11.a", "11b", "11c", "11m"]
		self.check_versions_order_list(versions)
	
	def test_versions_equal(self):
		self.new_comparer("1.0-alpha")
		self.check_versions_equal("1", "1")
		self.check_versions_equal("1", "1.0")
		self.check_versions_equal("1", "1.0.0")
		self.check_versions_equal("1.0", "1.0.0")
		self.check_versions_equal("1", "1-0")
		self.check_versions_equal("1", "1.0-0")
		self.check_versions_equal("1.0", "1.0-0")
		# no separator between number and character
		self.check_versions_equal("1a", "1-a")
		self.check_versions_equal("1a", "1.0-a")
		self.check_versions_equal("1a", "1.0.0-a")
		self.check_versions_equal("1.0a", "1-a")
		self.check_versions_equal("1.0.0a", "1-a")
		self.check_versions_equal("1x", "1-x")
		self.check_versions_equal("1x", "1.0-x")
		self.check_versions_equal("1x", "1.0.0-x")
		self.check_versions_equal("1.0x", "1-x")
		self.check_versions_equal("1.0.0x", "1-x")
		
		# aliases
		self.check_versions_equal("1ga", "1")
		self.check_versions_equal("1final", "1")
		self.check_versions_equal("1cr", "1rc")
		
		# special "aliases" a, b and m for alpha, beta and milestone
		self.check_versions_equal("1a1", "1-alpha-1")
		self.check_versions_equal("1b2", "1-beta-2")
		self.check_versions_equal("1m3", "1-milestone-3")
		
		# case insensitive
		self.check_versions_equal("1X", "1x")
		self.check_versions_equal("1A", "1a")
		self.check_versions_equal("1B", "1b")
		self.check_versions_equal("1M", "1m")
		self.check_versions_equal("1Ga", "1")
		self.check_versions_equal("1GA", "1")
		self.check_versions_equal("1Final", "1")
		self.check_versions_equal("1FinaL", "1")
		self.check_versions_equal("1FINAL", "1")
		self.check_versions_equal("1Cr", "1Rc")
		self.check_versions_equal("1cR", "1rC")
		self.check_versions_equal("1m3", "1Milestone3")
		self.check_versions_equal("1m3", "1MileStone3")
		self.check_versions_equal("1m3", "1MILESTONE3")
	
	def test_version_comparing(self):
		self.check_versions_order("1", "2")
		self.check_versions_order("1.5", "2")
		self.check_versions_order("1", "2.5")
		self.check_versions_order("1.0", "1.1")
		self.check_versions_order("1.1", "1.2")
		self.check_versions_order("1.0.0", "1.1")
		self.check_versions_order("1.0.1", "1.1")
		self.check_versions_order("1.1", "1.2.0")
		
		self.check_versions_order("1.0-alpha-1", "1.0")
		self.check_versions_order("1.0-alpha-1", "1.0-alpha-2")
		self.check_versions_order("1.0-alpha-1", "1.0-beta-1")
		
		self.check_versions_order("1.0-beta-1", "1.0-SNAPSHOT")
		self.check_versions_order("1.0-SNAPSHOT", "1.0")
		self.check_versions_order("1.0-alpha-1-SNAPSHOT", "1.0-alpha-1")
		
		self.check_versions_order("1.0", "1.0-1")
		self.check_versions_order("1.0-1", "1.0-2")
		self.check_versions_order("1.0.0", "1.0-1")
		
		self.check_versions_order("2.0-1", "2.0.1")
		self.check_versions_order("2.0.1-klm", "2.0.1-lmn")
		self.check_versions_order("2.0.1", "2.0.1-xyz")
		
		self.check_versions_order("2.0.1", "2.0.1-123")
		self.check_versions_order("2.0.1-xyz", "2.0.1-123")
	
	def test_MNG5568(self):
		a = "6.1.0";
		b = "6.1.0rc3";
		c = "6.1H.5-beta"; # this is the unusual version string, with 'H' in the middle
		
		self.check_versions_order(b, a) # classical
		self.check_versions_order(b, c) # now b < c, but before MNG-5568, was b > c
		self.check_versions_order(a, c)
	
	def test_reuse(self):
		c1 = mvn.Pom.VersionComparer("1")
		c1._parse("2")
		c2 = mvn.Pom.VersionComparer("2");
		assert c1 == c2, "reused instance should be equivalent to new instance"
	
	def new_comparer(self, version):
		ret = mvn.Pom.VersionComparer(version)
		canonical = ret.canonical
		parsed_canonical = mvn.Pom.VersionComparer(canonical).canonical
		#print "canonical( " + version + " ) = " + canonical
		assert canonical == parsed_canonical, "canonical( " + version + " ) = " + canonical + " -> canonical: " + parsedCanonical
		return ret
	
	def check_versions_equal(self, v1, v2):
		c1 = self.new_comparer(v1);
		c2 = self.new_comparer(v2)
		assert c1.compare_to(c2) == 0, "expected " + v1 + " == " + v2
		assert c2.compare_to(c1) == 0, "expected " + v2 + " == " + v1
		assert hash(c1) == hash(c2), "expected same hashcode for " + v1 + " and " + v2
		assert c1 == c2, "expected " + v1 + " == " + v2
		assert c2 == c1, "expected " + v2 + " == " + v1
	
	def check_versions_order(self, v1, v2):
		c1 = self.new_comparer(v1)
		c2 = self.new_comparer(v2)
		assert c1.compare_to(c2) < 0, "expected " + v1 + " < " + v2
		assert c2.compare_to(c1) > 0, "expected " + v2 + " > " + v1
	
	def check_versions_order_list(self, versions):
		c = []
		l = len(versions)
		for version in versions:
			c.append(self.new_comparer(version))
		for i in xrange(1, l):
			low = c[i - 1]
			for j in xrange(i, l):
				high = c[j]
				assert low.compare_to(high) < 0,  "expected " + low + " < " + high
				assert high.compare_to(low) > 0,  "expected " + high + " > " + low

class Test_VersionRange(object):
	CHECK_NUM_RESTRICTIONS = "check number of restrictions";
	CHECK_UPPER_BOUND = "check upper bound";
	CHECK_UPPER_BOUND_INCLUSIVE = "check upper bound is inclusive";
	CHECK_LOWER_BOUND = "check lower bound";
	CHECK_LOWER_BOUND_INCLUSIVE = "check lower bound is inclusive";
	CHECK_VERSION_RECOMMENDATION = "check version recommended";
	CHECK_SELECTED_VERSION_KNOWN = "check selected version known";
	CHECK_SELECTED_VERSION = "check selected version";
	
	def test_range(self):
		self.single_range_test('(,1.0]', 1, None, False, '1.0', True, None, False, None)
		self.single_range_test('1.0', 1, None, False, None, False, '1.0', True, '1.0')
		self.single_range_test('[1.0]', 1, '1.0', True, '1.0', True, None, False, None)
		self.single_range_test('[1.2,1.3]', 1, '1.2', True, '1.3', True, None, False, None)
		self.single_range_test('[1.0,2.0)', 1, '1.0', True, '2.0', False, None, False, None)
		self.single_range_test('[1.5,)', 1, '1.5', True, None, False, None, False, None)
		self.single_range_test('(,1.0],[1.2,)', 2, None, False, '1.0', True, None, False, None, 0)
		self.single_range_test('(,1.0],[1.2,)', 2, '1.2', True, None, False, None, False, None, 1)
		
		vr = self.create_from_version_spec('[1.0,)')
		assert vr.contains_version(mvn.Pom.ArtifactVersion('1.0-SNAPSHOT')) == False
		vr = self.create_from_version_spec('[1.0,1.1-SNAPSHOT]')
		assert vr.contains_version(mvn.Pom.ArtifactVersion('1.1-SNAPSHOT')) == True
		vr = self.create_from_version_spec('[5.0.9.0,5.0.10.0)')
		assert vr.contains_version(mvn.Pom.ArtifactVersion('5.0.9.0')) == True
	
	def test_invalid_ranges(self):
		# surround by []
		self.check_invalid_range("(1.0)")
		self.check_invalid_range("[1.0)")
		self.check_invalid_range("(1.0]")
		# identical boundries
		self.check_invalid_range("(1.0,1.0]")
		self.check_invalid_range("[1.0,1.0)")
		self.check_invalid_range("(1.0,1.0)")
		# fully-qualified sets
		self.check_invalid_range("[1.1,1.0]")
		self.check_invalid_range("[1.0,1.2),1.3")
		# overlap
		self.check_invalid_range("[1.0,1.2),(1.1,1.3]")
		self.check_invalid_range("[1.1,1.3),(1.0,1.2]")
		self.check_invalid_range("(1.1,1.2],[1.0,1.1)")
	
	def test_intersections(self):
		vr1 = self.create_from_version_spec('1.0')
		vr2 = self.create_from_version_spec('1.1')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 1, None, False, None, False, '1.0', True, '1.0')
		mvr = vr2.restrict(vr1)
		self.single_range_test(mvr, 1, None, False, None, False, '1.1', True, '1.1')
		
		vr1 = self.create_from_version_spec('[1.0,)')
		vr2 = self.create_from_version_spec('1.1')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 1, '1.0', True, None, False, '1.1', True, '1.1')
		
		vr1 = self.create_from_version_spec('[1.1,)')
		vr2 = self.create_from_version_spec('1.1')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 1, '1.1', True, None, False, '1.1', True, '1.1')
		
		vr1 = self.create_from_version_spec('[1.1]')
		vr2 = self.create_from_version_spec('1.1')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 1, '1.1', True, '1.1', True, '1.1', True, '1.1')
		
		vr1 = self.create_from_version_spec('(1.1,)')
		vr2 = self.create_from_version_spec('1.1')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 1, '1.1', False, None, False, None, False, None)
		
		vr1 = self.create_from_version_spec('[1.2,)')
		vr2 = self.create_from_version_spec('1.1')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 1, '1.2', True, None, False, None, False, None)
		
		vr1 = self.create_from_version_spec('(,1.2]')
		vr2 = self.create_from_version_spec('1.1')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 1, None, False, '1.2', True, '1.1', True, '1.1')
		
		vr1 = self.create_from_version_spec('(,1.1]')
		vr2 = self.create_from_version_spec('1.1')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 1, None, False, '1.1', True, '1.1', True, '1.1')
		
		vr1 = self.create_from_version_spec('(,1.1)')
		vr2 = self.create_from_version_spec('1.1')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 1, None, False, '1.1', False, None, False, None)
		
		vr1 = self.create_from_version_spec('(,1.0]')
		vr2 = self.create_from_version_spec('1.1')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 1, None, False, '1.0', True, None, False, None)
		
		vr1 = self.create_from_version_spec('(,1.0], [1.1,)')
		vr2 = self.create_from_version_spec('1.2')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 2, None, False, '1.0', True, '1.2', True, '1.2', 0)
		self.single_range_test(mvr, 2, '1.1', True, None, False, '1.2', True, '1.2', 1)
		
		vr1 = self.create_from_version_spec('(,1.0], [1.1,)')
		vr2 = self.create_from_version_spec('1.0.5')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 2, None, False, '1.0', True, None, False, None, 0)
		self.single_range_test(mvr, 2, '1.1', True, None, False, None, False, None, 1)
		
		vr1 = self.create_from_version_spec('(,1.1), (1.1,)')
		vr2 = self.create_from_version_spec('1.1')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 2, None, False, '1.1', False, None, False, None, 0)
		self.single_range_test(mvr, 2, '1.1', False, None, False, None, False, None, 1)
		
		vr1 = self.create_from_version_spec('[1.1, 1.3]')
		vr2 = self.create_from_version_spec('(1.1,)')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 1, '1.1', False, '1.3', True, None, False, None)
		
		vr1 = self.create_from_version_spec('(,1.3)')
		vr2 = self.create_from_version_spec('[1.2,1.3]')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 1, '1.2', True, '1.3', False, None, False, None)
		
		vr1 = self.create_from_version_spec('[1.1,1.3]')
		vr2 = self.create_from_version_spec('[1.2,)')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 1, '1.2', True, '1.3', True, None, False, None)
		
		vr1 = self.create_from_version_spec('(,1.3]')
		vr2 = self.create_from_version_spec('[1.2,1.4]')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 1, '1.2', True, '1.3', True, None, False, None)
		
		vr1 = self.create_from_version_spec('(1.2,1.3]')
		vr2 = self.create_from_version_spec('[1.1,1.4]')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 1, '1.2', False, '1.3', True, None, False, None)
		
		vr1 = self.create_from_version_spec('(1.2,1.3)')
		vr2 = self.create_from_version_spec('[1.1,1.4]')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 1, '1.2', False, '1.3', False, None, False, None)
		
		vr1 = self.create_from_version_spec('[1.2,1.3)')
		vr2 = self.create_from_version_spec('[1.1,1.4]')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 1, '1.2', True, '1.3', False, None, False, None)
		
		vr1 = self.create_from_version_spec('[1.0,1.1]')
		vr2 = self.create_from_version_spec('[1.1,1.4]')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 1, '1.1', True, '1.1', True, None, False, None)
		
		vr1 = self.create_from_version_spec('[1.0,1.1)')
		vr2 = self.create_from_version_spec('[1.1,1.4]')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 0, None, False, None, False, None, False, None)
		
		vr1 = self.create_from_version_spec('[1.0,1.2],[1.3,1.5]')
		vr2 = self.create_from_version_spec('[1.1]')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 1, '1.1', True, '1.1', True, None, False, None)
		
		vr1 = self.create_from_version_spec('[1.0,1.2],[1.3,1.5]')
		vr2 = self.create_from_version_spec('[1.4]')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 1, '1.4', True, '1.4', True, None, False, None)
		
		vr1 = self.create_from_version_spec('[1.0,1.2],[1.3,1.5]')
		vr2 = self.create_from_version_spec('[1.1,1.4]')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 2, '1.1', True, '1.2', True, None, False, None, 0)
		self.single_range_test(mvr, 2, '1.3', True, '1.4', True, None, False, None, 1)
		
		vr1 = self.create_from_version_spec('[1.0,1.2),(1.3,1.5]')
		vr2 = self.create_from_version_spec('[1.1,1.4]')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 2, '1.1', True, '1.2', False, None, False, None, 0)
		self.single_range_test(mvr, 2, '1.3', False, '1.4', True, None, False, None, 1)
		
		vr1 = self.create_from_version_spec('[1.0,1.2],[1.3,1.5]')
		vr2 = self.create_from_version_spec('(1.1,1.4)')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 2, '1.1', False, '1.2', True, None, False, None, 0)
		self.single_range_test(mvr, 2, '1.3', True, '1.4', False, None, False, None, 1)
		
		vr1 = self.create_from_version_spec('[1.0,1.2),(1.3,1.5]')
		vr2 = self.create_from_version_spec('(1.1,1.4)')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 2, '1.1', False, '1.2', False, None, False, None, 0)
		self.single_range_test(mvr, 2, '1.3', False, '1.4', False, None, False, None, 1)
		
		vr1 = self.create_from_version_spec('(,1.1),(1.4,)')
		vr2 = self.create_from_version_spec('[1.1,1.4]')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 0, None, False, None, False, None, False, None)
		
		vr1 = self.create_from_version_spec('(,1.1],[1.4,)')
		vr2 = self.create_from_version_spec('(1.1,1.4)')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 0, None, False, None, False, None, False, None)
		
		vr1 = self.create_from_version_spec('[,1.1],[1.4,]')
		vr2 = self.create_from_version_spec('[1.2,1.3]')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 0, None, False, None, False, None, False, None)
		
		vr1 = self.create_from_version_spec('[1.0,1.2],[1.3,1.5]')
		vr2 = self.create_from_version_spec('[1.1,1.4],[1.6,]')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 2, '1.1', True, '1.2', True, None, False, None, 0)
		self.single_range_test(mvr, 2, '1.3', True, '1.4', True, None, False, None, 1)
		
		vr1 = self.create_from_version_spec('[1.0,1.2],[1.3,1.5]')
		vr2 = self.create_from_version_spec('[1.1,1.4],[1.5,]')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 3, '1.1', True, '1.2', True, None, False, None, 0)
		self.single_range_test(mvr, 3, '1.3', True, '1.4', True, None, False, None, 1)
		self.single_range_test(mvr, 3, '1.5', True, '1.5', True, None, False, None, 2)
		
		vr1 = self.create_from_version_spec('[1.0,1.2],[1.3,1.7]')
		vr2 = self.create_from_version_spec('[1.1,1.4],[1.5,1.6]')
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 3, '1.1', True, '1.2', True, None, False, None, 0)
		self.single_range_test(mvr, 3, '1.3', True, '1.4', True, None, False, None, 1)
		self.single_range_test(mvr, 3, '1.5', True, '1.6', True, None, False, None, 2)
		
		vr1 = self.create_from_version_spec('[,1.1],[1.4,]')
		vr2 = self.create_from_version_spec('[1.2,1.3]')
		vr1 = vr1.restrict(vr2)
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 0, None, False, None, False, None, False, None)
		
		vr1 = self.create_from_version_spec('[,1.1],[1.4,]')
		vr2 = self.create_from_version_spec('[1.2,1.3]')
		vr2 = vr1.restrict(vr2)
		mvr = vr1.restrict(vr2)
		self.single_range_test(mvr, 0, None, False, None, False, None, False, None)

	def test_release_range_bounds_contains_snapshots(self):
		vr = self.create_from_version_spec('[1.0,1.2]')
		assert vr.contains_version(mvn.Pom.ArtifactVersion('1.1-SNAPSHOT')) == True
		assert vr.contains_version(mvn.Pom.ArtifactVersion('1.2-SNAPSHOT')) == True
		assert vr.contains_version(mvn.Pom.ArtifactVersion('1.0-SNAPSHOT')) == False
	
	def test_snapshot_range_bounds_can_contain_snapshots(self):
		vr = self.create_from_version_spec('[1.0,1.2-SNAPSHOT]')
		assert vr.contains_version(mvn.Pom.ArtifactVersion('1.1-SNAPSHOT')) == True
		assert vr.contains_version(mvn.Pom.ArtifactVersion('1.2-SNAPSHOT')) == True
		
		vr = self.create_from_version_spec('[1.0-SNAPSHOT,1.2]')
		assert vr.contains_version(mvn.Pom.ArtifactVersion('1.1-SNAPSHOT')) == True
		assert vr.contains_version(mvn.Pom.ArtifactVersion('1.2-SNAPSHOT')) == True
	
	def test_snapshot_soft_version_can_contain_snapshot(self):
		vr = self.create_from_version_spec('1.0-SNAPSHOT')
		assert vr.contains_version(mvn.Pom.ArtifactVersion('1.0-SNAPSHOT')) == True
	
	def test_contains(self):
		actual_version = mvn.Pom.ArtifactVersion('2.0.5')
		assert self.enforce_version('2.0.5', actual_version) == True
		assert self.enforce_version('2.0.4', actual_version) == True
		assert self.enforce_version('[2.0.5]', actual_version) == True
		assert self.enforce_version('[2.0.6,)', actual_version) == False
		assert self.enforce_version('[2.0.6]', actual_version) == False
		assert self.enforce_version('[2.0,2.1]', actual_version) == True
		assert self.enforce_version('[2.0,2.0.3]', actual_version) == False
		assert self.enforce_version('[2.0,2.0.5]', actual_version) == True
		assert self.enforce_version('[2.0,2.0.5)', actual_version) == False
	
	def enforce_version(self, required_version_range, actual_version):
		vr = self.create_from_version_spec(required_version_range)
		return vr.contains_version(actual_version)
	
	def check_invalid_range(self, version):
		try:
			self.create_from_version_spec(version)
			pytest.fail("Version '" + version + "' should have failed to construct")
		except mvn.Pom.VersionException as e:
			return
	
	def ensure_artifact_version(self, version):
		if version is None:
			return None
		elif isinstance(version, mvn.Pom.ArtifactVersion):
			return version
		else:
			return mvn.Pom.ArtifactVersion(version)
		
	def single_range_test(self, spec, rlen, lower_bound, lower_inclusive, upper_bound, upper_inclusive, recommended_version, selected_know, selected_version, index=0):
		if isinstance(spec, mvn.Pom.VersionRange):
			vr = spec
		else:
			vr = self.create_from_version_spec(spec)
		assert rlen == len(vr.restrictions), self.__class__.CHECK_NUM_RESTRICTIONS + " (expected: {0}, got: {1})".format(rlen, len(vr.restrictions))
		assert vr.recommended_version == self.ensure_artifact_version(recommended_version), self.__class__.CHECK_VERSION_RECOMMENDATION   + " (expected: {0}, got: {1})".format(recommended_version, vr.recommended_version)
		if rlen == 0:
			return
		r = vr.restrictions[index]
		assert r.lower_bound == self.ensure_artifact_version(lower_bound), self.__class__.CHECK_LOWER_BOUND + " (expected: {0}, got: {1})".format(lower_bound, r.lower_bound)
		assert r.lower_inclusive == lower_inclusive, self.__class__.CHECK_LOWER_BOUND_INCLUSIVE  + " (expected: {0}, got: {1})".format(lower_inclusive, r.lower_inclusive)
		assert r.upper_bound == self.ensure_artifact_version(upper_bound), self.__class__.CHECK_UPPER_BOUND + " (expected: {0}, got: {1})".format(upper_bound, r.upper_bound)
		assert r.upper_inclusive == upper_inclusive, self.__class__.CHECK_UPPER_BOUND_INCLUSIVE  + " (expected: {0}, got: {1})".format(upper_inclusive, r.upper_inclusive)
		assert vr.is_selected_version_known == selected_know, self.__class__.CHECK_SELECTED_VERSION_KNOWN + " (expected: {0}, got: {1})".format(selected_know, vr.is_selected_version_known)
		assert vr.selected_version == self.ensure_artifact_version(selected_version), self.__class__.CHECK_SELECTED_VERSION + " (expected: {0}, got: {1})".format(selected_version, vr.selected_version)
	
	def create_from_version_spec(self, spec):
		return mvn.Pom.VersionRange.create_from_version_spec(spec)

class Test_MirrorProcessor():
	def test_external_url(self):
		assert True == self.create_repo("foo", "http://somehost").is_external
		assert True == self.create_repo("foo", "http://somehost:9090/somepath").is_external
		assert True == self.create_repo("foo", "ftp://somehost").is_external
		assert True == self.create_repo("foo", "http://129.168.101.1").is_external
		assert True == self.create_repo("foo", "http://").is_external
		# local
		assert False == self.create_repo("foo", "http://localhost:8080").is_external
		assert False == self.create_repo("foo", "http://127.0.0.1:9090").is_external
		assert False == self.create_repo("foo", "file://localhost/somepath").is_external
		assert False == self.create_repo("foo", "file://localhost/D:/somepath").is_external
		assert False == self.create_repo("foo", "http://localhost").is_external
		assert False == self.create_repo("foo", "http://127.0.0.1").is_external
		assert False == self.create_repo("foo", "file:///somepath").is_external
		assert False == self.create_repo("foo", "file://D:/somepath").is_external
		# not a proper url
		assert False == self.create_repo("foo", "192.168.10.1").is_external
		assert False == self.create_repo("foo", "").is_external
	
	def test_mirror_lookup(self):
		mirror_a = self.create_mirror("a", "a", "http://a")
		mirror_b = self.create_mirror("b", "b", "http://b")
		mirrors = mvn.Pom.Mirrors([mirror_a, mirror_b])
		assert mirror_a == mirrors.get_mirror(self.create_repo('a', 'http://a'))
		assert mirror_b == mirrors.get_mirror(self.create_repo('b', 'http://b'))
		assert None == mirrors.get_mirror(self.create_repo('c', 'http://c'))
	
	def test_mirror_wildcard(self):
		mirror_a = self.create_mirror("a", "a", "http://a")
		mirror_b = self.create_mirror("b", "b", "http://b")
		mirror_c = self.create_mirror("c", "*", "http://c")
		mirrors = mvn.Pom.Mirrors([mirror_a, mirror_b, mirror_c])
		assert mirror_a == mirrors.get_mirror(self.create_repo('a', 'http://a'))
		assert mirror_b == mirrors.get_mirror(self.create_repo('b', 'http://b'))
		assert mirror_c == mirrors.get_mirror(self.create_repo('c', 'http://c'))
	
	def test_mirror_stop_on_first_match(self):
		mirror_a2 = self.create_mirror("a2", "a2", "http://a2")
		mirror_a = self.create_mirror("a", "a", "http://a")
		mirror_a3 = self.create_mirror("a3", "a3", "http://b")
		mirror_b = self.create_mirror("b", "b", "http://b")
		mirror_c = self.create_mirror("c", "d,e", "http://de")
		mirror_c2 = self.create_mirror("c", "*", "http://wildcard")
		mirror_c3 = self.create_mirror("c", "e,f", "http://ef")
		mirrors = mvn.Pom.Mirrors([mirror_a2, mirror_a, mirror_a3, mirror_b, mirror_c, mirror_c2, mirror_c3])
		
		assert mirror_a == mirrors.get_mirror(self.create_repo('a', 'http://a.a'))
		assert mirror_b == mirrors.get_mirror(self.create_repo('b', 'http://b.b'))
		assert mirror_c2 == mirrors.get_mirror(self.create_repo('c', 'http://c.c'))
		assert mirror_c == mirrors.get_mirror(self.create_repo('d', 'http://d'))
		assert mirror_c == mirrors.get_mirror(self.create_repo('e', 'http://e'))
		assert mirror_c2 == mirrors.get_mirror(self.create_repo('f', 'http://f'))
	
	def test_patterns(self):
		assert True == self.check_pattern('a', '*')
		assert True == self.check_pattern('a', '*,')
		assert True == self.check_pattern('a', ',*,')
		assert True == self.check_pattern('a', '*,')
		
		assert True == self.check_pattern('a', 'a')
		assert True == self.check_pattern('a', 'a,')
		assert True == self.check_pattern('a', ',a')
		assert True == self.check_pattern('a', ',a,')
		
		assert False == self.check_pattern('b', 'a')
		assert False == self.check_pattern('b', 'a,')
		assert False == self.check_pattern('b', ',a')
		assert False == self.check_pattern('b', ',a,')
		
		assert True == self.check_pattern('a', 'a,b')
		assert True == self.check_pattern('b', 'a,b')
		assert False == self.check_pattern('c', 'a,b')
		
		assert True == self.check_pattern('a', '*')
		assert True == self.check_pattern('a', '*,b')
		assert True == self.check_pattern('a', '*,!b')
		
		assert False == self.check_pattern('a', '*,!a')
		assert False == self.check_pattern('a', '!a,*')
		
		assert True == self.check_pattern('c', '*,!a')
		assert True == self.check_pattern('c', '!a,*,')
		
		assert False == self.check_pattern('c', ',!a,!c')
		assert False == self.check_pattern('d', ',!a,!c*')
		
	def test_patterns_with_external(self):
		assert True == self.check_pattern('a', '*', 'http://localhost')
		assert False == self.check_pattern('a', 'external:*', 'http://localhost')
		
		assert True == self.check_pattern('a', 'external:*,a', 'http://localhost')
		assert False == self.check_pattern('a', 'external:*,!a', 'http://localhost')
		assert True == self.check_pattern('a', 'a,external:*', 'http://localhost')
		assert False == self.check_pattern('a', '!a,external:', 'http://localhost')
		
		assert False == self.check_pattern('c', '!a,external:*', 'http://localhost')
		assert True == self.check_pattern('c', '!a,external:*', 'http://somehost')
	
	def test_layout_pattern(self):
		assert True == self.check_layout('default', None)
		assert True == self.check_layout('default', '')
		assert True == self.check_layout('default', '*')
		
		assert True == self.check_layout('default', 'default')
		assert False == self.check_layout('default', 'legacy')
		
		assert True == self.check_layout('default', 'legacy,default')
		assert True == self.check_layout('default', 'default,legacy')
	
		assert False == self.check_layout('default', 'legacy,!default')
		assert False == self.check_layout('default', '!default,legacy')
		
		assert False == self.check_layout('default', '*,!default')
		assert False == self.check_layout('default', '!default,*')
	
	def test_mirror_layout_considered_for_matching(self):
		repo = self.create_repo('a', 'a')
		mirror_a = self.create_mirror('a', 'a', 'http://a', None)
		mirror_b = self.create_mirror('b', 'b', 'http://b', 'p2')
		mirror_c = self.create_mirror('c', '*', 'http://c', None)
		mirror_d = self.create_mirror('d', '*', 'http://d', 'p2')
		
		assert mirror_a == mvn.Pom.Mirrors([mirror_a]).get_mirror(repo)
		assert None == mvn.Pom.Mirrors([mirror_b]).get_mirror(repo)
		assert mirror_c == mvn.Pom.Mirrors([mirror_c]).get_mirror(repo)
		assert None == mvn.Pom.Mirrors([mirror_d]).get_mirror(repo)
	
	def check_layout(self, repository_layout, mirror_layouts):
		mirror = self.create_mirror('test_mirror', '', '', mirror_layouts)
		repository = self.create_repo('test_repo', '')
		return mirror.match_layout(repository_layout)
		
	def check_pattern(self, repository_id, mirror_of, repository_url = ''):
		mirror = self.create_mirror('test_mirror', mirror_of, '')
		repository = self.create_repo(repository_id, repository_url)
		return mirror.match_repository(repository)
	
	def create_mirror(self, mirror_id, mirror_of, mirror_url, mirror_layouts = None):
		return mvn.Pom.Mirror(mirror_id, '', mirror_url, None, mirror_of, mirror_layouts)
	
	def create_repo(self, repo_id, repo_url, repo_layout=None):
		return mvn.Pom.ArtifactRepository(repo_id, repo_url, repo_layout)

if __name__ == '__main__':
	pass
