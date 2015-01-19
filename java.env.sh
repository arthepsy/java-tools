#!/bin/sh

_env_set_jdk() {
	if [ X"$1" = X"" ]; then
		echo "specify jdk directory."
		return 1
	fi
	local _jdk="$1"
	export JAVA_HOME="${_jdk}"
	export JRE_HOME="${_jdk}/jre"
	export PATH="${_jdk}/bin:$PATH"
	export JAVA_OPTS="$2"
}

_env_set_mvn() {
	if [ X"$1" = X"" ]; then
		echo "specify mvn directory." 
		return 1
	fi
	local _mvn="$1"
	export M2_HOME="${_mvn}"
	export M2="${M2_HOME}/bin"
	export PATH=$M2:$PATH
	export MAVEN_OPTS="$2"
}

case "$1" in
	jdk) _env_set_jdk "$2" "$3" ;;
	mvn) _env_set_mvn "$2" "$3" ;;
	*) 
		echo "usage: $0 [jdk|mvn] <directory> [options]"
		return 1
		;;
esac
