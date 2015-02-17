#!/usr/bin/env python
# -*- coding: utf-8 -*-

import imp

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
		parsed = "'{0}' parsed as ('{1}', '{2}', '{3}', '{4}', '{5}'), ".format(version, av.get_major(), av.get_minor(), av.get_incremental(), av.get_build_number(), av.get_qualifier())
		assert major == av.get_major(), parsed + "check major version"
		assert minor == av.get_minor(), parsed + "check minor version"
		assert incremental == av.get_incremental(), parsed + "check incremental version"
		assert build_number == av.get_build_number(), parsed + "check build number .. [{0}][{1}]".format(build_number, av.get_build_number())
		assert qualifier == av.get_qualifier(), parsed + "check qualifier"
		assert major == av.get_major(), parsed + "check major version"
		assert version == str(av), parsed + "check string value"
	
	def assert_version_older(self, left, right):
		assert mvn.Pom.ArtifactVersion(left).compare_to(mvn.Pom.ArtifactVersion(right)) < 0, left + " should be older than " + right 
		assert mvn.Pom.ArtifactVersion(right).compare_to(mvn.Pom.ArtifactVersion(left)) > 0, right + " should be newer than " + left 
	
	def assert_version_equal(self, left, right):
		assert mvn.Pom.ArtifactVersion(left).compare_to(mvn.Pom.ArtifactVersion(right)) == 0, left + " should be equal to " + right 
		assert mvn.Pom.ArtifactVersion(right).compare_to(mvn.Pom.ArtifactVersion(left)) == 0, right + " should be equal to " + left 

class Test_ArtifactVersionComparer(object):
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
		c1 = mvn.Pom.ArtifactVersionComparer("1")
		c1._parse("2")
		c2 = mvn.Pom.ArtifactVersionComparer("2");
		assert c1 == c2, "reused instance should be equivalent to new instance"
	
	def new_comparer(self, version):
		ret = mvn.Pom.ArtifactVersionComparer(version)
		canonical = ret.get_canonical()
		parsed_canonical = mvn.Pom.ArtifactVersionComparer(canonical).get_canonical()
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

if __name__ == '__main__':
	pass
