#!/bin/sh
_cdir=$(cd -- "$(dirname "$0")" && pwd)
${_cdir}/java.tool.sh getClassName $*
