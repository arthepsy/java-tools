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
import sys, os, errno, re
import click
import itertools
import signal
from lxml import etree
import rfc3987
import platform

from inspect import getmembers
from pprint import pprint

signal.signal(signal.SIGPIPE, signal.SIG_DFL)

class Config(object):
	def __init__(self, verbose=False):
		self.verbose = verbose
		self.pom_file = None

class Pom(object):
	def __init__(self):
		self.__module_cache = {}
		self.__properties = Pom.Properties.create_root()
		
		self.__global_settings = Pom.Settings.create('${env.M2_HOME}/conf/settings.xml', self.__properties)
		self.__user_settings = Pom.Settings.create('${user.home}/.m2/settings.xml', self.__properties)
		self.user_settings.merge(self.__global_settings)
		
		default_storage = Pom.ArtifactStorage.create_default(self.user_settings.local_repository)
		self.__storage = Pom.ArtifactStorage(default_storage)
		for profile in self.user_settings.active_profiles:
			self.storage.add(profile.repositories, self.user_settings.mirrors)
	
	@property
	def properties(self):
		return self.__properties
	
	@property
	def module_cache(self):
		return self.__module_cache
	
	@property
	def global_settings(self):
		return self.__global_settings
	
	@property
	def user_settings(self):
		return self.__user_settings
	
	@property
	def storage(self):
		return self.__storage
	
	class Settings(object):
		def __init__(self, properties):
			self.__defaults = set()
			self._set_defaults(properties)
			self.__mirrors = Pom.Mirrors()
			self.__profiles = Pom.Profiles()
			self.__active_profile_names = set()
		
		@property
		def defaults(self):
			return self.__defaults
		
		@property
		def local_repository(self):
			return self.__local_repository
		
		@property
		def mirrors(self):
			return self.__mirrors
		
		@property
		def profiles(self):
			return self.__profiles
		
		@property
		def active_profile_names(self):
			return self.__active_profile_names
		
		@property
		def active_profiles(self):
			for profile_name in self.__active_profile_names:
				if profile_name in self.profiles:
					yield self.profiles[profile_name]
		
		def _set_defaults(self, properties):
			if properties is None:
				properties = Pom.Properties()
			self.__local_repository = properties.expand_value('${user.home}/.m2/repository')
			self.__defaults.add('local_repository')
		
		def merge(self, other):
			if other is None:
				return
			key = 'local_repository'
			if key in self.defaults:
				if not key in other.defaults:
					self.__local_repository = other.local_repository
					self.defaults.remove('local_repository')
			if len(other.mirrors) > 0:
				mirrors = Pom.Mirrors()
				for mirror in other.mirrors:
					mirrors.append(mirror)
				for mirror in self.mirrors:
					mirrors.append(mirror)
				self.__mirrors = mirrors
			for profile in other.profiles:
				if profile.name not in self.profiles:
					self.profiles[profile.name] = profile
			for active_profile_name in other.active_profile_names:
				self.__active_profile_names.add(active_profile_name)
		
		def parse(self, file_path, properties):
			file_path = properties.expand_value(file_path)
			io = Pom.IO(file_path)
			if not os.path.isfile(io.file_path):
				return
			parser = etree.XMLParser(recover=True)
			xtree = etree.parse(io.file_path, parser)
			xroot = xtree.getroot()
			if xroot is None:
				return
			
			self.__mirrors.fill(xroot)
			self.__profiles = Pom.Profiles.create(io, xroot)
			for xnode in Pom.Xml.get_nodes(xroot, 'activeProfile', 'activeProfiles'):
				profile_name = Pom.Xml.get_node_value(xnode, '')
				if profile_name:
					self.__active_profile_names.add(profile_name)
			value = Pom.Xml.get_child_node_value(xroot, 'localRepository', None)
			if value is not None and len(value) > 0:
				self.__local_repository = value
				self.defaults.remove('local_repository')
		
		@classmethod
		def create(cls, file_path, properties):
			o = cls(properties)
			o.parse(file_path, properties)
			return o
	
	class Mirrors(list):
		def __init__(self, *args, **kwargs):
			list.__init__(self, *args, **kwargs)
		
		def fill(self, xroot):
			for xmirror in Pom.Xml.get_mirrors(xroot):
				mirror = Pom.Mirror.parse(xmirror)
				if mirror is None: continue
				self.append(mirror)
		
		def get_mirror(self, repository):
			for mirror in self:
				if mirror.mirror_of == repository.id and mirror.match_layout(repository.layout):
					return mirror
			for mirror in self:
				if mirror.match_repository(repository) and mirror.match_layout(repository.layout):
					return mirror
			return None
		
		@classmethod
		def create(cls, xroot):
			o = cls()
			o.fill(xroot)
			return o
	
	class Mirror(object):
		VALID_LAYOUTS = ['default', 'legacy']
		
		def __init__(self, mirror_id, name, url, layout = None, mirror_of = None, mirror_layouts = None):
			self.__id = mirror_id
			self.__name = name
			self.__url = url
			self.__layout = layout or 'default'
			self.__mirror_of = mirror_of or '*'
			self.__mirror_layouts = mirror_layouts or 'default,legacy'
		
		@property
		def id(self):
			return self.__id
		
		@property
		def name(self):
			return self.__name
		
		@property
		def url(self):
			return self.__url
		
		@property
		def layout(self):
			return self.__layout
		
		@property
		def mirror_of(self):
			return self.__mirror_of
		
		@property
		def mirror_layouts(self):
			return self.__mirror_layouts
		
		def get_mirror(self, repository):
			if self.mirror_of == repository.id and mirror.match_layout(repository.layout):
				return self
			if self.match_repository(repository) and self.match_layout(repository.layout):
				return self
			return None
		
		def match_layout(self, mirror_layout):
			if len(self.mirror_layouts) == 0 or mirror_layout == '*':
				return True
			if self.mirror_layouts == mirror_layout:
				return True
			matched = False
			for layout in self.mirror_layouts.split(','):
				layout = layout.strip()
				if len(layout) > 1 and layout.startswith('!'):
					if layout[1:] == mirror_layout:
						return False
				elif layout == mirror_layout:
					matched = True
				elif layout == '*':
					matched = True
			return matched
		
		def match_repository(self, repository):
			if self.mirror_of == '*' or repository.id == self.mirror_of:
				return True
			matched = False
			for mirror_repo in self.mirror_of.split(','):
				mirror_repo = mirror_repo.strip()
				if len(mirror_repo) > 1 and mirror_repo.startswith('!'):
					if mirror_repo[1:] == repository.id:
						return False
				if mirror_repo == repository.id:
					return True
				elif repository.is_external and mirror_repo == 'external:*':
					matched = True
				elif mirror_repo == '*':
					matched = True
			return matched
		
		@classmethod
		def parse(cls, xnode):
			mirror_id = (Pom.Xml.get_child_node_value(xnode, 'id', '') or 'default').lower()
			name = Pom.Xml.get_child_node_value(xnode, 'name', '')
			url = Pom.Xml.get_child_node_value(xnode, 'url', '')
			layout = Pom.Xml.get_child_node_value(xnode, 'layout', None)
			mirror_of = Pom.Xml.get_child_node_value(xnode, 'mirrorOf', None)
			mirror_layouts = Pom.Xml.get_child_node_value(xnode, 'mirrorOfLayouts', None)
			mirror = cls(mirror_id, name, url, layout, mirror_of, mirror_layouts)
			return mirror
		
		def __str__(self):
			return self.url
		
		def __eq__(self, other):
			if not isinstance(other, self.__class__):
				return False
			if self.id != other.id or self.url != other.url:
				return False
			elif self.layout != other.layout:
				return False
			elif self.mirror_of != other.mirror_of:
				return False
			elif self.mirror_layouts != other.mirror_layouts:
				return False
			return True
		
		def __ne__(self, other):
			return not self.__eq__(other)
		
		#def __hash__(self):
		#	TODO

		def __repr__(self):
			return "{0}(id='{1}', of='{2}', url={3}, name='{4}')".format(self.__class__.__name__, self.id, self.mirror_of, self.url, self.name)
	
	class ArtifactRepositories(list):
		def __init__(self, *args, **kwargs):
			list.__init__(self, *args, **kwargs)
		
		@classmethod
		def create(cls, xroot, plugins=False):
			repositories = cls()
			parent_name = 'pluginRepositories' if plugins else 'repositories'
			child_name = 'pluginRepository' if plugins else 'repository'
			for xrepository in Pom.Xml.get_nodes(xroot, child_name, parent_name):
				repository = Pom.ArtifactRepository.create(xrepository)
				if repository is None: 
					continue
				repositories.append(repository) 
			return repositories
	
	class ArtifactRepository(object):
		def __init__(self, repository_id, url, layout=None):
			self.__id = repository_id
			self.__url = url
			if layout is None:
				layout = 'default'
			self.__layout = layout
			self.__name = ''
			self.__releases = Pom.RepositoryPolicy()
			self.__snapshots = Pom.RepositoryPolicy()
		
		@property
		def id(self):
			return self.__id
		
		@property
		def url(self):
			return self.__url
		
		@property
		def layout(self):
			return self.__layout
		
		@property
		def name(self):
			return self.__name
		
		@property
		def releases(self):
			return self.__releases
		
		@property
		def snapshots(self):
			return self.__snapshots
		
		@staticmethod
		def is_external_url(url):
			try:
				d = rfc3987.parse(url, rule='URI')
				if d['host'] == 'localhost' or d['host'] == '127.0.0.1':
					return False
				elif d['scheme'] == 'file':
					return False
				return True
			except ValueError:
				return False
		
		@property
		def is_external(self):
			return self.__class__.is_external_url(self.url)
		
		def set_mirror(self, mirror):
			if mirror is not None:
				self.__url = mirror.url
		
		def clone(self):
			o = self.__class__(self.id, self.url, self.layout)
			o.__name = self.name
			o.__releases = self.releases
			o.__snapshots = self.snapshots
			return o
		
		@classmethod
		def create(cls, xrepository):
			repository_id = Pom.Xml.get_id(xrepository)
			if len(repository_id) == 0: 
				return None
			url = Pom.Xml.get_child_node_value(xrepository, 'url', '')
			layout = Pom.Xml.get_child_node_value(xrepository, 'layout', None)
			repository = cls(repository_id, url, layout)
			repository.__name = Pom.Xml.get_child_node_value(xrepository, 'name', '')
			repository.__releases = Pom.RepositoryPolicy.create(Pom.Xml.get_node(xrepository, 'releases'))
			repository.__snapshots = Pom.RepositoryPolicy.create(Pom.Xml.get_node(xrepository, 'snapshots'))
			return repository
		
		@staticmethod
		def get_str(repository):
			out = 'id={0}, url={1}, layout={2}'.format(repository.id, repository.url, repository.layout)
			default_policy = Pom.RepositoryPolicy()
			if repository.releases != default_policy:
				out += ', releases={0}'.format(repository.releases)
			if repository.snapshots != default_policy:
				out += ', snapshots={0}'.format(repository.snapshots)
			return out
		
		def __str__(self):
			return self.__class__.get_str(self)
		
		def __repr__(self):
			return '{0}({1})'.format(self.__class__.__name__, str(self))
	
	class ArtifactStorage(object):
		def __init__(self, parent = None):
			self.__local = []
			self.__remote = []
			if parent is None:
				return
			for repository in parent.local:
				self.add(repository)
			for repository in parent.remote:
				self.add(repository)
		
		@property
		def local(self):
			return self.__local
		
		@property
		def remote(self):
			return self.__remote
		
		def _add_repository(self, repositories, repository):
			pos = -1
			idx = 0
			for r in repositories:
				if r.id == repository.id:
					pos = idx
					break
				idx += 1
			if pos > -1:
				repositories[pos] = repository
			else:
				repositories.append(repository)
			
		def add(self, repositories, mirrors = None):
			if hasattr(repositories, '__iter__'):
				if len(repositories) == 0:
					return
				for repository in repositories:
					self.add(repository, mirrors)
			else:
				repository = repositories
				mirror = None
				if mirrors is not None and hasattr(mirrors, 'get_mirror'):
					mirror = mirrors.get_mirror(repository)
				if mirror is not None:
					repository = repository.clone()
					repository.set_mirror(mirror)
				if repository.is_external:
					self._add_repository(self.remote, repository)
				else:
					self._add_repository(self.local, repository)
		
		@classmethod
		def create_default(cls, local_repository_path):
			storage = cls()
			repository = Pom.ArtifactRepository('local', local_repository_path)
			storage.add(repository)
			repository = Pom.ArtifactRepository('central', 'https://repo.maven.apache.org/maven2')
			storage.add(repository)
			repository = Pom.ArtifactRepository('apache.snapshots', 'http://repository.apache.org/snapshots')
			storage.add(repository)
			return storage
		
		def __str__(self):
			out = ''
			if len(self.local) > 0:
				out += 'local={0}'.format(self.local)
			if len(self.remote) > 0:
				if len(out) > 0: out += ', '
				out += 'remote={0}'.format(self.remote)
			return '{' + out + '}' 
		
		def __repr__(self):
			return '{0}({1})'.format(self.__class__.__name__, str(self))
	
	class RepositoryPolicy(object):
		def __init__(self):
			self.__enabled = True
			self.__update_policy = 'daily'
			self.__checksum_policy = 'warn'
		
		@property
		def enabled(self):
			return self.__enabled
		
		@property
		def update_policy(self):
			return self.__update_policy
		
		@property
		def checksum_policy(self):
			return self.__checksum_policy
		
		@classmethod
		def create(cls, xnode):
			policy = cls()
			if xnode is None:
				return policy
			value = Pom.Xml.get_child_node_value(xnode, 'enabled', None)
			if value is not None:
				policy.__enabled = value.lower() == 'true'
			value = Pom.Xml.get_child_node_value(xnode, 'updatePolicy', None)
			if value is not None:
				value = value.lower()
				if value.startswith('interval:') or value in ['always', 'daily', 'never']:
					policy.__update_policy = value
			value = Pom.Xml.get_child_node_value(xnode, 'checksumPolicy', None)
			if value is not None:
				value = value.lower()
				if value in ['ignore', 'fail', 'warn']:
					policy.__checksum_policy = value
			return policy
			
		def __str__(self):
			out = 'enabled={0}, checksums={1}, updates={2}'.format(self.enabled, self.checksum_policy, self.update_policy)
			return '{' + out + '}' 
		
		def __eq__(self, other):
			if not isinstance(other, self.__class__):
				return False
			if self.enabled != other.enabled:
				return False
			if self.update_policy != other.update_policy:
				return False
			if self.checksum_policy != other.checksum_policy:
				return False
			return True
		
		def __ne__(self, other):
			return not self.__eq__(other)
		
		def __hash__(self):
			value = 3
			value = 19 * value + hash(self.enabled)
			value = 19 * value + hash(self.update_policy)
			value = 19 * value + hash(self.checksum_policy)
			return value
		
		def __repr__(self):
			return '{0}({1})'.format(self.__class__.__name__, str(self))
	
	class BuildGraphConf(object):
		def __init__(self, modules = None, profiles = None, level = 0):
			self.modules = modules
			self.profiles = profiles
			self.level = level
			
			self.parent_matched = False
			self.match_path = None
			self.do_mark = True
			self.do_filter = False
			
			self.show_weight = False
			self.output = False
			self.output_type = 'graph'
			self.output_tree = True
			self.matched_modules = set()
			self.show_implicit = False
			self.show_prefix = True
		
		def do_match(self):
			return self.match_path is not None and not self.match_path.is_empty()
		
		def fork(self, modules = None, profiles = None, level = 0, parent_matched = False):
			conf = Pom.BuildGraphConf(modules, profiles, level)
			conf.match_path = self.match_path
			conf.do_mark = self.do_mark
			conf.do_filter = self.do_filter
			conf.parent_matched = self.parent_matched
			conf.show_weight = self.show_weight
			conf.output = self.output
			conf.output_type = self.output_type
			conf.output_tree = self.output_tree
			conf.matched_modules = self.matched_modules
			conf.show_implicit =  self.show_implicit
			conf.show_prefix = self.show_prefix
			return conf
	
	class BuildGraph(object):
		def __init__():
			pass
		
		@staticmethod
		def get_padding(level):
			if level < 1:
				return ''
			padding = ' ' + ' |' * (level - 1) + ' +-'
			return padding
		
		@staticmethod
		def get_weight_text(conf, o, matched = False):
			if o is None: 
				return  ''
			text = ' {weight='
			do_match = conf.match_path is not None and not conf.match_path.is_empty()
			w = o.get_weight()
			if do_match and matched:
				cw = o.get_weight(conf.match_path)
				if (cw != w):
					text += '%.4f/' % cw
			text += '%.4f' % w
			text += ')'
			return text
		
		@staticmethod
		def show(conf = None):
			if conf is None:
				conf = Pom.BuildGraphConf()
			Pom.BuildGraph._build(conf)
			conf.output = True
			if conf.output_type == 'modules':
				Pom.BuildGraph._show_modules(conf)
			else:
				Pom.BuildGraph._build(conf)
		
		@staticmethod
		def _output_module(conf, module, display_name):
			text = ''
			do_match = conf.do_match()
			matched = conf.parent_matched if do_match else False
			if conf.show_prefix:
				if do_match:
					match_sign = '*' if matched else ' '
					if not matched and conf.show_implicit:
						implicit_match = display_name in conf.matched_modules
						if implicit_match:
							match_sign = '.'
					text += '[ mod %s ]' % (match_sign)
				else:
					text += '[ module]'
			padding = Pom.BuildGraph.get_padding(conf.level)
			if conf.output_tree:
				text += ' %s' % (padding)
			else:
				if conf.show_prefix:
					text += ' '
			text += display_name
			if conf.show_weight:
				text += Pom.BuildGraph.get_weight_text(conf, module, matched)
			print text
		
		@staticmethod
		def _output_profile(conf, profile, display_name):
			text = ''
			do_match = conf.do_match()
			matched = conf.match_path.is_profile_active(profile) if do_match else False
			if do_match:
				match_sign = '*' if matched else ' '
				text += '[prof %s ]' % (match_sign)
			else:
				text += '[profile]'
			padding = Pom.BuildGraph.get_padding(conf.level)
			text += ' %s%s' % (padding, display_name)
			if profile.activation is not None:
				subtext = []
				activation = profile.activation
				if activation.by_default:
					subtext.append('+active')
				if activation.property_name is not None:
					if activation.property_value is None:
						subtext.append('%s' % activation.property_name)
					else:
						subtext.append('%s=%s' % (activation.property_name, activation.property_value))
				if len(subtext) > 0:
					text += ' (' + ','.join(subtext) + ')'
			if conf.show_weight:
				text += Pom.BuildGraph.get_weight_text(conf, profile, matched)
			print text
		
		
		@staticmethod
		def _show_modules(conf, parent = None):
			modules = Pom.Modules()
			if conf.modules is not None:
				for module_name, module in conf.modules.items():
					modules[module_name] = module
			if conf.profiles is not None:
				for profile_name, profile in conf.profiles.items():
					for module_name, module in profile.modules.items():
						modules[module_name] = module
			for module_name in sorted(modules):
				module = modules[module_name]
				if parent is not None and parent != module.artifact.parent:
					continue 
				if module is not None:
					module_display_name = module.artifact.moduleId
				else:
					module_display_name = module_name
				Pom.BuildGraph._output_module(conf, module, module_display_name)
				Pom.BuildGraph._show_modules(conf.fork(module.modules, module.profiles, conf.level + 1), module.artifact)
		
		@staticmethod
		def _build(conf):
			do_match = conf.do_match()
			if conf.modules is not None: 
				for module_name in sorted(conf.modules):
					module = conf.modules[module_name]
					if module is not None:
						module_display_name = module.artifact.moduleId
					else:
						module_display_name = module_name
					matched = conf.parent_matched if do_match else False
					if matched:
						conf.matched_modules.add(module_display_name)
					if conf.output:
						Pom.BuildGraph._output_module(conf, module, module_display_name)
					if module is not None:
						Pom.BuildGraph._build(conf.fork(module.modules, module.profiles, conf.level + 1))
			if conf.profiles is not None:
				for profile_name in sorted(conf.profiles):
					profile = conf.profiles[profile_name]
					matched = conf.match_path.is_profile_active(profile) if do_match else False
					if do_match and not matched and conf.do_filter:
						continue
					if conf.output:
						Pom.BuildGraph._output_profile(conf, profile, profile_name)
					if profile is not None:
						sconf = conf.fork(profile.modules, None, conf.level + 1)
						sconf.parent_matched = matched
						Pom.BuildGraph._build(sconf)
	
	class Xml(object):
		@staticmethod
		def get_group_id(xnode):
			return Pom.Xml.get_child_node_value(xnode, 'groupId', '')
		
		@staticmethod
		def get_artifact_id(xnode):
			return Pom.Xml.get_child_node_value(xnode, 'artifactId', '')
		
		@staticmethod
		def get_version(xnode):
			return Pom.Xml.get_child_node_value(xnode, 'version', '')
		
		@staticmethod
		def get_id(xnode):
			return Pom.Xml.get_child_node_value(xnode, 'id', '')
		
		@staticmethod
		def get_packaging(xroot):
			return Pom.Xml.get_child_node_value(xroot, 'packaging', '')
		
		@staticmethod
		def get_classifier(xroot):
			return Pom.Xml.get_child_node_value(xroot, 'classifier', '')
		
		@staticmethod
		def get_modules(xnode):
			return Pom.Xml.get_nodes(xnode, 'module', 'modules')
		
		@staticmethod
		def get_profiles(xnode):
			return Pom.Xml.get_nodes(xnode, 'profile', 'profiles')
		
		@staticmethod
		def get_properties(xnode):
			return Pom.Xml.get_nodes(xnode, parent_name = 'properties')
		
		@staticmethod
		def get_dependencies(xnode, management=False):
			if management:
				xnode = Pom.Xml.get_node(xnode, 'dependencyManagement')
			if xnode is None:
				return []
			return Pom.Xml.get_nodes(xnode, 'dependency', 'dependencies')
		
		@staticmethod
		def get_parent_relpath(xnode):
			xparent = Pom.Xml.get_node(xnode, 'parent')
			if xparent is None:
				return ''
			return Pom.Xml.get_child_node_value(xparent, 'relativePath', '') 
		
		@staticmethod
		def get_plugins(xnode):
			return Pom.Xml.get_nodes(xnode, 'plugin', 'plugins')
		
		@staticmethod
		def get_mirrors(xnode):
			return Pom.Xml.get_nodes(xnode, 'mirror', 'mirrors')
		
		@staticmethod
		def get_nodes(xnode, children_name=None, parent_name=None):
			if xnode is None:
				return []
			if parent_name is not None and len(parent_name) > 0:
				xparent = xnode.find("{*}" + parent_name)
			else:
				xparent = xnode
			if xparent is not None:
				if children_name is None or len(children_name) == 0:
					return xparent.iterchildren()
				else:
					return xparent.iterchildren("{*}" + children_name)
			else:
				return []
		
		@staticmethod
		def get_root_node(xnode):
			if xnode is None:
				return None
			parent = xnode
			while parent.getparent() is not None:
				parent = parent.getparent()
			return parent
		
		@staticmethod
		def get_node(xnode, child_name):
			return xnode.find('{*}' + child_name)
		
		@staticmethod
		def get_node_value(xnode, default_value = None):
			if xnode is not None and xnode.text is not None:
				value = xnode.text.strip()
			else:
				value = None
			if value is None or len(value) == 0:
				value = default_value
			return value
		
		@staticmethod
		def get_child_node_value(xnode, child_name, default_value = None):
			xnode = Pom.Xml.get_node(xnode, child_name)
			return Pom.Xml.get_node_value(xnode, default_value)
		
		@staticmethod
		def get_clean_tag(xnode):
			if xnode is None: return ''
			return re.sub('^({[^{]*})?[ \t]*(.*)$', '\\2', xnode.tag.strip())
	
	class IO(object):
		def __init__(self, file_path):
			file_path = os.path.expanduser(file_path)
			self.__file_path = os.path.abspath(file_path)
			self.__dir_path = os.path.abspath(os.path.dirname(file_path))
		
		@property
		def file_path(self):
			return self.__file_path
		
		@property
		def dir_path(self):
			return self.__dir_path
		
		def __str__(self):
			return self.file_path
		
		def __repr__(self):
			return "{0}('{1}')".format(self.__class__.__name__, self.file_path)
	
	class Properties(dict):
		def __init__(self, *args, **kwargs):
			dict.__init__(self, *args, **kwargs)
			self.__parent = None
			self.__internal = set()
		
		@property
		def parent(self):
			return self.__parent
		
		@property
		def internal(self):
			return self.__internal
		
		def _get_item_keys(self, value, ignore_list = None):
			keys = set(re.findall('\${([^}]*)}', value))
			if ignore_list is not None:
				for key in list(keys):
					if key in ignore_list:
						keys.remove(key)
			#keys.remove('')
			return keys
			
		def expand_required(self, value = None, ignore_list = None):
			if value is not None:
				if ignore_list is None:
					return value.find('${') != -1
				else:
					keys = self._get_item_keys(value, ignore_list)
					return not len(keys) == 0
			for value in self.values():
				if self.expand_required(value, ignore_list):
					return True
			return False
		
		def expand_value(self, value):
			return self.expand_item(None, value)
		
		def expand_item(self, key=None, value=None):
			self._expand_cache = {}
			value = self._expand_item(key, value)
			self._expand_cache = {}
			return value
		
		def _get_value(self, key, cache = None):
			if cache is not None:
				value = cache.get(key, self.get(key))
			else:
				value = self.get(key)
			if value is not None:
				return value
			if self.parent is not None:
				return self.parent._get_value(key, cache)
			else:
				return None
		
		def _expand_item(self, key=None, value=None):
			if key is None and value is None: 
				return '' 
			stack = []
			stack.append(key)
			irreplaceable = set()
			while True:
				item_key = stack.pop()
				item_value = value if item_key is None else self._get_value(item_key, self._expand_cache)
				if item_value is not None:
					if self.expand_required(item_value):
						replace_keys = self._get_item_keys(item_value)
						for replace_key in list(replace_keys):
							if replace_key in stack:
								replace_keys.remove(replace_key)
								irreplaceable.add(replace_key)
								continue
							replace_value = self._get_value(replace_key, self._expand_cache)
							if replace_value is None:
								replace_keys.remove(replace_key)
								irreplaceable.add(replace_key)
							elif not self.expand_required(replace_value, irreplaceable):
								replace_keys.remove(replace_key)
								item_value = item_value.replace('${' + replace_key + '}', replace_value)
						if len(replace_keys) > 0:
							stack.append(item_key)
							for replace_key in replace_keys:
								stack.append(replace_key)
				if item_key is not None:
					self._expand_cache[item_key] = item_value
				if len(stack) == 0:
					break
			return next((item for item in [item_value, key, value] if item is not None), '')
		
		def _expand_self(self):
			if not self.expand_required():
				return
			for k, v in self.items():
				if v is None: 
					self[k] = ''
					continue
				if self.expand_required(v):
					self[k] = self._expand_item(k) 
		
		def _add_build_properties(self, pom_io, xroot):
			if pom_io is None:
				return
			self._expand_cache = {}
			# initial
			self['basedir'] = pom_io.dir_path
			self['project.basedir'] = self['basedir']
			self.internal.add('basedir')
			self.internal.add('project.basedir')
			# SuperPOM (build)
			self['project.build.directory'] = self._expand_item('${project.basedir}/target')
			self['project.build.outputDirectory'] = self._expand_item('${project.build.directory}/classes')
			self['project.build.testOutputDirectory'] = self._expand_item('${project.build.directory}/test-classes')
			self['project.build.sourceDirectory'] = self._expand_item('${project.basedir}/src/main/java')
			self['project.build.scriptSourceDirectory'] = self._expand_item('${project.basedir}/src/main/scripts')
			self['project.build.testSourceDirectory'] = self._expand_item('${project.basedir}/src/test/java')
			self['project.build.resources.resource.directory'] = self._expand_item('${project.basedir}/src/main/resources')
			self['project.build.testResources.testResource.directory'] = self._expand_item('${project.basedir}/src/test/resources')
			self.internal.add('project.build.directory')
			self.internal.add('project.build.outputDirectory')
			self.internal.add('project.build.testOutputDirectory')
			self.internal.add('project.build.sourceDirectory')
			self.internal.add('project.build.scriptSourceDirectory')
			self.internal.add('project.build.testSourceDirectory')
			self.internal.add('project.build.resources.resource.directory')
			self.internal.add('project.build.testResources.testResource.directory')
			xbuild = Pom.Xml.get_node(xroot, 'build')
			if xbuild is not None:
				tags = ['directory', 'outputDirectory', 'testOutputDirectory', 'sourceDirectory', 'scriptSourceDirectory', 'testSourceDirectory']
				tagz = ['resources', 'testResources']
				for xnode in xbuild:
					tag = Pom.Xml.get_clean_tag(xnode)
					if tag in tags:
						value = Pom.Xml.get_node_value(xnode, '')
						if len(value) > 0: 
							self['project.build.' + tag] = self._expand_item(value)
					elif tag in tagz:
						subtag = tag[:-1]
						xsubnode = Pom.Xml.get_node(xnode, subtag)
						if xsubnode is None:
							continue
						value = Pom.Xml.get_child_node_value(xsubnode, 'directory', '')
						if len(value) > 0: 
							self['project.build.{0}.{1}.directory'.format(tag, subtag)] = self._expand_item(value)
			self._expand_cache = {}
		
		def _add_project_properties(self, xroot):
			self._expand_cache = {}
			# SuperPOM (artifact)
			parent_tag = Pom.Xml.get_clean_tag(xroot)
			if parent_tag == 'project':
				artifact = Pom.Artifact.parse(xroot, Pom.ArtifactOrigin.PROJECT)
				if artifact is not None:
					self['project.groupId'] = artifact.groupId
					self['project.artifactId'] = artifact.artifactId
					self['project.version'] = artifact.version
					self.internal.add('project.groupId')
					self.internal.add('project.artifactId')
					self.internal.add('project.version')
				self['project.finalName'] = self._expand_item('${project.artifactId}-${project.version}')
				self.internal.add('project.finalName')
			self._expand_cache = {}
		
		def _add_session_properties(self, pom_io):
			self._expand_cache = {}
			key = 'session.executionRootDirectory'
			value = None
			if self.parent is not None:
				value = self.parent._get_value(key)
				if value is not None:
					return
			if pom_io is not None:
				self.add_internal(key, pom_io.dir_path)
		
		def add_internal(self, key, value):
			self[key] = value
			self.internal.add(key)
		
		def get_list(self, internal=False):
			properties = {}
			for k, v in self.items():
				if not k in self.internal:
					properties[k] = v
			return properties
		
		@classmethod
		def create_root(cls):
			properties = cls()
			for k,v in os.environ.items():
				properties.add_internal('env.' + k, v)
			if not 'env.M2_HOME' in properties:
				m2_home = Pom.Env.get_maven_home()
				if m2_home is not None:
					properties['env.M2_HOME'] = m2_home
			
			properties.add_internal('file.separator', os.sep)
			# TODO: java.home, java.vendor, java.vendor.url, java.version, java.class.path
			#       line.separator, path.separator
			properties.add_internal('os.arch', Pom.OS.get_system_arch())
			properties.add_internal('os.name', Pom.OS.get_system_family())
			properties.add_internal('os.version', Pom.OS.get_system_version())
			properties.add_internal('user.home', Pom.Env.get_user_home())
			properties.add_internal('user.name', Pom.Env.get_user_name())
			return properties
		
		@classmethod
		def create(cls, xroot, parent_properties=None, pom_io=None):
			properties = cls()
			properties.__parent = parent_properties
			properties._add_build_properties(pom_io, xroot)
			properties._add_project_properties(xroot)
			properties._add_session_properties(pom_io)
			xproperties = Pom.Xml.get_properties(xroot)
			for xproperty in xproperties:
				if xproperty.tag is etree.Comment:
					continue
				key = Pom.Xml.get_clean_tag(xproperty)
				value = Pom.Xml.get_node_value(xproperty, '') 
				properties[key] = value
			properties._expand_cache = {}
			properties._expand_self()
			properties._expand_cache = {}
			return properties
	
	class ArtifactOrigin(object):
		UNKNOWN = 0
		PROJECT = 1
		DEPENDENCY = 2
		
		@staticmethod
		def ensure(value):
			if 0 < value > 2:
				return Pom.ArtifactOrigin.UNKNOWN
			else:
				return value
	
	class ArtifactVersion(object):
		def __init__(self, version):
			self.__major = None
			self.__minor = None
			self.__incremental = None
			self.__build_number = None
			self.__qualifier = None
			self._parse(version)
			self.__comparer = Pom.VersionComparer(version)
		
		@property
		def major(self):
			return self.__major or 0
		
		@property
		def minor(self):
			return self.__minor or 0
		
		@property
		def incremental(self):
			return self.__incremental or 0
		
		@property
		def build_number(self):
			return self.__build_number or 0
		
		@property
		def qualifier(self):
			return self.__qualifier
		
		@property
		def comparer(self):
			return self.__comparer
		
		def compare_to(self, other):
			if isinstance(other, self.__class__):
				return self.__comparer.compare_to(other.comparer)
			else:
				return self.compare_to(Pom.ArtifactVersion(str(other)))
		
		def _get_int(self, value):
			int_value = int(value)
			if int_value > 2147483647 or int_value < -2147483648:
				raise ValueError('32bit integer overflow')
			return int_value
		
		def _get_token_int(self, tokens):
			try:
				value = tokens.pop(0)
			except IndexError:
				raise ValueError('Number is invalid: "{0}"'.format(value))
			if len(value) > 1 and value.startswith('0'):
				raise ValueError('Number part has a leading 0: "{0}"'.format(value))
			return self._get_int(value)
		
		def _parse(self, version):
			idx = version.find('-')
			p1 = '';
			p2 = None
			if idx < 0:
				p1 = version
			else:
				p1 = version[0:idx]
				p2 = version[idx+1:]
			if p2 is not None:
				try:
					if len(p2) == 1 or not p2.startswith('0'):
						self.__build_number = self._get_int(p2) 
					else:
						self.__qualifier = p2
				except ValueError:
					self.__qualifier = p2
			if p1.find('.') < 0 and not p1.startswith('0'):
				try:
					self.__major = self._get_int(p1)
				except ValueError:
					self.__qualifier = version
					self.__build_number = None
			else:
				fallback =  p1.find('..') >= 0 or p1.startswith('.') or p1.endswith('.')
				if not fallback:
					tokens = p1.split('.')
					try:
						self.__major = self._get_token_int(tokens)
						if tokens:
							self.__minor = self._get_token_int(tokens)
						if tokens:
							self.__incremental = self._get_token_int(tokens)
						if tokens:
							self.__qualifier = tokens.pop(0)
							fallback = self.__qualifier.isdigit()
					except ValueError:
						fallback = True
				if fallback:
					self.__qualifier = version
					self.__major = None
					self.__minor = None
					self.__incremental = None
					self.__build_number = None
		
		def __str__(self):
			return str(self.__comparer)
		
		def __eq__(self, other):
			return isinstance(other, self.__class__) and self.compare_to(other) == 0
		
		def __ne__(self, other):
			return not self.__eq__(other)
		
		def __hash__(self):
			return 11 + hash(self.__comparer)
	
	class VersionComparer(object):
		def __init__(self, version):
			self._parse(version)
		
		@property
		def value(self):
			return self.__value
		
		@property
		def canonical(self):
			return self.__canonical
		
		@property
		def items(self):
			return self.__items
		
		def compare_to(self, other):
			return isinstance(other, self.__class__) and self.items.compare_to(other.items)
		
		def _parse(self, version):
			self.__value = version
			self.__items = Pom.VersionComparer.ListItem()
			
			version = version.lower()
			lizt  = self.__items
			stack = []
			stack.append(lizt)
			is_digit = False
			start_idx = 0
			
			for idx in xrange(0, len(version)):
				c = version[idx]
				new_list = False
				if c == '.' or c == '-':
					if idx == start_idx:
						lizt.append(Pom.VersionComparer.IntegerItem(0))
					else:
						lizt.append(self._parse_item(is_digit, version[start_idx:idx]))
					start_idx = idx + 1
					if c == '-':
						new_list = True
				elif c.isdigit():
					if not is_digit and idx > start_idx:
						lizt.append(Pom.VersionComparer.StringItem(version[start_idx:idx], True))
						start_idx = idx
						new_list = True
					is_digit = True
				else:
					if is_digit and idx > start_idx:
						lizt.append(self._parse_item(True, version[start_idx:idx]))
						start_idx = idx
						new_list = True
					is_digit = False
				
				if new_list:
					new_lizt = Pom.VersionComparer.ListItem()
					lizt.append(new_lizt)
					lizt = new_lizt
					stack.append(lizt)
			
			if len(version) > start_idx:
				lizt.append(self._parse_item(is_digit, version[start_idx:]))
			while stack:
				lizt = stack.pop()
				lizt._normalize()
			self.__canonical = str(self.items)
		
		def _parse_item(self, is_digit, value):
			if is_digit:
				return Pom.VersionComparer.IntegerItem(value)
			else:
				return Pom.VersionComparer.StringItem(value, False)
		
		def __str__(self):
			return self.value
		
		def __eq__(self, other):
			return isinstance(other, self.__class__) and self.canonical == other.canonical
		
		def __ne__(self, other):
			return not self.__eq__(other)
		
		def __hash__(self):
			return hash(self.canonical)
		
		
		class Item(object):
			def __init__(self, value=None):
				self.__value = value
			
			@property
			def value(self):
				return self.__value
			
			def _raise(self, method):
				raise NotImplementedError("{0}.{1}".format(self.__class__.__name__, method))
			
			@property
			def is_null(self):
				self._raise('is_null')
			
			def compare_to(self, value):
				self._raise('compare_to()')
			
			def __str__(self):
				self._raise('__str__()')
		
		
		class IntegerItem(Item):
			def __init__(self, value=None):
				value = int(value) if value is not None else 0
				super(self.__class__, self).__init__(value)
			
			@property
			def is_null(self):
				return self.value == 0
			
			def compare_to(self, item):
				if item is None:
					return 0 if self.is_null else 1 # 1.0 == 1, 1.1 > 1
				item_type = type(item)
				if item_type is Pom.VersionComparer.IntegerItem:
					return cmp(self.value, item.value)
				elif item_type is Pom.VersionComparer.StringItem:
					return 1 # 1.1 > 1-sp
				elif item_type is Pom.VersionComparer.ListItem:
					return 1 # 1.1 > 1-1
				else:
					raise TypeError('Noncompareable type: %s' % type(item))
			
			def __str__(self):
				return str(self.value)
			
			def __repr__(self):
				return str(self)
		
		
		class StringItem(Item):
			QUALIFIERS = ["alpha", "beta", "milestone", "rc", "snapshot", "", "sp"]
			ALIASES = {"ga":"", "final":"", "cr":"rc"}
			RELEASE_VERSION_INDEX = str(QUALIFIERS.index(""))
			
			def __init__(self, value, followed_by_digit):
				if followed_by_digit and len(value) == 1:
					replaces = {'a':'alpha', 'b':'beta', 'm':'milestone'}
					value = replaces.get(value[0], value)
				value = self.ALIASES.get(value, value)
				super(self.__class__, self).__init__(value)
			
			@property
			def is_null(self):
				return cmp(self._cmp_qualifier(self.value), self.RELEASE_VERSION_INDEX) == 0
			
			def _cmp_qualifier(self, qualifier):
				idx = self.QUALIFIERS.index(qualifier) if qualifier in self.QUALIFIERS else None
				if idx is None:
					return "{0}-{1}".format(len(self.QUALIFIERS), qualifier)
				else:
					return str(idx)
			
			def compare_to(self, item):
				if item is None:
					return cmp(self._cmp_qualifier(self.value), self.RELEASE_VERSION_INDEX) # 1-rc < 1, 1-ga > 1
				item_type = type(item)
				if item_type is Pom.VersionComparer.IntegerItem:
					return -1 # 1.any < 1.1 ?
				if item_type is Pom.VersionComparer.StringItem:
					return cmp(self._cmp_qualifier(self.value), self._cmp_qualifier(item.value))
				if item_type is Pom.VersionComparer.ListItem:
					return -1 # 1.any < 1.1
				else:
					raise TypeError('Noncompareable type: %s' % type(item))
			
			def __str__(self):
				return self.value
			
			def __repr__(self):
				return "'{0}'".format(str(self))
		
		
		class ListItem(list, Item):
			def __init__(self, *args, **kwargs):
				list.__init__(self, *args, **kwargs)
			
			@property
			def is_null(self):
				return len(self) == 0
			
			def compare_to(self, item):
				if item is None:
					if len(self) == 0:
						return 0 # 1-0 = 1- (normalize) = 1
					else:
						return self[0].compare_to(None)
				item_type = type(item)
				if item_type is Pom.VersionComparer.IntegerItem:
					return -1 # 1-1 < 1.0.x
				if item_type is Pom.VersionComparer.StringItem:
					return 1 # 1-1 > 1-sp
				if item_type is Pom.VersionComparer.ListItem:
					idx = 0
					mlen = len(self)
					olen = len(item)
					while idx < mlen or idx < olen:
						left = self[idx] if idx < mlen else None
						right = item[idx] if idx < olen else None
						if left is None:
							if right is None:
								return 0
							else:
								result = right.compare_to(left) * -1
						else:
							result = left.compare_to(right) 
						if result != 0:
							return result
						idx += 1
					return 0
				else:
					raise TypeError('Noncompareable type: %s' % type(item))
			
			def _normalize(self):
				for idx in xrange(len(self) - 1, -1, -1):
					item = self[idx]
					if item.is_null:
						del self[idx]
					elif not isinstance(item, Pom.VersionComparer.ListItem):
						break
			
			def __str__(self):
				buf = ""
				for item in self:
					if len(buf) > 0:
						buf += '-' if isinstance(item, self.__class__) else '.'
					buf += str(item)
				return buf
	
	class VersionRange(object):
		def __init__(self, recommended_version, restrictions):
			self.__recommended_version = recommended_version
			self.__restrictions = restrictions
		
		@property
		def recommended_version(self):
			return self.__recommended_version
		
		@property
		def restrictions(self):
			return self.__restrictions
		
		@property
		def has_restrictions(self):
			return self.__restrictions is not None and len(self.__restrictions) > 0
		
		@property
		def selected_version(self):
			if self.__recommended_version is not None:
				return self.__recommended_version
			else:
				if len(self.__restrictions) == 0:
					raise Pom.VersionException('No valid ranges found')
			return None
		
		@property
		def is_selected_version_known(self):
			try:
				return self.selected_version is not None
			except Pom.VersionException:
				return False
		
		def contains_version(self, version):
			if not isinstance(version, Pom.ArtifactVersion):
				version = Pom.ArtifactVersion(version)
			for restriction in self.__restrictions:
				if restriction.contains_version(version):
					return True
			return False
		
		def restrict(self, other):
			r1 = self.__restrictions
			r2 = other.restrictions
			if (r1 is None or len(r1) == 0) or (r2 is None or len(r2) == 0):
				restrictions = []
			else:
				restrictions = self._intersection(r1, r2)
			version = None
			if len(restrictions) > 0:
				for r in self.__restrictions:
					if self.__recommended_version is not None and r.contains_version(self.__recommended_version):
						version = self.__recommended_version
						break
					elif version is None and other.recommended_version is not None and r.contains_version(other.recommended_version):
						version = other.recommended_version
			elif self.__recommended_version is not None:
				version = self.__recommended_version
			elif other.recommended_version is not None:
				version = other.recommended_version
			return Pom.VersionRange(version, restrictions)
		
		def _intersection(self, r1, r2):
			restrictions = []
			i1 = iter(r1)
			i2 = iter(r2)
			res1 = i1.next()
			res2 = i2.next()
			
			done = False
			while not done:
				if res1.lower_bound is None or res2.upper_bound is None or res1.lower_bound.compare_to(res2.upper_bound) <= 0:
					if res1.upper_bound is None or res2.lower_bound is None or res1.upper_bound.compare_to(res2.lower_bound) >= 0:
						if res1.lower_bound is None:
							lower = res2.lower_bound
							lower_inclusive = res2.lower_inclusive
						elif res2.lower_bound is None:
							lower = res1.lower_bound
							lower_inclusive = res1.lower_inclusive
						else:
							cmp_res = res1.lower_bound.compare_to(res2.lower_bound)
							if cmp_res < 0:
								lower = res2.lower_bound
								lower_inclusive = res2.lower_inclusive
							elif cmp_res == 0:
								lower = res1.lower_bound
								lower_inclusive = res1.lower_inclusive and res2.lower_inclusive
							else:
								lower = res1.lower_bound
								lower_inclusive = res1.lower_inclusive
						if res1.upper_bound is None:
							upper = res2.upper_bound
							upper_inclusive = res2.upper_inclusive
						elif res2.upper_bound is None:
							upper = res1.upper_bound
							upper_inclusive = res1.upper_inclusive
						else:
							cmp_res = res1.upper_bound.compare_to(res2.upper_bound)
							if cmp_res < 0:
								upper = res1.upper_bound
								upper_inclusive = res1.upper_inclusive
							elif cmp_res == 0:
								upper = res1.upper_bound
								upper_inclusive = res1.upper_inclusive and res2.upper_inclusive
							else:
								upper = res2.upper_bound
								upper_inclusive = res2.upper_inclusive
						# do not add if they are equal and one is not inclusive
						if lower is None or upper is None or lower.compare_to(upper) != 0:
							restrictions.append(Pom.VersionRestriction(lower, lower_inclusive, upper, upper_inclusive))
						elif lower_inclusive and upper_inclusive:
							restrictions.append(Pom.VersionRestriction(lower, lower_inclusive, upper, upper_inclusive))
						
						# no-inspection object equality
						if upper == res2.upper_bound:
							try:
								res2 = i2.next()
							except StopIteration:
								done = True
						else:
							try:
								res1 = i1.next()
							except StopIteration:
								done = True
					else:
						try:
							res1 = i1.next()
						except StopIteration:
							done = True
				else:
					try:
						res2 = i2.next()
					except StopIteration:
						done = True
			return restrictions
		
		@staticmethod
		def create_from_version(version):
			return Pom.VersionRange(ArtifactVersion(version), [])
		
		@staticmethod
		def create_from_version_spec(spec):
			if spec is None:
				return None
			restrictions = []
			process = spec
			version = None
			lower_bound = None
			upper_bound = None
			
			while process.startswith('[') or process.startswith('('):
				idx1 = process.find(')')
				idx = idx2 = process.find(']')
				if (idx < 0 or idx1 < idx2) and (idx1 >= 0):
					idx = idx1
				if idx < 0:
					raise Pom.VersionException('Unbounded range: ' + spec)
				restriction = Pom.VersionRange._parse_restriction(process[0:idx+1])
				if lower_bound is None:
					lower_bound = restriction.lower_bound
				if upper_bound is not None:
					lb = restriction.lower_bound
					if  lb is None or lb.compare_to(upper_bound) < 0:
						raise Pom.VersionException('Ranges overlap: ' + spec)
				restrictions.append(restriction)
				upper_bound = restriction.upper_bound
				process = process[idx + 1:].strip()
				if len(process) > 0 and process.startswith(','):
					process = process[1:].strip()
			if len(process) > 0:
				if len(restrictions) > 0:
					raise Pom.VersionException('Only fully-qualified sets allowed in multiple set scenario: ' + spec)
				else:
					version = Pom.ArtifactVersion(process)
					restrictions.append(Pom.VersionRestriction.allow_everything())
			return Pom.VersionRange(version, restrictions)
		
		
		@staticmethod
		def _parse_restriction(spec):
			lower_inclusive = spec.startswith('[')
			upper_inclusive = spec.endswith(']')
			process = spec[1:-1].strip()
			idx = process.find(',')
			if idx < 0:
				if not lower_inclusive or not upper_inclusive:
					raise Pom.VersionException('Single version must be surrounded by []: ' + spec)
				version = Pom.ArtifactVersion(process)
				return Pom.VersionRestriction(version, lower_inclusive, version, upper_inclusive)
			else:
				lower_bound = process[0:idx].strip()
				upper_bound = process[idx+1:].strip()
				if lower_bound == upper_bound:
					raise Pom.VersionException('Range cannot have identical boundries: ' + spec)
				lower_version = Pom.ArtifactVersion(lower_bound) if len(lower_bound) > 0 else None
				upper_version = Pom.ArtifactVersion(upper_bound) if len(upper_bound) > 0 else None
				if upper_version is not None and lower_version is not None and upper_version.compare_to(lower_version) < 0:
					raise Pom.VersionException('Ranges defies version ordering: ' + spec)
				return Pom.VersionRestriction(lower_version, lower_inclusive, upper_version, upper_inclusive)
		
		def __eq__(self, other):
			if not isinstance(other, self.__class__):
				return False
			if self.__recommended_version == other.__recommended_version:
				equals = True
			else:
				equals = (self.__recommended_version is not None and self.__recommended_version == other.__recommended_version)
			if equals == False:
				return False
			if not self.__restrictions == other.__restrictions:
				equals &= (self.__restrictions is not None and self.__restrictions == other.__restrictions)
			return equals
		
		def __ne__(self, other):
			return not self.__eq__(other)
		
		def __hash__(self):
			value = 7
			value = 31 * value + (hash(self.__recommended_version) if self.__recommended_version is not None else 0)
			value = 31 * value + (hash(self.__restrictions) if self.__restrictions is not None else 0)
			return value
			
		def __str__(self):
			if self.__recommended_version is not None:
				return str(self.__recommended_version)
			else:
				return ','.join(str(v) for v in self.__restrictions)
	
	class VersionException(Exception):
		pass
	
	class VersionRestriction(object):
		def __init__(self, lower_bound, lower_inclusive, upper_bound, upper_inclusive):
			self.__lower_bound = lower_bound
			self.__lower_inclusive = lower_inclusive
			self.__upper_bound = upper_bound
			self.__upper_inclusive = upper_inclusive
		
		@property
		def lower_bound(self):
			return self.__lower_bound
		
		@property
		def upper_bound(self):
			return self.__upper_bound
		
		@property
		def lower_inclusive(self):
			return self.__lower_inclusive
		
		@property
		def upper_inclusive(self):
			return self.__upper_inclusive
		
		@staticmethod
		def allow_everything():
			return Pom.VersionRestriction(None, False, None, False)
		
		def contains_version(self, version):
			if not isinstance(version, Pom.ArtifactVersion):
				return False
			if self.__lower_bound is not None:
				cmp_ret = self.__lower_bound.compare_to(version)
				if cmp_ret == 0 and not self.__lower_inclusive:
					return False
				if cmp_ret > 0:
					return False
			if self.__upper_bound is not None:
				cmp_ret = self.__upper_bound.compare_to(version)
				if cmp_ret == 0 and not self.__upper_inclusive:
					return False
				if cmp_ret < 0:
					return False
			return True
		
		def __eq__(self, other):
			if not isinstance(other, self.__class__):
				return False
			if self.__lower_bound is not None:
				if self.__lower_bound != other.__lower_bound:
					return False
			elif other.__lower_bound is not None:
				return False
			if self.__lower_inclusive != other.__lower_inclusive:
				return False
			if self.__upper_bound is not None:
				if self.__upper_bound != other.__upper_bound:
					return False
			elif other.__upper_bound is not None:
				return False
			return self.__upper_inclusive == other.__upper_inclusive
		
		def __ne__(self, other):
			return not self.__eq__(other)
		
		def __hash__(self):
			res = 13
			if self.__lower_bound is not None:
				res += 1
			else:
				res += hash(self.__lower_bound)
			res = res * (1 if self.__lower_inclusive else 2)
			if self.__upper_bound is not None:
				res -= 3
			else:
				res -= hash(self.__upper_bound)
			res = res * (2 if self.__upper_inclusive else 3)
			return res
		
		def __str__(self):
			buf = ''
			buf += '[' if self.__lower_inclusive else '('
			if self.__lower_bound is not None:
				buf += str(self.__lower_bound)
			buf += ','
			if self.__upper_bound is not None:
				buf += str(self.__upper_bound)
			buf += ']' if self.__upper_inclusive else ')'
			return buf
		
		def __repr__(self):
			return "'" + self.__str__() + "'"
	
	class Artifact(object):
		def __init__(self, origin, parent, groupId, artifactId, packaging, classifier, version):
			self.__origin = Pom.ArtifactOrigin.ensure(origin)
			self.__parent = parent
			self.__groupId = groupId
			self.__artifactId = artifactId
			self.__packaging = packaging
			self.__classifier = classifier
			self.__version = version
			self.__moduleId = self.get_module_id()
		
		@property
		def origin(self):
			return self.__origin
		
		@property
		def parent(self):
			return self.__parent
		
		@property
		def groupId(self):
			return self.__groupId if len(self.__groupId) > 0 else self.__parent.__groupId
		
		@property
		def artifactId(self):
			return self.__artifactId
			
		@property
		def version(self):
			return self.__version if len(self.__version) > 0 else self.__parent.__version
		
		@property
		def packaging(self):
			return self.__packaging
		
		@property
		def classifier(self):
			return self.__classifier
		
		@property
		def moduleId(self):
			return self.__moduleId
		
		@staticmethod
		def get_parts(module_name):
			p = module_name.split(':')
			l = len(p)
			clean = lambda v: None if v == '*' else v.strip()
			if l == 1:
				return {'artifactId': clean(p[0])}
			if 3 < l > 5:
				return {}
			if l >= 3:
				parts = {'groupId': clean(p[0]), 'artifactId': clean(p[1])}
			if l == 3:
				parts['version'] = clean(p[2])
			elif l == 4:
				parts['packaging'] = clean(p[2])
				parts['version'] = clean(p[3])
			elif l == 5:
				parts['packaging'] = clean(p[2])
				parts['classifier'] = clean(p[3])
				parts['version'] = clean(p[4])
			return parts
		
		def match(self, groupId=None, artifactId=None, packaging=None, classifier=None, version=None):
			if groupId is not None and self.groupId != groupId: return False
			if artifactId is not None and self.artifactId != artifactId: return False
			if packaging is not None and self.packaging != packaging: return False
			if classifier is not None and self.classifier != classifier: return False
			if version is not None and self.version != version: return False
			return True
		
		def match_name(self, name):
			parts = Pom.Artifact.get_parts(name)
			return self.match(parts.get('groupId'),
			                  parts.get('artifactId'),
			                  parts.get('packaging'),
			                  parts.get('classifier'),
			                  parts.get('version'))
		
		def get_module_id(self, full=False):
			moduleId = self.groupId + ':' + self.artifactId + ':'
			if full:
				if len(self.classifier) > 0:
					moduleId += self.packaging + ':' + self.classifier + ':'
				elif self.packaging and self.packaging != 'jar':
					moduleId += self.packaging + ':'
			moduleId += self.version
			return moduleId
		
		def __eq__(self, other):
			return self.get_module_id() == other.get_module_id()
		
		def __ne__(self, other):
			return not self.__eq__(other)
		
		def __hash__(self):
			return hash(self.get_module_id(True))
		
		def __str__(self):
			return self.get_module_id(True)
		
		def __repr__(self):
			return "Pom.Artifact(%s)" % str(self)
		
		@staticmethod
		def parse(xroot, origin=0, module=None):
			origin = Pom.ArtifactOrigin.ensure(origin)
			
			properties = module.properties if module else Pom.Properties()
			managed_dependencies = module.all_managed_dependencies if module else Pom.Dependencies()
			
			parent = None
			parent_tag = Pom.Xml.get_clean_tag(xroot)
			if parent_tag == 'project' or origin == Pom.ArtifactOrigin.PROJECT:
				xparent = Pom.Xml.get_node(xroot, 'parent')
				if xparent is not None:
					parent = Pom.Artifact.parse(xparent, origin)
			expand = lambda v: properties.expand_value(v) if properties.expand_required(v) else v
			
			artifactId = expand(Pom.Xml.get_artifact_id(xroot))
			if len(artifactId) == 0:
				raise Exception("artifactId not defined")
			groupId = expand(Pom.Xml.get_group_id(xroot))
			version = expand(Pom.Xml.get_version(xroot))
			if len(groupId) == 0 and (parent is None or len(parent.groupId) == 0):
				if len(version) == 0 and (parent is None or len(parent.version) == 0):
					raise Exception("groupId and version not defined for artifact (%s)" % (artifactId))
				if origin != Pom.ArtifactOrigin.DEPENDENCY:
					raise Exception("groupId not defined for artifact (%s::%s)" % (artifactId, version))
				found = None
				mx_version = version or parent.version
				for dependency in managed_dependencies.values():
					if dependency.artifact.match(artifactId=artifactId, version=mx_version):
						found = dependency
				if found is None:
					raise Exception("groupId not defined for dependency (%s::%s)" % (artifactId, version))
				groupId = found.artifact.groupId
			if len(version) == 0 and (parent is None or len(parent.version) == 0):
				if origin != Pom.ArtifactOrigin.DEPENDENCY:
					raise Exception("version not defined for artifact (%s:%s)" % (groupId, artifactId))
				found = None
				mx_groupId = groupId or parent.groupId
				for dependency in managed_dependencies.values():
					if dependency.artifact.match(groupId=mx_groupId, artifactId=artifactId):
						found = dependency
				if found is None:
					raise Exception("version not defined for dependency (%s:%s)" % (groupId, artifactId))
				version = found.artifact.version
			if origin == Pom.ArtifactOrigin.DEPENDENCY:
				packaging = ''
			else:
				packaging = Pom.Xml.get_packaging(xroot)
				if len(packaging) == 0:
					packaging = 'jar'
				if packaging not in ['pom', 'jar', 'maven-plugin', 'ejb', 'war', 'ear', 'rar', 'par', 'rpm']:
					raise Exception("invalid packaging (%s) for artifact (%s:%s:%s)" % (packaging, groupId, artifactId, version))
			classifier = expand(Pom.Xml.get_classifier(xroot))
			return Pom.Artifact(origin, parent, groupId, artifactId, packaging, classifier, version)
	
	class Dependencies(dict):
		def __init__(self, *args, **kwargs):
			dict.__init__(self, *args, **kwargs)
			self.__is_managed = set()
			self.__managed = {}
		
		@property
		def managed(self):
			if self.__managed is None:
				self.__managed = {k: v for k, v in self.items() if k in self.__is_managed}
			return self.__managed
		
		def add(self, dependency):
			if dependency is None or not isinstance(dependency, Pom.Dependency):
				return
			self[dependency.artifact] = dependency
		
		def add_managed(self, dependency):
			self.add(dependency)
			self.__is_managed.add(dependency.artifact)
			self.__managed = None
		
		@staticmethod
		def populate(module, xroot):
			for xdependency in Pom.Xml.get_dependencies(xroot, True):
				try:
					dependency = Pom.Dependency.parse(xdependency, module)
				except Exception as e:
					print "[error] " + e.message
					continue
				module.dependencies.add_managed(dependency)
			for xdependency in Pom.Xml.get_dependencies(xroot, False):
				try:
					dependency = Pom.Dependency.parse(xdependency, module)
				except Exception as e:
					print "[error] " + e.message
					continue
				module.dependencies.add(dependency)
	
	class Dependency(object):
		def __init__(self, artifact, deptype, scope, system_path, optional):
			self.__artifact = artifact
			self.__deptype = deptype
			self.__scope = scope
			self.__system_path = system_path
			self.__optional = optional
		
		@property
		def artifact(self):
			return self.__artifact
		
		@property
		def deptype(self):
			return self.__deptype
		
		@property
		def scope(self):
			return self.__scope
		
		@property
		def system_path(self):
			return self.__system_path
		
		@property
		def optional(self):
			return self.__optional
		
		@staticmethod
		def _get_property(xnode, key, managed_dependencies, artifact, default_value = ''):
			value = Pom.Xml.get_child_node_value(xnode, key, None)
			if value is not None:
				return value
			attr_conv = {'type': 'deptype', 'systemPath': 'system_path'}
			if artifact in managed_dependencies:
				dependency = managed_dependencies[artifact]
				value = getattr(dependency, attr_conv.get(key, key), None)
			if value is None:
				value = default_value
			if value is not None:
				value = str(value)
			return value
		
		@staticmethod
		def parse(xnode, module = None):
			artifact = Pom.Artifact.parse(xnode, Pom.ArtifactOrigin.DEPENDENCY, module)
			managed_dependencies = module.all_managed_dependencies if module else Pom.Dependencies()
			deptype = Pom.Dependency._get_property(xnode, 'type', managed_dependencies, artifact, '')
			scope = Pom.Dependency._get_property(xnode, 'scope', managed_dependencies, artifact, 'compile')
			if scope not in ['compile', 'provided', 'runtime', 'test', 'system']:
				raise Exception('invalid scope (%s) for dependency %s' % (scope, artifact)) 
			if scope == 'system':
				system_path = Pom.Dependency._get_property(xnode, 'systemPath', managed_dependencies, artifact, '')
			else:
				system_path = ''
			optional = Pom.Dependency._get_property(xnode, 'optional', managed_dependencies, artifact, 'false')
			optional = optional.lower() == 'true'
			dependency = Pom.Dependency(artifact, deptype, scope, system_path, optional)
			return dependency
		
		def __repr__(self):
			rest = [self.deptype, 'optional' if self.optional else '']
			rest = ', '.join([i for i in rest if len(i) > 0])
			if len(rest) > 0: rest = ', ' + rest
			return "Pom.Dependency(%s, %s%s)" % (self.scope, self.artifact, rest)
	
	class BuildNode(object):
		def __init__(self):
			self.__weight_cache = {}
			self.__properties = Pom.Properties()
			self.__repositories = Pom.ArtifactRepositories()
			self.__plugin_repositories = Pom.ArtifactRepositories()
			self.__modules = Pom.Modules()
		
		def _raise(self, method):
			raise NotImplementedError("{0}.{1}".format(self.__class__.__name__, method))
		
		@property
		def pure_weight(self):
			self._raise('pure_weight')
		
		@property
		def depth(self):
			self._raise('depth')
		
		@property
		def properties(self):
			return self.__properties
		
		@property
		def repositories(self):
			return self.__repositories
		
		@property
		def plugin_repositories(self):
			return self.__plugin_repositories
		
		@property
		def modules(self):
			return self.__modules
		
		def _set_properties(self, properties):
			self.__properties = properties
		
		def _set_repositories(self, repositories, plugin_repositories):
			self.__repositories = repositories
			self.__plugin_repositories = plugin_repositories
		
		def _set_modules(self, modules):
			self.__modules = modules
		
		def get_weight(self, bp = None, artifacts = None, level = 0):
			if bp not in self.__weight_cache:
				self.__weight_cache[bp] = self._get_weight(bp)
			return self.__weight_cache[bp]
		
		def _get_weight(self, bp = None, artifacts = None, level = 0):
			if artifacts is None:
				artifacts = set()
			subweight = 0
			try:
				for m in self.modules.values():
					if m is None: continue
					subweight += m._get_weight(bp, artifacts, level + 1)
			except (AttributeError, TypeError):
				pass
			try:
				for p in self.profiles.values():
					if p is None: continue
					if bp is None or bp.is_profile_active(p):
						subweight += p._get_weight(bp, artifacts, level + 1)
			except (AttributeError, TypeError):
				pass
			weight = self.pure_weight + subweight
			try:
				a = self.artifact
				if a in artifacts:
					weight = 0
				else:
					artifacts.add(a)
			except (AttributeError, TypeError):
				pass
			return weight
	
	class Modules(dict):
		def __init__(self, *args, **kwargs):
			dict.__init__(self, *args, **kwargs)
		
		@classmethod
		def create(cls, pom_io, xroot, parent = None):
			modules = cls()
			for xmodule in Pom.Xml.get_modules(xroot):
				module_name = xmodule.text.strip()
				if len(module_name) == 0: 
					continue
				if module_name in modules: 
					continue
				#modules[module_name] = None
				if os.path.isdir(os.path.join(pom_io.dir_path, module_name)):
					pom_file = os.path.join(pom_io.dir_path, module_name, 'pom.xml')
					pom_module = Pom.Module.create(pom_file, parent)
					if pom_module is not None:
						modules[module_name] = pom_module
				else:
					pom_file = os.path.join(pom_io.dir_path, module_name)
					pom_module = Pom.Module.create(pom_file, parent)
					if pom_module is not None:
						modules[module_name] = pom_module
			return modules
	
	class Module(BuildNode):
		def __init__(self, artifact):
			super(self.__class__, self).__init__()
			self.__artifact = artifact
			self.__parent = None
			self.__dependencies = Pom.Dependencies()
			self.__profiles = Pom.Profiles()
		
		@property
		def pure_weight(self):
			return 1.0000
		
		@property
		def depth(self):
			if self.parent is None:
				return 0
			else:
				return self.parent.depth + 1

		@property
		def artifact(self):
			return self.__artifact
		
		@property
		def parent(self):
			return self.__parent
		
		@property
		def dependencies(self):
			return self.__dependencies
		
		@property
		def profiles(self):
			return self.__profiles
		
		@property
		def all_managed_dependencies(self):
			dependencies = Pom.Dependencies()
			stack = []
			parent = self.parent
			while parent is not None:
				stack.append(parent.dependencies.managed)
				parent = parent.parent
			while stack:
				dependencies.update(stack.pop())
			dependencies.update(self.dependencies.managed)
			return dependencies
		
		def show_graph(self, bgc = None, matched = False):
			if bgc is None:
				bgc = Pom.BuildGraphConf()
			if len(self.artifact.artifactId) > 0:
				module_name = self.artifact.artifactId
			else:
				module_name = '__unnamed__'
			conf = bgc.fork({module_name: self}, None, self.depth)
			conf.parent_matched = matched
			Pom.BuildGraph.show(conf)
		
		@staticmethod
		def _parse_parent(xroot, pom_io, artifact):
			parent_path = None
			validate = False
			parent_relpath = Pom.Xml.get_parent_relpath(xroot) 
			if len(parent_relpath) > 0:
				parent_path = os.path.abspath(os.path.join(pom_io.dir_path, parent_relpath))
				if os.path.isdir(parent_path):
					parent_filepath = os.path.join(parent_path, 'pom.xml')
				else:
					parent_filepath = parent_path
				if os.path.isfile(parent_filepath):
					parent_path = parent_filepath
			if parent_path is None:
				validate = True
				parent_filepath = os.path.abspath(os.path.join(pom_io.dir_path, '..', 'pom.xml'))
				if os.path.isfile(parent_filepath):
					parent_path = parent_filepath
			if parent_path is not None:
				if parent_path in pom.module_cache:
					return pom.module_cache[parent_path]
				return Pom.Module.create(Pom.IO(parent_path))
			return None
		
		@staticmethod
		def create(pom_io, parent = None):
			if not isinstance(pom_io, Pom.IO):
				pom_io = Pom.IO(pom_io)
			if not os.path.isfile(pom_io.file_path):
				return None
			if pom_io.file_path in pom.module_cache:
				return pom.module_cache[pom_io.file_path]
			
			parser = etree.XMLParser(recover=True)
			xtree = etree.parse(pom_io.file_path, parser)
			xroot = xtree.getroot()
			if xroot is None:
				return None 
			
			artifact = Pom.Artifact.parse(xroot, Pom.ArtifactOrigin.PROJECT)
			if artifact is None:
				return None
			module = Pom.Module(artifact)
			pom.module_cache[pom_io.file_path] = module
			
			if parent is not None:
				module.__parent = parent
			else:
				if artifact.parent is not None:
					module.__parent = Pom.Module._parse_parent(xroot, pom_io, artifact)
				else:
					module.__parent = None
			
			parent_properties = module.parent.properties if module.parent else pom.properties
			properties = Pom.Properties.create(xroot, parent_properties, pom_io)
			module._set_properties(properties)
			
			repositories = Pom.ArtifactRepositories.create(xroot, False)
			plugin_repositories = Pom.ArtifactRepositories.create(xroot, True)
			module._set_repositories(repositories, plugin_repositories)
			
			Pom.Dependencies.populate(module, xroot)
			
			modules = Pom.Modules.create(pom_io, xroot, module)
			module._set_modules(modules)
			module.__profiles = Pom.Profiles.create(pom_io, xroot, module)
			return module
		
		def __str__(self):
			return str(self.artifact)
		
		def __repr__(self):
			return "Pom.Module(%s)" % str(self)
	
	class Profiles(dict):
		def __init__(self, *args, **kwargs):
			dict.__init__(self, *args, **kwargs)
		
		def add(self, profile):
			self[profile.name] = profile
		
		@classmethod
		def create(cls, pom_io, xroot, module = None):
			profiles = cls()
			for xprofile in Pom.Xml.get_profiles(xroot):
				profile_name = Pom.Xml.get_id(xprofile)
				if len(profile_name) == 0: 
					continue
				if profile_name in profiles: 
					continue
				profile = Pom.Profile.create(pom_io, xprofile, module)
				if profile is None: 
					continue
				profiles.add(profile) 
			return profiles
	
	class Profile(BuildNode):
		def __init__(self, name, properties, activation):
			super(self.__class__, self).__init__()
			self.__name = name
			self.__activation = activation
			self.__depth = 0
			self._set_properties(properties)
		
		@property
		def pure_weight(self):
			return 0.0001
		
		@property
		def depth(self):
			return self.__depth
		
		@property
		def name(self):
			return self.__name
		
		@property
		def activation(self):
			return self.__activation
		
		def show_graph(self, bgc = None, matched = False):
			if bgc is None:
				bgc = Pom.BuildGraphConf()
			conf = bgc.fork(None, {self.name:self}, self.depth)
			conf.parent_matched = matched
			Pom.BuildGraph.show(conf)
		
		@staticmethod
		def create(pom_io, xprofile, module = None):
			if not isinstance(pom_io, Pom.IO):
				pom_io = Pom.IO(pom_io)
			if not os.path.isfile(pom_io.file_path):
				return None
			name = Pom.Xml.get_id(xprofile)
			parent_properties = module.properties if module else None
			properties = Pom.Properties.create(xprofile, parent_properties)
			activation = Pom.ProfileActivation.parse(xprofile)
			profile = Pom.Profile(name, properties, activation)
			
			repositories = Pom.ArtifactRepositories.create(xprofile, False)
			plugin_repositories = Pom.ArtifactRepositories.create(xprofile, True)
			profile._set_repositories(repositories, plugin_repositories)
			
			modules = Pom.Modules.create(pom_io, xprofile, module)
			profile._set_modules(modules)
			
			profile.__depth = (module.depth if module else 0) + 1
			return profile
		
		def __str__(self):
			return self.name
		
		def __repr__(self):
			return "Pom.Profile(%s)" % str(self)
	
	class OS(object):
		def __init__(self, name, family, arch, version):
			self.__name = Pom.OS.unwrap_value(name, Pom.OS.get_valid_name)
			self.__family = Pom.OS.unwrap_value(family, Pom.OS.get_valid_family)
			if self.name is None and self.family == 'linux':
				self.__family = None
				self.__name = 'linux'
			self.__arch = Pom.OS.unwrap_value(arch, Pom.OS.get_valid_arch)
			self.__version = version
		
		@property
		def name(self):
			return self.__name
		
		@property
		def family(self):
			return self.__family
		
		@property
		def arch(self):
			return self.__arch
		
		@property
		def version(self):
			return self.__version
		
		@staticmethod
		def clean_value(value):
			if value is None:
				return None
			value = value.strip().lower()
			if len(value) == 0:
				return None
			return value
		
		@staticmethod
		def unwrap_value(value, f):
			value = Pom.OS.clean_value(value)
			if value is None:
				return None
			rev = value.startswith('!')
			if rev:
				value = value[1:]
			value = f(value)
			if rev:
				value = '!' + value
			return value
		
		@staticmethod
		def get_valid_family(family):
			family = Pom.OS.clean_value(family)
			if family is None:
				return None
			if family == 'darwin':
				family = 'macos'
			return family
		
		@staticmethod
		def get_valid_name(name):
			name = Pom.OS.clean_value(name)
			if name is None:
				return None
			if name in ['gnu/linux']:
				name = 'linux'
			return name
		
		@staticmethod
		def get_valid_arch(arch):
			arch = Pom.OS.clean_value(arch)
			if arch is None:
				return None
			if arch in ['i386', 'i486', 'i586', 'i686', 'x86']:
				arch = 'i386'
			elif arch in ['amd64', 'x86_64', 'x64']:
				arch = 'amd64'
			else:
				if arch not in ['ppc', 'ppc64', 'ia64', 'sparc', 'sun4u', 'arm', 'mips', 'alpha']: 
					raise Exception('Unknown architecture: ' + arch)
			return arch
		
		@staticmethod
		def get_system_arch():
			return Pom.OS.get_valid_arch(platform.machine())
		
		@staticmethod
		def get_system_family():
			return Pom.OS.get_valid_family(platform.system())
		
		@staticmethod
		def get_system_version():
			return platform.release()
		
		@classmethod
		def parse(cls, xnode):
			xos = Pom.Xml.get_node(xnode, 'os')
			if xos is None:
				return None
			name = Pom.Xml.get_child_node_value(xos, 'name', None)
			family = Pom.Xml.get_child_node_value(xos, 'family', None)
			arch = Pom.Xml.get_child_node_value(xos, 'arch', None)
			version = Pom.Xml.get_child_node_value(xos, 'version', None)
			if not name and not family and not arch and not version:
				return None
			return cls(name, family, arch, version)
		
		def __str__(self):
			props = []
			if self.family:
				props.append('family={0}'.format(self.family))
			if self.name:
				props.append('name={0}'.format(self.name))
			if self.family:
				props.append('arch={0}'.format(self.arch))
			if self.version:
				props.append('version={0}'.format(self.version))
			return ', '.join(props)
		
		def __eq__(self, other):
			if not isinstance(other, self.__class__):
				return False
			if self.family != other.family:
				return False
			elif self.name != other.name:
				return False
			elif self.arch != other.arch:
				return False
			elif self.version != other.version:
				return False
			return True
		
		def __ne__(self, other):
			return not self.__eq__(other)
		
		def __repr__(self):
			return "{0}({1})".format(self.__class__.__name__, str(self))
	
	class Env(object):
		@staticmethod
		def which(name, flags=os.X_OK):
			result = []
			exts = filter(None, os.environ.get('PATHEXT', '').split(os.pathsep))
			path = os.environ.get('PATH', None)
			if path is None:
				return []
			for p in os.environ.get('PATH', '').split(os.pathsep):
				p = os.path.join(p, name)
				if os.access(p, flags):
					result.append(p)
				for e in exts:
					pext = p + e
					if os.access(pext, flags):
						result.append(pext)
			return result
		
		@staticmethod
		def get_user_home():
			if 'HOME' in os.environ:
				home = os.environ['HOME']
			elif os.name == 'posix':
				home = os.path.expanduser("~")
			elif os.name == 'nt':
				if 'HOMEPATH' in os.environ and 'HOMEDRIVE' in os.environ:
					home = os.path.join(os.environ['HOMEDRIVE'], os.environ['HOMEPATH'])
			else:
				home = os.environ['HOMEPATH']
			if home.endswith(os.sep):
				home = home[:-len(os.sep)]
			return home
		
		@staticmethod
		def get_user_name():
			for name in ('LOGNAME', 'USER', 'LNAME', 'USERNAME'):
				user = os.environ.get(name)
				if user:
					return user
			import pwd
			return pwd.getpwuid(os.getuid())[0]
		
		@staticmethod
		def get_maven_home():
			if 'M2_HOME' in os.environ:
				return os.environ['M2_HOME']
			mvn = None
			if 'M2' in os.environ:
				mvn = os.path.join(os.environ['M2'], 'mvn')
			else:
				mvns = Pom.Env.which('mvn')
				if len(mvns) > 0:
					mvn = mvns[0]
			if os.path.isfile(mvn):
				m2_home = os.path.abspath(os.path.join(mvn, '..', '..'))
				m2_conf = os.path.join(m2_home, 'conf', 'settings.xml')
				if not os.path.isfile(m2_conf):
					m2_home = None
			return m2_home
	
	class ProfileActivation(object):
		def __init__(self, by_default, jdk, os, property_name, property_value):
			self.__by_default = by_default
			if jdk is not None:
				jdk = jdk.strip()
			self.__jdk = jdk
			self.__os = os
			self.__property_name = property_name or None
			if not property_name:
				property_value = None
			self.__property_value = property_value
		
		@property
		def by_default(self):
			return self.__by_default
		
		@property
		def jdk(self):
			return self.__jdk
		
		@property
		def os(self):
			return self.__os
		
		@property
		def property_name(self):
			return self.__property_name
		
		@property
		def property_value(self):
			return self.__property_value
		
		def match_properties(self, properties):
			if self.property_name is None:
				return True
			if self.property_name not in properties:
				return False
			if self.property_value is None:
				return True
			return properties[self.property_name] == self.property_value 
		
		def match_jdk(self, jdk_version):
			jdk = self.jdk
			if jdk is None or len(jdk) == 0:
				return True
			if jdk.startswith('[') or jdk.startswith(')'):
				try:
					jdk_range = Pom.VersionRange.create_from_version_spec(jdk)
					jdk_av = Pom.ArtifactVersion(jdk_version.replace('_', '-'))
					return jdk_range.contains_version(jdk_av)
				except VersionException as e:
					raise VersionException('Invalid JDK version: ' + e.message)
			rev = False
			if jdk.startswith('!'):
				rev = True
				jdk = jdk[1:]
			if jdk_version.startswith(jdk):
				return not rev
			else:
				return rev
		
		def match_os(self, os):
			if self.os is None:
				return True
			return self.os == os
		
		def __repr__(self):
			props = []
			if self.by_default:
				props.append('default')
			if self.property_name is not None:
				prop = 'property={0}'.format(self.property_name)
				if self.property_value is not None:
					prop += ':{0}'.format(self.property_value)
				props.append(prop)
				if self.jdk is not None:
					props.append('jdk={0}'.format(self.jdk))
			return "{0}({1})".format(self.__class__.__name__, ', '.join(props))
	
		@classmethod
		def parse(cls, xnode):
			xactivation = Pom.Xml.get_node(xnode, 'activation')
			if xactivation is None:
				return None
			by_default = Pom.Xml.get_child_node_value(xactivation, 'activateByDefault', 'false').lower() == 'true'
			jdk = Pom.Xml.get_child_node_value(xactivation, 'jdk', None)
			os = Pom.OS.parse(xactivation)
			xprop = Pom.Xml.get_node(xactivation, 'property')
			if xprop is not None:
				property_name = Pom.Xml.get_child_node_value(xprop, 'name', '').strip() or None
				property_value = Pom.Xml.get_child_node_value(xprop, 'value', '').strip() or None
			else:
				property_name = None
				property_value = None
			return cls(by_default, jdk, os, property_name, property_value)
	
	class BuildPath(object):
		def __init__(self, profiles = set(), properties = {}):
			self.profiles = set()
			self.properties = {}
			for p in profiles:
				self.profiles.add(p)
			for k, v in properties.items():
				if v is not None and len(v.strip()) == 0:
					v = None
				self.properties[k] = v
		
		def is_empty(self):
			return len(self.profiles) == 0 and len(self.properties) == 0
		
		def get_cmdline(self):
			cmdline = ''
			if len(self.profiles) > 0:
				cmdline = '-P' + ','.join(sorted(self.profiles))
			if len(self.properties) > 0:
				for k in sorted(self.properties):
					cmdline += ' -D'
					v = self.properties[k]
					if v is None:
						cmdline += k
					else:
						cmdline += k + '=' + v
			return cmdline.strip()
		
		def get_merged(self, other):
			b = self.clone()
			b.merge(other)
			return b
		
		def merge(self, other):
			self.profiles = self.profiles.union(other.profiles)
			for k, v in other.properties.items():
				if k in self.properties:
					if v is None or len(v) == 0:
						continue
					ov = self.properties[k]
					if ov is None or len(ov) == 0:
						self.properties[k] = v
					elif v == ov:
						continue
					else:
						raise Exception('Cannot merge. Incompatible property %s values - %s, %s' % (k, v, ov))
				else:
					self.properties[k] = v
		
		def is_profile_active(self, p):
			if p is None:
				return False
			active = False
			if p.name in self.profiles:
				active = True
			elif p.activation is not None:
				a = p.activation
				if a.by_default:
					active = True
				elif a.match_properties(self.properties):
					active = True
			return active
		
		def clone(self):
			clone = Pom.BuildPath()
			for profile in self.profiles:
				clone.profiles.add(profile)
			for k, v in self.properties.items():
				clone.properties[k] = v
			return clone
		
		def __repr__(self):
			if len(self.profiles) > 0 and len(self.properties) > 0:
				return "Pom.BuildPath(profiles=%r, properties=%r)" % (self.profiles, self.properties)
			else:
				if len(self.profiles) > 0:
					return "Pom.BuildPath(profiles=%r)" % (self.profiles)
				elif len(self.properties) > 0:
					return "Pom.BuildPath(properties=%r)" % (self.properties)
				else:
					return "Pom.BuildPath()"
		
		def __hash__(self):
			return hash(self.__repr__())
		
		def __eq__(self, other):
			return self.__repr__() == other.__repr__()
		
		def __ne__(self, other):
			return not self.__eq__(other)
	
	class BuildPathSet(set):
		def __init__(self):
			pass
	
	class BuildPathMap(object):
		def __init__(self):
			self.modules = {}
			self.profiles = {}
		
		@staticmethod
		def create(pom_module):
			bpm = Pom.BuildPathMap()
			bpm._process(Pom.BuildPath(), pom_module.modules, pom_module.profiles)
			return bpm
		
		def _get_module_key(self, module):
			if isinstance(module, Pom.Module):
				return module.artifact
			else:
				return self._find_module_key(str(module))
		
		def _find_module_key(self, module_name):
			found = []
			for artifact in self.modules:
				if artifact.match_name(module_name):
					found.append(artifact)
			l = len(found)
			if l > 1:
				raise Exception('multiple modules matched by "%s": %s' % (module_name, found))
			elif l == 1:
				return found[0]
			else:
				return None
		
		def _get_profile_key(self, profile):
			if isinstance(profile, Pom.Profile):
				return profile.name
			else:
				return self._find_profile_key(str(profile))
		
		def _find_profile_key(self, profile_key):
			if profile_key in self.profiles:
				return profile_key
			else:
				return None
		
		def _add_module_path(self, module, buildpath):
			k = self._get_module_key(module)
			if not k in self.modules:
				self.modules[k] = Pom.BuildPathSet()
			self.modules[k].add(buildpath)
		
		def _add_profile_path(self, profile, buildpath):
			k = self._get_profile_key(profile)
			if not k in self.profiles:
				self.profiles[k] = Pom.BuildPathSet()
			self.profiles[k].add(buildpath)
		
		def _get_module_buildpaths(self, search_module):
			k = self._get_module_key(search_module)
			if k is not None and k in self.modules:
				return self.modules[k]
			else:
				return None
		
		def _get_profile_buildpaths(self, search_profile):
			k = self._get_profile_key(search_profile)
			if k is not None and k in self.profiles:
				return self.profiles[k]
			else:
				return None
		
		def _get_filtered_buildpaths(self, buildpaths, excludes = set()):
			if len(excludes) == 0: return buildpaths
			bps = Pom.BuildPathSet()
			for bp in buildpaths:
				exclude = False
				for e in excludes:
					if e in bp.profiles:
						exclude = True
						break
					if e in bp.properties:
						exclude = True
						break
				if exclude: continue
				bps.add(bp)
			return bps
		
		def get_buildpaths(self, modules, profiles, excludes = set()):
			initial_buildpaths = []
			for module in modules:
				bps = self._get_module_buildpaths(module)
				if bps is None: continue
				bps = self._get_filtered_buildpaths(bps, excludes)
				if len(bps) == 0: continue
				initial_buildpaths.append(bps)
			for profile in profiles:
				bps = self._get_profile_buildpaths(profile)
				if bps is None: continue
				bps = self._get_filtered_buildpaths(bps, excludes)
				if len(bps) == 0: continue
				initial_buildpaths.append(bps)
			
			reduced_buildpaths = Pom.BuildPathSet()
			first = True
			for bps in initial_buildpaths:
				if first:
					reduced_buildpaths = bps
					first = False
				else:
					common = reduced_buildpaths.intersection(bps)
					if len(common) > 0:
						product1 = reduced_buildpaths.difference(common)
						product2 = bps.difference(common)
						reduced_buildpaths = common
					else:
						product1 = reduced_buildpaths
						product2 = bps
						reduced_buildpaths = Pom.BuildPathSet()
					for buildpath_combination in itertools.product(product1, product2):
						merged_buildpath = Pom.BuildPath()
						for bp in buildpath_combination:
							merged_buildpath.merge(bp)
						reduced_buildpaths.add(merged_buildpath)
			return reduced_buildpaths
		
		def _process(self, buildpath, modules, profiles):
			for module_name in sorted(modules):
				module = modules[module_name]
				if module is None: continue
				self._add_module_path(module, buildpath.clone())
				b = buildpath.clone()
				self._process(b, module.modules, module.profiles)
			
			for profile_name in sorted(profiles):
				profile = profiles[profile_name]
				if profile is None: continue
				activation = profile.activation
				by_name = True
				if activation is not None:
					if activation.by_default:
						by_name = False
						b = buildpath.clone()
						self._add_profile_path(profile, b.clone())
						self._process(b, profile.modules, [])
					elif activation.property_name is not None:
						b = buildpath.clone()
						b.properties[activation.property_name] = activation.property_value
						self._add_profile_path(profile, b.clone())
						self._process(b, profile.modules, [])
				if by_name:
					b = buildpath.clone()
					b.profiles.add(profile_name)
					self._add_profile_path(profile, b.clone())
					self._process(b, profile.modules, [])

