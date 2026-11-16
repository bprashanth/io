#!/bin/sh
# Claude Code's status line for Idli's two terminals (lib/rolelabels.py): a coloured block, then plain words.
# Analyst: teal. Builder: amber. Claude Code passes session JSON on stdin; it isn't needed here.
[ -t 0 ] || cat >/dev/null 2>&1
case "$1" in
  analyst) printf '\033[1;97;48;5;30m ANALYST \033[0m \033[38;5;37m%s\033[0m  private values are codes' "$2" ;;
  builder) printf '\033[1;30;48;5;214m BUILDER \033[0m \033[38;5;214m%s\033[0m  changes this team, never your data' "$2" ;;
  *) printf '%s' "$2" ;;
esac
