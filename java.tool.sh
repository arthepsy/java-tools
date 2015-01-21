#!/bin/sh
_cdir=$(cd -- "$(dirname "$0")" && pwd)

_bin="${_cdir}/bin"
_cpa="${_cdir}/lib/bcel-5.2.jar"

_pkg="eu.arthepsy.utils"
_cls="JavaTool"
_ccf="${_bin}/$(echo "${_pkg}" | tr '.' '/')/${_cls}.class"

mkdir -p "${_bin}"
if [ ! -f "${_ccf}" ]; then
	javac -d "${_bin}" -cp "${_cdir}:${_cpa}" ${_cdir}/${_cls}.java
fi
java -cp "${_bin}:${_cpa}" "${_pkg}.${_cls}" $*


