# PDCA — Contract Tests & Codegen ガイド
**Last Updated:** 2025-08-24 (JST)  
**Owner:** Platform / PDCA

対象OpenAPI: `docs/apis/openapi/pdca-api.yaml`

---

## 0. 目的
- OpenAPI を **唯一の契約**として、サーバ/フロントの型やクライアントSDKを自動生成。  
- **契約テスト**で、API 実装が OpenAPI と乖離しないことを継続検証。  
- モックAPI とスモークテストで、GUI 開発をサーバ実装に先行させる。

---

## 1. ディレクトリ構成（提案）
```
/docs/apis/openapi/pdca-api.yaml
/scripts/codegen/            # コード生成スクリプト
  ├─ codegen-ts.sh          # TypeScript クライアント/型
  ├─ codegen-py.sh          # Python dataclass/SDK
  └─ preview-swagger.sh     # SwaggerUI ローカルプレビュー
/scripts/mock/
  └─ mock-prism.sh          # OpenAPI モックサーバ起動
/tests/contract/
  ├─ conftest.py
  ├─ test_openapi_schema.py
  ├─ test_contract_pdca.py
  └─ requirements.txt
/.github/workflows/contract-ci.yml
/ui/                         # （フロント）型/SDK 出力先
  /api/gen/ts/               # 生成物（コミットOK）
/pdca_api/                   # （サーバ）型/SDK 出力先
  /gen/py/
```

> ※ 生成物は**コミット推奨**（ビルド時の安定性/差分レビューのため）。

---

## 2. コード生成（TypeScript / Frontend）

### 2.1 依存（1回のみ）
```bash
# WSL/Ubuntu 想定
npm i -D @openapitools/openapi-generator-cli typescript zod zod-to-json-schema
npx openapi-generator-cli version-manager set 7.6.0
```

### 2.2 生成スクリプト `scripts/codegen/codegen-ts.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
SPEC="$ROOT/docs/apis/openapi/pdca-api.yaml"
OUT="$ROOT/ui/api/gen/ts"

mkdir -p "$OUT"
npx openapi-generator-cli generate \
  -i "$SPEC" \
  -g typescript-fetch \
  -o "$OUT" \
  --additional-properties=useSingleRequestParameter=true,withInterfaces=true,supportsES6=true,typescriptThreePlus=true,modelPropertyNaming=original

# 型安全補助: zod スタブ（任意）
cat > "$OUT/README.md" <<'MD'
# Generated TS SDK
- Generator: typescript-fetch
- Command: scripts/codegen/codegen-ts.sh
MD

echo "✅ TS SDK generated at $OUT"
```

### 2.3 実行
```bash
chmod +x scripts/codegen/codegen-ts.sh
scripts/codegen/codegen-ts.sh
```

> 利用例（フロント）:
```ts
import { Configuration, DefaultApi } from '@/api/gen/ts';

const api = new DefaultApi(new Configuration({ basePath: import.meta.env.VITE_API_BASE, accessToken: () => jwt }));
const res = await api.listStrategies({ page: 1, pageSize: 50 });
```

---

## 3. コード生成（Python / サーバ）

### 3.1 依存（1回のみ）
```bash
# pyproject で管理している場合は dev-deps に追加してOK
pip install openapi-python-client==0.21.6
```

### 3.2 生成スクリプト `scripts/codegen/codegen-py.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
SPEC="$ROOT/docs/apis/openapi/pdca-api.yaml"
OUT="$ROOT/pdca_api/gen/py"

mkdir -p "$OUT"
openapi-python-client generate --path "$SPEC" --config /dev/stdin <<'YAML'
project_name_override: noctria_pdca_sdk
package_name_override: noctria_pdca_sdk
class_overrides: {}
YAML

# 生成パッケージを所定フォルダに配置（toolはカレントへ出力する）
PKG_DIR="$(ls -d noctria_pdca_sdk* | head -n1 2>/dev/null || true)"
if [ -n "$PKG_DIR" ]; then
  rm -rf "$OUT" && mkdir -p "$OUT"
  mv "$PKG_DIR"/"$PKG_DIR" "$OUT"/noctria_pdca_sdk
  rm -rf "$PKG_DIR"
fi
echo "✅ Python SDK generated at $OUT/noctria_pdca_sdk"
```

### 3.3 実行
```bash
chmod +x scripts/codegen/codegen-py.sh
scripts/codegen/codegen-py.sh
```

> 利用例（サーバ）:
```python
from pdca_api.gen.py.noctria_pdca_sdk import Client
client = Client(base_url="http://localhost:8001", token="Bearer ...")
# 型付きリクエストを利用（例は擬似）
```

---

## 4. Swagger UI プレビュー & モックサーバ

### 4.1 Swagger UI（ローカル表示）
`scripts/codegen/preview-swagger.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
SPEC="$ROOT/docs/apis/openapi/pdca-api.yaml"
PORT="${1:-8042}"

docker run --rm -p "$PORT:8080" -e SWAGGER_JSON=/openapi.yaml \
  -v "$SPEC":/openapi.yaml swaggerapi/swagger-ui:v5.17.14
# http://localhost:8042
```

実行:
```bash
chmod +x scripts/codegen/preview-swagger.sh
scripts/codegen/preview-swagger.sh 8042
```

### 4.2 モック（Prism）
`scripts/mock/mock-prism.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
SPEC="$ROOT/docs/apis/openapi/pdca-api.yaml"
PORT="${1:-4010}"

