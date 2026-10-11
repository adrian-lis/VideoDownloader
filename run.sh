#!/usr/bin/env bash

if [ ! -x ".venv/bin/python" ]; then
  echo "The application is not installed yet."
  echo
  echo "Run:"
  echo "  ./install.sh"
  echo
  exit 1
fi

exec ".venv/bin/python" downloader.py