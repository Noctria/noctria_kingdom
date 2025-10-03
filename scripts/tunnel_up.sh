#!/usr/bin/env bash
set -e
ssh -N -f -L 127.0.0.1:8009:127.0.0.1:8001 -p 20122 user@localhost -i ~/.ssh/mykey.txt
curl -s http://127.0.0.1:8009/v1/models | jq . || exit 1
echo "OK: bridge via 8009"
