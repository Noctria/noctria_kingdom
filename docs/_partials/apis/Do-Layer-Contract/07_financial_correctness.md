<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/_partials/apis/Do-Layer-Contract/07_financial_correctness.md title="数値精度・丸め（Financial Correctness）" -->
### 数値精度・丸め（Financial Correctness）

<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/_partials/apis/Do-Layer-Contract/07_financial_correctness.md title="数値精度・丸め（Financial Correctness）" -->
### 数値精度・丸め（Financial Correctness）

<!-- AUTODOC:BEGIN mode=file_content path_globs=docs/_partials/apis/Do-Layer-Contract/07_financial_correctness.md title="数値精度・丸め（Financial Correctness）" -->
### 数値精度・丸め（Financial Correctness）

- **数量**：`qty_step` に **floor**（例：0.5004 → 0.500）  
- **価格**：`price_tick` に **side 別**丸め  
  - `BUY` → **floor**（過大価格を避ける）  
  - `SELL` → **ceil**（過小価格を避ける）  
- **手数料**：非負、最大 1e-6 単位、表記は `number`（JSON）  
- **スリッページ**：`slippage_pct` は **0..100**（%）。内部は小数点 **2 桁**まで保持。

> シンボルごとの `qty_step/price_tick` は `constraints` 指定が**最優先**、なければアダプタが注入。

---
<!-- AUTODOC:END -->
