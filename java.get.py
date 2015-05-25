#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
   The MIT License (MIT)
   
   Copyright (C) 2015 Andris Raugulis (moo@arthepsy.eu)
   
   Permission is hereby granted, free of charge, to any person obtaining a copy
   of this software and associated documentation files (the "Software"), to deal
   in the Software without restriction, including without limitation the rights
   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
   copies of the Software, and to permit persons to whom the Software is
   furnished to do so, subject to the following conditions:
   
   The above copyright notice and this permission notice shall be included in
   all copies or substantial portions of the Software.
   
   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
   THE SOFTWARE.
"""
from __future__ import print_function
import os, sys, subprocess
import click

def _err(*objs):
	print(*objs, file=sys.stderr)
	sys.exit(1)

def _out(*objs):
	print(*objs, file=sys.stdout)

def _int(s):
	return int(_num(s))

def _num(s): 
	try: 
		return int(s)
	except ValueError:
		return float(s)

JDK_ARCH = {'x64' : 'x64', 'x86_64': 'x64', 'x86': 'i586', 'i386': 'i586', 'i586': 'i586', 'i686': 'i586' }
JDK = { 7: { 80: 15, 79: 15, 76: 13, 75: 13, 72: 14, 71: 14, 67: 1, 65: 17, 60: 19, 55: 13, 51: 13, 45: 18, 40: 43, 25: 15, 21: 12, 17: 2, 15: 3, 13: 20, 11: 21, 10: 18, 9: 5, 7: 10, 6: 24, 5: 6, 4: 20, 3: 4, 2: 13, 1: 8 },
        8: { 45: 14, 40: 25, 31: 13, 25: 17, 20: 26, 11: 12, 5: 13, 0: 132 }}
def check_jdk(arch, major):
	if not major in JDK:
		raise click.UsageError('<major> "{0}" is not a major version of JDK.'.format(major))
	
def get_jdk_list(arch, major):
	check_jdk(arch, major)
	versions = ', '.join(str(v) for v in sorted(JDK[major], reverse=True))
	return versions
	
def get_jdk(arch, major, minor, build):
	check_jdk(arch, major)
	if not minor in JDK[major]:
		jdk_list = get_jdk_list(arch, major)
		raise click.UsageError('<minor> "{0}" is not a known version of JDK{1}. Available versions: {2}\n'.format(minor, major, jdk_list))
	if build is None:
		build=JDK[major][minor]
	minor = 'u' + str(minor) if minor > 0 else ''
	cookie = "gpw_e24=http%3A%2F%2Fwww.oracle.com%2F; oraclelicense=accept-securebackup-cookie"
	url = "http://download.oracle.com/otn-pub/java/jdk/{1}{2}-b{3}/jdk-{1}{2}-linux-{0}.tar.gz".format(arch, major, minor, build)
	if cmd_exists('wget'):
		cmd = 'wget --no-cookies --no-check-certificate --header "Cookie: {0}" "{1}"'.format(cookie, url)
	elif cmd_exists('curl'):
		cmd = 'curl -O -L --insecure --cookie "{0}" "{1}"'.format(cookie, url)
	else:
		_err('error: wget or curl not found.')
	os.system(cmd)

MAVEN = { 'archive': ['2.0.8', '2.0.9', '2.0.10', '2.0.11', '2.1.0', '2.2.0', '2.2.1', '3.0', '3.0.1', '3.0.2', '3.0.3', '3.0.4', '3.0.4', '3.0.5', '3.1.0', '3.1.1', '3.2.1', '3.2.2', '3.2.3'],
          'current': ['3.0.5', '3.1.1', '3.2.5', '3.3.1', '3.3.3'],
          'legacy_archive_url': 'http://archive.apache.org/dist/maven/binaries/',
          'archive_url': 'http://archive.apache.org/dist/maven/maven-3/',
          'current_url': 'http://mirror.nexcess.net/apache/maven/maven-3/'}

def check_mvn(version):
	if not version in MAVEN['current'] and not version in MAVEN['archive']:
		mvn_list = get_mvn_list()
		raise click.UsageError('"{0}" is not a known version of Maven. Available versions: {1}'.format(version, mvn_list))

def get_mvn_list():
	versions = sorted(set(MAVEN['current']  + MAVEN['archive']), reverse=True)
	return ', '.join(versions)

def get_mvn(version):
	check_mvn(version)
	if version in MAVEN['current']:
		url_base = MAVEN['current_url'].rstrip('/')
		url = url_base + '/{0}/binaries/apache-maven-{0}-bin.tar.gz'.format(version)
	elif version in MAVEN['archive']:
		if version < '3.0.4':
			url_base = MAVEN['legacy_archive_url'].rstrip('/')
			url = url_base + '/apache-maven-{0}-bin.tar.gz'.format(version)
		else:
			url_base = MAVEN['archive_url'].rstrip('/')
			url = url_base + '/' + version + '/binaries/apache-maven-{0}-bin.tar.gz'.format(version)
	else:
		_err('Unknown Maven version.')
	if cmd_exists('wget'):
		cmd = 'wget --no-cookies --no-check-certificate "{0}"'.format(url)
	elif cmd_exists('curl'):
		cmd = 'curl -O -L --insecure "{0}"'.format(url)
	else:
		_err('error: wget or curl not found.')
	os.system(cmd)

def cmd_exists(cmd):
	return subprocess.call("type " + cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0
 
@click.group()
def cli():
	pass

@cli.command('jdk', short_help='download Java JDK')
@click.argument('arch', metavar='<arch>', type=click.Choice(JDK_ARCH.keys()))
@click.argument('major', metavar='<major>', type=click.Choice(['7', '8']))
@click.argument('minor', metavar='<minor>', type=int, required=False)
@click.option('--build', type=int)
def jdk(arch, major, minor, build):
	"""download Java JDK
	
	\b
	<arch>  - [x64|x86]
	<major> - [7|8]
	<minor> - minor version
	"""
	arch = JDK_ARCH[arch]
	if minor is None:
		jdk_list = get_jdk_list(arch, _num(major))
		_err('Available JDK{0} versions: {1}'.format(major, jdk_list))
	get_jdk(arch, _num(major), minor, build)

@cli.command('mvn', short_help='download Maven')
@click.argument('version', metavar='<version>', type=str, required=False)
def mvn(version):
	"""download Maven
	
	\b
	<version> - version
	"""
	if version is None:
		mvn_list = get_mvn_list()
		_err('Available Maven versions: {0}'.format(mvn_list))
	get_mvn(version)

if __name__ == '__main__':
	cli()
