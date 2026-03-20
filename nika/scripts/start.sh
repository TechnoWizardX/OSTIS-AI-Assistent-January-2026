#!/usr/bin/env bash
set -eo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT_PATH="$(cd "$SCRIPT_PATH/.." && pwd)"

NIKA_PATH="$PROJECT_ROOT_PATH"/install/nika
SC_MACHINE_PATH="$PROJECT_ROOT_PATH"/install/sc-machine
FIXED_SEARCH_STRATEGY_TEMPLATE_PROCESSING_LIB="$PROJECT_ROOT_PATH"/install/fixed-search-strategy-template-processing-lib

LD_LIBRARY_PATH="$LD_LIBRARY_PATH/lib:$SC_MACHINE_PATH/lib:$FIXED_SEARCH_STRATEGY_TEMPLATE_PROCESSING_LIB/lib:$LD_LIBRARY_PATH"

case "$1" in
  build_kb)
    "$PROJECT_ROOT_PATH"/install/sc-machine/bin/sc-builder -i repo-patch.path -o kb.bin --clear
    "$PROJECT_ROOT_PATH"/install/sc-machine/bin/sc-builder -i repo.path -o kb.bin
    ;;
  machine)
    LD_LIBRARY_PATH="$LD_LIBRARY_PATH" \
      $SC_MACHINE_PATH/bin/sc-machine -s kb.bin \
      -e "$SC_MACHINE_PATH/lib/extensions;$NIKA_PATH/lib/extensions" -c nika.ini
    ;;
  web)
    cd $PROJECT_ROOT_PATH/sc-web || exit 1
    source .venv/bin/activate
    python3 server/app.py
    ;;
  interface)
    cd $PROJECT_ROOT_PATH/interface || exit 1
    npm run start
    ;;
  py_server)
    cd $PROJECT_ROOT_PATH/problem-solver/py || exit 1
    source .venv/bin/activate
    python3 server.py
    ;;
  *)
    echo "Usage: $0 {build_kb|machine|web|interface|py_server}"
    exit 1
    ;;
esac
