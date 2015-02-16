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

from inspect import getmembers
from pprint import pprint

signal.signal(signal.SIGPIPE, signal.SIG_DFL)

class Config(object):
	def __init__(self, verbose=False):
		self.verbose = verbose
		self.pom_file = None

class Pom():
	def __init__(self):
		self.module_cache = {}
	
	class BuildGraphConf():
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
	
	class BuildGraph():
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
				if activation.prop_name is not None:
					if activation.prop_value is None:
						subtext.append('%s' % activation.prop_name)
					else:
						subtext.append('%s=%s' % (activation.prop_name, activation.prop_value))
				if len(subtext) > 0:
					text += ' (' + ','.join(subtext) + ')'
			if conf.show_weight:
				text += Pom.BuildGraph.get_weight_text(conf, profile, matched)
			print text
		
		
		@staticmethod
		def _show_modules(conf, parent = None):
			modules = {}
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
	
	class Xml():
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
		def get_nodes(xnode, children_name=None, parent_name=None):
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
	
	class IO():
		def __init__(self, pom_file):
			self.file_path = os.path.abspath(pom_file)
			self.dir_path = os.path.abspath(os.path.dirname(pom_file))
	
	class Properties(dict):
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
		
		def expand_item(self, key=None, value=None):
			self._expand_cache = {}
			value = self._expand_item(key, value)
			self._expand_cache = {}
			return value
		
		def _expand_item(self, key=None, value=None):
			if key is None and value is None: 
				return '' 
			stack = []
			stack.append(key)
			irreplaceable = set()
			get_value = lambda k: self._expand_cache.get(k, self.get(k, None))
			while True:
				item_key = stack.pop()
				item_value = value if item_key is None else get_value(item_key)
				if item_value is not None:
					if self.expand_required(item_value):
						replace_keys = self._get_item_keys(item_value)
						for replace_key in list(replace_keys):
							if replace_key in stack:
								replace_keys.remove(replace_key)
								irreplaceable.add(replace_key)
								continue
							replace_value = get_value(replace_key)
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
		
		#def expand_self(self):
		#	self._expand_cache = {}
		#	self._expand_self()
		#	self._expand_cache = {}
		
		def _expand_self(self):
			if not self.expand_required():
				return
			for k, v in self.items():
				if v is None: 
					self[k] = ''
					continue
				if self.expand_required(v):
					self[k] = self._expand_item(k) 
		
		def expand_with(self, other_properties):
			self._expand_cache = {}
			self._expand_with(other_properties)
			self._expand_cache = {}
		
		def _expand_with(self, other_properties):
			if not hasattr(self, 'external'):
				self.external = set()
			updated = False
			for k, v in other_properties.items():
				if not k in self:
					updated = True
					self[k] = v
					self.external.add(k)
			if updated:
				self._expand_self()
		
		def _add_build_properties(self, pom_io, xroot):
			if pom_io is None:
				return
			self._expand_cache = {}
			if not hasattr(self, 'internal'):
				self.internal = set()
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
			if not hasattr(self, 'internal'):
				self.internal = set()
			# SuperPOM (artifact)
			parent_tag = Pom.Xml.get_clean_tag(xroot)
			if parent_tag == 'project':
				artifact = Pom.Artifact.parse(xroot, Pom.ArtifactOrigin.PROJECT)
				if artifact is not None:
					self['project.groupId'] = artifact.get_groupId()
					self['project.artifactId'] = artifact.artifactId
					self['project.version'] = artifact.get_version()
					self.internal.add('project.groupId')
					self.internal.add('project.artifactId')
					self.internal.add('project.version')
				self['project.finalName'] = self._expand_item('${project.artifactId}-${project.version}')
				self.internal.add('project.finalName')
			self._expand_cache = {}
		
		def _add_session_properties(self, pom_io, parent_properties):
			self._expand_cache = {}
			key = 'session.executionRootDirectory'
			if key in parent_properties:
				self['session.executionRootDirectory'] = parent_properties[key]
			else:
				self['session.executionRootDirectory'] = pom_io.dir_path
			self.internal.add('session.executionRootDirectory')
			self._expand_cache = {}
		
		def get_list(self, internal=False, external=False):
			properties = {}
			for k, v in self.items():
				if not k in self.external and not k in self.internal:
					properties[k] = v
			return properties
		
		@classmethod
		def create(cls, xroot, pom_io=None, parent_properties=None):
			if parent_properties is None:
				parent_properties = Pom.Properties()
			properties = cls()
			properties.internal = set()
			properties.external = set()
			properties._add_build_properties(pom_io, xroot)
			properties._add_project_properties(xroot)
			properties._add_session_properties(pom_io, parent_properties)
			xproperties = Pom.Xml.get_properties(xroot)
			for xproperty in xproperties:
				if xproperty.tag is etree.Comment:
					continue
				key = Pom.Xml.get_clean_tag(xproperty)
				value = Pom.Xml.get_node_value(xproperty, '') 
				properties[key] = value
			properties._expand_cache = {}
			properties._expand_self()
			properties._expand_with(parent_properties)
			properties._expand_cache = {}
			return properties
	
	
	class ArtifactOrigin():
		UNKNOWN = 0
		PROJECT = 1
		DEPENDENCY = 2
		
		@staticmethod
		def ensure(value):
			if 0 < value > 2:
				return Pom.ArtifactOrigin.UNKNOWN
			else:
				return value
	
	class ArtifactVersion():
		def __init__(self, version):
			self.major = None
			self.minor = None
			self.incremental = None
			self.build_number = None
			self.qualifier = None
			self._parse(version)
		
		def get_major(self):
			return self.major or 0
		
		def get_minor(self):
			return self.minor or 0
		
		def get_incremental(self):
			return self.incremental or 0
		
		def get_build_number(self):
			return self.build_number or 0
		
		def get_qualifier(self):
			return self.qualifier
		
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
						self.build_number = self._get_int(p2) 
					else:
						self.qualifier = p2
				except ValueError:
					self.qualifier = p2
			if p1.find('.') < 0 and not p1.startswith('0'):
				try:
					self.major = self._get_int(p1)
				except ValueError:
					self.qualifier = version
					self.build_number = None
			else:
				fallback =  p1.find('..') >= 0 or p1.startswith('.') or p1.endswith('.')
				if not fallback:
					tokens = p1.split('.')
					try:
						self.major = self._get_token_int(tokens)
						if tokens:
							self.minor = self._get_token_int(tokens)
						if tokens:
							self.incremental = self._get_token_int(tokens)
						if tokens:
							self.qualifier = tokens.pop(0)
							fallback = self.qualifier.isdigit()
					except ValueError:
						fallback = True
				if fallback:
					self.qualifier = version
					self.major = None
					self.minor = None
					self.incremental = None
					self.build_number = None
		
		def __str__(self):
			buf = ''
			if self.major:
				buf += str(self.major)
			if self.minor:
				buf += '.' + str(self.minor)
			if self.incremental:
				buf += '.' + str(self.incremental)
			if self.build_number:
				buf += '-' + str(self.build_number)
			elif self.qualifier:
				if len(buf) > 0:
					buf += '-'
				buf += self.qualifier
			return buf
	
	class Artifact():
		def __init__(self, origin, parent, groupId, artifactId, packaging, classifier, version):
			self.origin = Pom.ArtifactOrigin.ensure(origin)
			self.parent = parent
			self.groupId = groupId
			self.artifactId = artifactId
			self.packaging = packaging
			self.classifier = classifier
			self.version = version
			self.moduleId = self.get_module_id()
		
		def get_groupId(self):
			return self.groupId if len(self.groupId) > 0 else self.parent.groupId
		
		def get_version(self):
			return self.version if len(self.version) > 0 else self.parent.version
		
		@staticmethod
		def get_parts(module_name):
			p = module_name.split(':')
			l = len(p)
			clean = lambda v: None if v == '*' else v.strip()
			if l == 1:
				return {'artifactId': clean([0])}
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
			if groupId is not None and self.get_groupId() != groupId: return False
			if artifactId is not None and self.artifactId != artifactId: return False
			if packaging is not None and self.packaging != packaging: return False
			if classifier is not None and self.classifier != classifier: return False
			if version is not None and self.get_version() != version: return False
			return True
		
		def match_name(self, name):
			parts = Pom.Artifact.get_parts(name)
			return self.match(parts.get('groupId'),
			                  parts.get('artifactId'),
			                  parts.get('packaging'),
			                  parts.get('classifier'),
			                  parts.get('version'))
		
		def get_module_id(self, full=False):
			moduleId = self.get_groupId() + ':' + self.artifactId + ':'
			if full:
				if len(self.classifier) > 0:
					moduleId += self.packaging + ':' + self.classifier + ':'
				elif self.packaging != 'jar':
					moduleId += self.packaging + ':'
			moduleId += self.get_version()
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
			
			properties = Pom.Inheritance.get_properties(module)
			managed_dependencies = Pom.Inheritance.get_managed_dependencies(module)
			
			parent = None
			parent_tag = Pom.Xml.get_clean_tag(xroot)
			if parent_tag == 'project' or origin == Pom.ArtifactOrigin.PROJECT:
				xparent = Pom.Xml.get_node(xroot, 'parent')
				if xparent is not None:
					parent = Pom.Artifact.parse(xparent, origin)
			expand = lambda v: properties.expand_item(value=v) if properties.expand_required(v) else v
			
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
			self.managed = set()
			self._managed = {}
		
		def get_managed(self):
			if self._managed is None:
				self._managed = {k: v for k, v in self.items() if k in self.managed}
			return self._managed
		
		def add(self, dependency):
			if dependency is None or not isinstance(dependency, Pom.Dependency):
				return
			self[dependency.artifact] = dependency
			
		def add_managed(self, dependency):
			self.add(dependency)
			self.managed.add(dependency.artifact)
			self._managed = None
		
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
	
	class Dependency:
		def __init__(self, artifact, deptype, scope, system_path, optional):
			self.artifact = artifact
			self.deptype = deptype
			self.scope = scope
			self.system_path = system_path
			self.optional = optional
		
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
			managed_dependencies = Pom.Inheritance.get_managed_dependencies(module)
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
	
	class LocalRepository(object):
		def __init__(self, repository_path = None):
			pass
		
		def contains(artifact):
			pass
	
	class BuildWeight(object):
		def __init__(self):
			self._wcache = {}
		
		def get_self_weight(self):
			if isinstance(self, Pom.Profile):
				return 0.0001
			elif isinstance(self, Pom.Module):
				return 1.0000
			else:
				return 0.0000
		
		def get_weight(self, bp = None, artifacts = None, level = 0):
			if bp not in self._wcache:
				self._wcache[bp] = self._get_weight(bp)
			return self._wcache[bp]
		
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
			weight = self.get_self_weight() + subweight
			try:
				a = self.artifact
				if a in artifacts:
					weight = 0
				else:
					artifacts.add(a)
			except (AttributeError, TypeError):
				pass
			return weight
	
	class Inheritance(object):
		@staticmethod
		def get_properties(module):
			properties = Pom.Properties()
			if module is None or not isinstance(module, Pom.Module):
				return properties
			stack = []
			parent = module.parent
			while parent is not None:
				stack.append(parent.properties)
				parent = parent.parent
			while stack:
				properties.update(stack.pop())
			if hasattr(module, 'properties'):
				properties.update(module.properties)
			return properties
		
		@staticmethod
		def get_managed_dependencies(module):
			dependencies = Pom.Dependencies()
			if not isinstance(module, Pom.Module):
				return dependencies
			stack = []
			parent = module.parent
			while parent is not None:
				stack.append(parent.dependencies.get_managed())
				parent = parent.parent
			while stack:
				dependencies.update(stack.pop())
			if hasattr(module, 'dependencies'):
				dependencies.update(module.dependencies.get_managed())
			return dependencies
	
	class Module(BuildWeight):
		def __init__(self, pom_io, artifact, depth = 0):
			super(self.__class__, self).__init__()
			self.depth = depth
			self.io = pom_io
			self.artifact = artifact
			self.parent = None
			self.properties = Pom.Properties()
			self.dependencies = Pom.Dependencies()
			self.modules = {}
			self.profiles = {}
		
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
		def create(pom_io, parent = None, depth = 0):
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
			module = Pom.Module(pom_io, artifact, depth)
			pom.module_cache[pom_io.file_path] = module
			
			if parent is not None:
				module.parent = parent
			else:
				if artifact.parent is not None:
					module.parent = Pom.Module._parse_parent(xroot, pom_io, artifact)
				else:
					module.parent = None
			
			parent_properties = module.parent.properties if module.parent else None
			module.properties = Pom.Properties.create(xroot, pom_io, parent_properties)
			
			Pom.Dependencies.populate(module, xroot)
			
			module.modules = Pom.Module.get_modules(pom_io, xroot, module, depth + 1)
			module.profiles = Pom.Profile.get_profiles(pom_io, xroot, module, depth + 1)
			return module
		
		@staticmethod
		def get_modules(pom_io, xroot, parent = None, depth = 0):
			modules = {}
			for xmodule in Pom.Xml.get_modules(xroot):
				module_name = xmodule.text.strip()
				if len(module_name) == 0: continue
				if module_name in modules: continue
				#modules[module_name] = None
				if os.path.isdir(os.path.join(pom_io.dir_path, module_name)):
					pom_file = os.path.join(pom_io.dir_path, module_name, 'pom.xml')
					pom_module = Pom.Module.create(pom_file, parent, depth)
					if pom_module is not None:
						modules[module_name] = pom_module
				else:
					pom_file = os.path.join(pom_io.dir_path, module_name)
					pom_module = Pom.Module.create(pom_file, parent, depth)
					if pom_module is not None:
						modules[module_name] = pom_module
			return modules
		
		def __str__(self):
			return str(self.artifact)
		
		def __repr__(self):
			return "Pom.Module(%s)" % str(self)
	
	class Profile(BuildWeight):
		def __init__(self, pom_io, name, properties, modules, activation, depth = 0):
			super(self.__class__, self).__init__()
			self.depth = depth
			self.io = pom_io
			self.name = name
			self.properties = properties
			self.modules = modules
			self.activation = activation
		
		def show_graph(self, bgc = None, matched = False):
			if bgc is None:
				bgc = Pom.BuildGraphConf()
			conf = bgc.fork(None, {self.name:self}, self.depth)
			conf.parent_matched = matched
			Pom.BuildGraph.show(conf)
		
		@staticmethod
		def create(pom_io, xprofile, module = None, depth = 0):
			if not isinstance(pom_io, Pom.IO):
				pom_io = Pom.IO(pom_io)
			if not os.path.isfile(pom_io.file_path):
				return None
			name = Pom.Xml.get_id(xprofile)
			parent_properties = module.properties if module else None
			properties = Pom.Properties.create(xprofile, None, parent_properties)
			modules = Pom.Module.get_modules(pom_io, xprofile, module, depth + 1)
			activation = Pom.Activation.parse(xprofile)
			
			return Pom.Profile(pom_io, name, properties, modules, activation, depth)
		
		@staticmethod
		def get_profiles(pom_io, xroot, module = None, depth = 0):
			profiles = {}
			for xprofile in Pom.Xml.get_profiles(xroot):
				profile_name = Pom.Xml.get_id(xprofile)
				if len(profile_name) == 0: continue
				if profile_name in profiles: continue
				profile = Pom.Profile.create(pom_io, xprofile, module, depth)
				if profile is None: continue
				profiles[profile_name] = profile 
			return profiles
		
		def __str__(self):
			return self.name
		
		def __repr__(self):
			return "Pom.Profile(%s)" % str(self)
	
	class Activation():
		def __init__(self, by_default, prop_name, prop_value):
			self.by_default = by_default
			self.prop_name = prop_name
			self.prop_value = prop_value
		
		def __repr__(self):
			return "%s(default=%s, property=%s:%s)" % (self.__class__, self.by_default, self.prop_name, self.prop_value)
	
		@staticmethod
		def parse(xnode):
			xactivation = xnode.find('{*}activation')
			if xactivation is None:
				return None
			act_by_default = False
			act_prop_name = None
			act_prop_value = None
			
			xbydef = xactivation.find('{*}activateByDefault')
			if xbydef is not None:
				if xbydef.text.strip().lower() == 'true':
					act_by_default = True
			xprop = xactivation.find('{*}property')
			if xprop is not None:
				xprop_name = xprop.find('{*}name')
				if xprop_name is not None:
					prop_name = xprop_name.text.strip()
					if len(prop_name) > 0:
						act_prop_name = prop_name
				xprop_value = xprop.find('{*}value')
				if xprop_value is not None:
					prop_value = xprop_value.text.strip()
					if len(prop_value) > 0:
						act_prop_value = prop_value
			
			return Pom.Activation(act_by_default, act_prop_name, act_prop_value)
	
	class BuildPath():
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
				elif a.prop_name is not None and a.prop_name in self.properties:
					if a.prop_value is None:
						active = True
					else:
						active = self.properties[a.prop_name] == a.prop_value
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
	
	class BuildPathMap():
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
					elif activation.prop_name is not None:
						b = buildpath.clone()
						b.properties[activation.prop_name] = activation.prop_value
						self._add_profile_path(profile, b.clone())
						self._process(b, profile.modules, [])
				if by_name:
					b = buildpath.clone()
					b.profiles.add(profile_name)
					self._add_profile_path(profile, b.clone())
					self._process(b, profile.modules, [])
pom = Pom()

class Maven():
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

class CmdLine():
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
