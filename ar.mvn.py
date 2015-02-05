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
				#print module_name, module
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
		def get_modules(xnode):
			return Pom.Xml.get_nodes(xnode, 'module', 'modules')
		
		@staticmethod
		def get_profiles(xnode):
			return Pom.Xml.get_nodes(xnode, 'profile', 'profiles')
		
		@staticmethod
		def get_nodes(xnode, children_name, parent_name=None):
			if parent_name is not None and len(parent_name) > 0:
				xparent = xnode.find("{*}" + parent_name)
			else:
				xparent = xnode
			if xparent is not None:
				return xparent.iterchildren("{*}" + children_name)
			else:
				return []
		
		@staticmethod
		def get_node(xnode, child_name):
			return xnode.find('{*}' + child_name)
		
		@staticmethod
		def get_node_value(xnode, default_value = None):
			value = xnode.text.strip() if xnode is not None else ''
			if len(value) == 0 and default_value is not None:
				groupid = default_value
			return value
		
		@staticmethod
		def get_child_node_value(xnode, child_name, default_value = None):
			xnode = Pom.Xml.get_node(xnode, child_name)
			return Pom.Xml.get_node_value(xnode, default_value)
	
	class IO():
		def __init__(self, pom_file):
			self.file_path = os.path.abspath(pom_file)
			self.dir_path = os.path.abspath(os.path.dirname(pom_file))
	
	class Artifact():
		def __init__(self, parent, groupId, artifactId, version, packaging):
			self.parent = parent
			self.groupId = groupId
			self.artifactId = artifactId
			self.version = version
			self.packaging = packaging
			self.moduleId = self.get_module_id()
		
		def match(self, name):
			module_id = self.get_module_id()
			if module_id == name:
				return True
			module_parts = module_id.split(':')
			l = len(module_parts)
			if l == 3:
				return name == module_parts[1]
			elif l == 2 or l == 1:
				return name == module_parts[0]
			else:
				return False
		
		def get_module_id(self):
			if len(self.groupId) > 0:
				moduleId = self.groupId + ':'
			elif self.parent is not None and len(self.parent.groupId) > 0:
				moduleId = self.parent.groupId + ':'
			else:
				moduleId = ''
			if len(self.artifactId) > 0:
				moduleId = moduleId + self.artifactId
			else:
				moduleId = moduleId + '__unnamed__'
			if len(self.version) > 0:
				moduleId = moduleId + ':' + self.version
			elif self.parent is not None and len(self.parent.version) > 0:
				moduleId = moduleId + ':' + self.parent.version
			return moduleId
		
		def __eq__(self, other):
			return self.get_module_id() == other.get_module_id()
		
		def __ne__(self, other):
			return not self.__eq__(other)
		
		def __hash__(self):
			return hash(self.get_module_id())
		
		def __str__(self):
			return self.get_module_id()
		
		def __repr__(self):
			return "Pom.Artifact(%s)" % str(self)
		
		@staticmethod
		def parse(xroot):
			xparent = Pom.Xml.get_node(xroot, 'parent')
			if xparent is not None:
				parent = Pom.Artifact.parse(xparent)
			else:
				parent = None
			groupId = Pom.Xml.get_group_id(xroot)
			artifactId = Pom.Xml.get_artifact_id(xroot)
			version = Pom.Xml.get_version(xroot)
			packaging = Pom.Xml.get_packaging(xroot)
			return Pom.Artifact(parent, groupId, artifactId, version, packaging)
	
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
	
	class Module(BuildWeight):
		def __init__(self, pom_io, artifact, modules, profiles, depth = 0):
			super(self.__class__, self).__init__()
			self.depth = depth
			self.io = pom_io
			self.artifact = artifact
			self.modules = modules
			self.profiles = profiles
		
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
		def create(pom_io, depth = 0):
			if not isinstance(pom_io, Pom.IO):
				pom_io = Pom.IO(pom_io)
			if not os.path.isfile(pom_io.file_path):
				return None
			xtree = etree.parse(pom_io.file_path)
			xroot = xtree.getroot()
			
			artifact = Pom.Artifact.parse(xroot)
			modules = Pom.Module.get_modules(pom_io, xroot, depth + 1)
			profiles = Pom.Profile.get_profiles(pom_io, xroot, depth + 1)
			
			return Pom.Module(pom_io, artifact, modules, profiles, depth)
		
		@staticmethod
		def get_modules(pom_io, xroot, depth = 0):
			modules = {}
			for xmodule in Pom.Xml.get_modules(xroot):
				module_name = xmodule.text.strip()
				if len(module_name) == 0: continue
				if module_name in modules: continue
				modules[module_name] = None
				if os.path.isdir(os.path.join(pom_io.dir_path, module_name)):
					pom_file = os.path.join(pom_io.dir_path, module_name, 'pom.xml')
					pom_module = Pom.Module.create(pom_file, depth)
					if pom_module is not None:
						modules[module_name] = pom_module
				else:
					pom_file = os.path.join(pom_io.dir_path, module_name)
					pom_module = Pom.Module.create(pom_file, depth)
					if pom_module is not None:
						modules[module_name] = pom_module
			return modules
		
		def __str__(self):
			return str(self.artifact)
		
		def __repr__(self):
			return "Pom.Module(%s)" % str(self)
	
	class Profile(BuildWeight):
		def __init__(self, pom_io, name, modules, activation, depth = 0):
			super(self.__class__, self).__init__()
			self.depth = depth
			self.io = pom_io
			self.name = name
			self.modules = modules
			self.activation = activation
		
		def show_graph(self, bgc = None, matched = False):
			if bgc is None:
				bgc = Pom.BuildGraphConf()
			conf = bgc.fork(None, {self.name:self}, self.depth)
			conf.parent_matched = matched
			Pom.BuildGraph.show(conf)
		
		@staticmethod
		def create(pom_io, xprofile, depth = 0):
			if not isinstance(pom_io, Pom.IO):
				pom_io = Pom.IO(pom_io)
			if not os.path.isfile(pom_io.file_path):
				return None
			name = Pom.Xml.get_id(xprofile)
			modules = Pom.Module.get_modules(pom_io, xprofile, depth + 1)
			activation = Pom.Activation.parse(xprofile)
			
			return Pom.Profile(pom_io, name, modules, activation, depth)
		
		@staticmethod
		def get_profiles(pom_io, xroot, depth = 0):
			profiles = {}
			for xprofile in Pom.Xml.get_profiles(xroot):
				profile_name = Pom.Xml.get_id(xprofile)
				if len(profile_name) == 0: continue
				if profile_name in profiles: continue
				profile = Pom.Profile.create(pom_io, xprofile, depth)
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
				if artifact.match(module_name):
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

if __name__ == '__main__':
	cmd = CmdLine()
	cmd.run()
