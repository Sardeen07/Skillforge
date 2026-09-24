#!/bin/sh
# Runs hook.py with a working Python 3.10+, reading the hook payload from stdin.
# `python3` alone is not portable: on Windows it is often a Microsoft Store alias that
# prints "Python was not found" and exits 0. So probe for a real version string.
# With no usable Python, exit 0 silently: a missing brief must never block a prompt.
# The hook is an experiment and is off unless SKILLFORGE_HOOK selects a variant, so the
# default install costs nothing per prompt.
case "${SKILLFORGE_HOOK:-off}" in brief|catalog|fixed) ;; *) exit 0 ;; esac
script="$(dirname "$0")/../skills/skillforge/scripts/hook.py"
for py in python3 python py; do
  if [ "$("$py" -c 'import sys; print(sys.version_info >= (3, 10))' 2>/dev/null)" = "True" ]; then
    exec "$py" "$script"
  fi
done
exit 0