pom = Pom()

class Maven(object):
	def __init__(self, cfg):
		if cfg is None or not isinstance(cfg, Config):
			raise TypeError('config not valid', cfg)
		self.pom_file = cfg.pom_file
		self.verbose = cfg.verbose
	
	def remove_plugin(self, plugin):
		plugin_parts = plugin.split(':')
		if len(plugin_parts) < 2 or len(plugin_parts) > 3:
			raise ValueError('incorrect plugin definition: "%s"' % plugin)
		group_id = plugin_parts[0].strip()
		artifact_id = plugin_parts[1].strip()
		version = plugin_parts[2].strip() if len(plugin_parts) > 2 else ''
		if len(artifact_id) == 0:
			raise ValueError('incorrect plugin definition: "%s"' % plugin)
		parse_group = len(group_id) > 0
		parse_version = len(version) > 0
		
		pomtree = etree.parse(self.pom_file)
		pomroot = pomtree.getroot()
		
		plugins = []
		for plugin_node in pomroot.iter("{*}plugin"):
			group_node = plugin_node.find('{*}groupId')
			if parse_group and (group_node is None or group_node.text != group_id):
				continue 
			artifact_node = plugin_node.find('{*}artifactId')
			if artifact_node is None or artifact_node.text != artifact_id:
				continue
			version_node = plugin_node.find('{*}version')
			if parse_version and (version_node is None or version_node.text != version):
				continue 
			plugins.append(plugin_node)
		if len(plugins) > 0:
			for plugin_node in plugins:
				plugin_node.getparent().remove(plugin_node)
			pomtree.write(self.pom_file, encoding='UTF-8', xml_declaration=True)
	
	def how_to_build(self, modules, profiles, excludes, show_weigth=False):
		pom = Pom.Module.create(self.pom_file)
		bpm = Pom.BuildPathMap.create(pom)
		bps = bpm.get_buildpaths(modules, profiles, excludes)
		
		sorted_bps = sorted(bps, key=lambda item: pom.get_weight(item))
		for bp in sorted_bps:
			if show_weigth:
				print "%.4f\t%s" % (pom.get_weight(bp), bp.get_cmdline())
			else:
				print "%s" % bp.get_cmdline()
	
	def show_dependencies(self, show_tree):
		pom = Pom.Module.create(self.pom_file)
		for v in sorted(pom.dependencies.values(), key=lambda d: (d.scope, d.artifact.get_module_id())):
			print v