docker run --rm -p "$PORT:4010" -v "$SPEC":/tmp/api.yaml stoplight/prism:4 \
  mock -h 0.0.0.0 /tmp/api.yaml
# http://localhost:4010
```

実行:
```bash
chmod +x scripts/mock/mock-prism.sh
scripts/mock/mock-prism.sh 4010
```

---

## 5. 契約テスト（Schemathesis + pytest）

### 5.1 依存
`/tests/contract/requirements.txt`
```
pytest==8.3.2
schemathesis==3.27.6
httpx==0.27.2
```

インストール:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r tests/contract/requirements.txt
```

### 5.2 conftest & ベースURL
`/tests/contract/conftest.py`
```python
import os, pytest
BASE = os.getenv("PDCA_BASE", "http://localhost:8001")

@pytest.fixture(scope="session")
def base_url():
    return BASE

@pytest.fixture(scope="session")
def bearer():
    return os.getenv("PDCA_JWT", "DUMMY")
```

### 5.3 スキーマ検証（単純）
`/tests/contract/test_openapi_schema.py`
```python
from pathlib import Path
import yaml

def test_openapi_loadable():
    p = Path("docs/apis/openapi/pdca-api.yaml")
    with p.open() as f:
        doc = yaml.safe_load(f)
    assert doc["openapi"].startswith("3.")
```

### 5.4 プロパティベース契約テスト
`/tests/contract/test_contract_pdca.py`
```python
import schemathesis as st
import os

schema = st.from_path("docs/apis/openapi/pdca-api.yaml")
BASE = os.getenv("PDCA_BASE", "http://localhost:8001")
JWT  = os.getenv("PDCA_JWT", "DUMMY")

@schema.parametrize()
def test_api_conforms(case):
    # 共通ヘッダ（必要に応じて分岐）
    case.headers.setdefault("Authorization", f"Bearer {JWT}")
    if case.path == "/pdca/recheck" and case.method == "POST":
        case.headers.setdefault("Idempotency-Key", "01JTESTULIDXYZ")
    if case.path == "/pdca/recheck_all" and case.method == "POST":
        case.headers.setdefault("Idempotency-Key", "01JTESTULIDABC")
    response = case.call(base_url=BASE)
    case.validate_response(response)
```

### 5.5 実行例
```bash
# サーバ or モックを起動してから
export PDCA_BASE=http://localhost:8001
export PDCA_JWT=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
pytest -q tests/contract
```

> 備考: Prism モックに対して流す場合は `PDCA_BASE=http://localhost:4010` を指定。

---

## 6. CI（GitHub Actions）
`.github/workflows/contract-ci.yml`
```yaml
name: PDCA Contract CI

on:
  pull_request:
    paths:
      - "docs/apis/openapi/**.yaml"
      - "scripts/**"
      - "tests/contract/**"
  push:
    branches: [ main, docs/** ]

jobs:
  contract:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Python setup
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install deps
        run: |
          python -m pip install -r tests/contract/requirements.txt

      - name: Start Prism mock
        run: |
          docker run -d --name prism -p 4010:4010 \
            -v $GITHUB_WORKSPACE/docs/apis/openapi/pdca-api.yaml:/tmp/api.yaml \
            stoplight/prism:4 mock -h 0.0.0.0 /tmp/api.yaml
          sleep 2

      - name: Run contract tests against mock
        env:
          PDCA_BASE: http://localhost:4010
          PDCA_JWT: DUMMY
        run: pytest -q tests/contract

      - name: TS SDK codegen (sanity)
        run: |
          npm i -D @openapitools/openapi-generator-cli
          npx openapi-generator-cli generate -i docs/apis/openapi/pdca-api.yaml -g typescript-fetch -o /tmp/sdk

      - name: Upload test reports (optional)
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: contract-reports
          path: ./.pytest_cache
```

---

## 7. Make タスク（任意）
`Makefile` 追記:
```make
.PHONY: codegen ts-sdk py-sdk mock swagger test-contract
codegen: ts-sdk py-sdk
ts-sdk:
	./scripts/codegen/codegen-ts.sh
py-sdk:
	./scripts/codegen/codegen-py.sh
mock:
	./scripts/mock/mock-prism.sh 4010
swagger:
	./scripts/codegen/preview-swagger.sh 8042
test-contract:
	PDCA_BASE?=http://localhost:4010 ; \
	PDCA_JWT?=DUMMY ; \
	pytest -q tests/contract
```

---

## 8. 運用ノート
- **OpenAPI を変更**したら：
  1) `make codegen`（TS/Py 再生成）  
  2) `make mock && make test-contract`（モックで契約テスト）  
  3) サーバ実装に反映 → 実サーバで契約テストを流す  
- **破壊的変更**は PR で「変更点サマリ（Breaking）」を必須化。  
- **Idempotency-Key** は `POST /pdca/recheck*` 系で**常に**ヘッダ設定。  
- **RateLimit** / `Retry-After` のふるまいはモックでは近似になる点に留意。

---

## 9. 変更履歴
- **2025-08-24**: 初版（TS/Pyコード生成、Swagger/Prism、Schemathesis契約テスト、CI）