class CmdLine(object):
	_type_dir = click.Path(exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True)
	_type_rofile = click.Path(exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True)
	_type_rwfile = click.Path(exists=False, file_okay=True, dir_okay=False, writable=True, resolve_path=True)
	
	def run(self):
		self.cli()
	
	@staticmethod
	def get_multi_option(value):
		vset = set()
		for v1 in value:
			for v2 in v1.split(','):
				v2 = v2.strip()
				if len(v2) == 0: continue
				vset.add(v2)
		return vset
	
	@staticmethod
	def get_key_value_option(value):
		initial = CmdLine.get_multi_option(value)
		kv = {}
		for rawkv in initial:
			parts = rawkv.split('=')
			l = len(parts)
			key = parts[0].strip()
			if len(key) == 0: continue
			value = parts[1].strip() if l>1 else ''
			if l == 1 or len(value) == 0:
				kv[key] = None
			else:
				kv[key] = value
		return kv
	
	@click.group()
	@click.option('--verbose', '-v', default=False, is_flag=True)
	@click.argument('pom', metavar='<pom>', type=_type_rofile)
	@click.pass_context
	def cli(ctx, verbose, pom):
		cfg = ctx.ensure_object(Config)
		cfg.verbose = verbose
		cfg.pom_file = pom
	
	@cli.command('remove-plugin', short_help='remove plugin')
	@click.argument('plugin', metavar='<plugin>')
	@click.pass_context
	def remove_plugin(ctx, plugin):
		"""Remove plugin from maven configuration
		
		<plugin>\t[groupId]:artifcatId[:version]
		 """
		cfg = ctx.ensure_object(Config)
		mvn = Maven(cfg)
		mvn.remove_plugin(plugin)
	
	@cli.command('show-graph', short_help='show graph')
	@click.pass_context
	@click.option('--mark', '-m', default=True, is_flag=True, help='mark build graph')
	@click.option('--filter', '-f', default=False, is_flag=True, help='filter build graph')
	@click.option('--profile', '-p', metavar='<profile>', multiple=True, help='profile (multiple)')
	@click.option('--property', '-k', metavar='<property>', multiple=True, help='property name[=value] (multiple)')
	@click.option('--show-weight', '-w', default=False, is_flag=True, help='show weight')
	@click.option('--show-implicit', '-i', default=False, is_flag=True, help='show implicit matches')
	def show_graph(ctx, profile, property, mark, filter, show_weight, show_implicit):
		cfg = ctx.ensure_object(Config)
		profiles = CmdLine.get_multi_option(profile)
		properties = CmdLine.get_key_value_option(property)
		match_path = Pom.BuildPath(profiles, properties)
		root = Pom.Module.create(cfg.pom_file)
		bgc = Pom.BuildGraphConf()
		bgc.match_path = match_path
		bgc.do_mark = mark
		bgc.do_filter = filter
		bgc.show_weight = show_weight
		bgc.show_implicit = show_implicit
		root.show_graph(bgc, True)
	
	@cli.command('show-modules', short_help='show modules')
	@click.pass_context
	@click.option('--mark', '-m', default=True, is_flag=True, help='mark build graph')
	@click.option('--filter', '-f', default=False, is_flag=True, help='filter build graph')
	@click.option('--profile', '-p', metavar='<profile>', multiple=True, help='profile (multiple)')
	@click.option('--property', '-k', metavar='<property>', multiple=True, help='property name[=value] (multiple)')
	@click.option('--show-weight', '-w', default=False, is_flag=True, help='show weight')
	@click.option('--show-implicit', '-i', default=False, is_flag=True, help='show implicit matches')
	@click.option('--hide-prefix', '-x', default=False, is_flag=True, help='hide module/profile prefix')
	@click.option('--tree/--list', '-t/-l', default=True, is_flag=True, help='show tree or list')
	def show_modules_list(ctx, profile, property, mark, filter, show_weight, show_implicit, hide_prefix, tree):
		cfg = ctx.ensure_object(Config)
		profiles = CmdLine.get_multi_option(profile)
		properties = CmdLine.get_key_value_option(property)
		match_path = Pom.BuildPath(profiles, properties)
		root = Pom.Module.create(cfg.pom_file)
		bgc = Pom.BuildGraphConf()
		bgc.match_path = match_path
		bgc.do_mark = mark
		bgc.do_filter = filter
		bgc.show_weight = show_weight
		bgc.show_implicit = show_implicit
		bgc.output_type = 'modules'
		bgc.show_prefix = not hide_prefix
		bgc.output_tree = tree
		root.show_graph(bgc, True)
	
	@cli.command('how-to-build', short_help='how to build')
	@click.option('--module', '-m', metavar='<module>', multiple=True, help='module to build (multiple)')
	@click.option('--profile', '-p', metavar='<profile>', multiple=True, help='profile to build (multiple)')
	@click.option('--exclude', '-e', metavar='<exclude>', multiple=True, help='exclude build profile/property (multiple)')
	@click.option('--show-weight', '-w', default=False, is_flag=True, help='show build path weight')
	@click.pass_context
	def how_to_build(ctx, module, profile, exclude, show_weight):
		cfg = ctx.ensure_object(Config)
		mvn = Maven(cfg)
		modules = CmdLine.get_multi_option(module)
		profiles = CmdLine.get_multi_option(profile)
		excludes = CmdLine.get_multi_option(exclude)
		mvn.how_to_build(modules, profiles, excludes, show_weight)
	
	@cli.command('show-dependencies', short_help='show dependencies')
	@click.pass_context
	@click.option('--tree/--list', '-t/-l', default=True, is_flag=True, help='show tree or list')
	def show_dependencies(ctx, tree):
		cfg = ctx.ensure_object(Config)
		mvn = Maven(cfg)
		mvn.show_dependencies(tree)

if __name__ == '__main__':
	cmd = CmdLine()
	cmd.run()
