import assert from "node:assert/strict";
import fs from "node:fs";
import ts from "typescript";

const source = fs.readFileSync(new URL("./orderPayload.ts", import.meta.url), "utf8");
const { outputText } = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
  },
});
const module = { exports: {} };
new Function("exports", "module", outputText)(module.exports, module);

const { buildOrderStartMessage } = module.exports;

const message = buildOrderStartMessage(
  {
    sku: "VNPAWIC1S-Silver-OneSize",
    quantity: 2,
    print_sides: "both",
    carrier: ["LaPoste"],
  },
  {
    country: "CH",
    carrier: "LaPoste",
    referenceOrderId: "REF-VNPAWIC1S-Silver-OneSize",
  }
);

assert.equal(
  message,
  [
    "catalog_sku: VNPAWIC1S-Silver-OneSize",
    "quantity: 2",
    "shipping_country: CH",
    "shipping_carrier: LaPoste",
    "print_sides: both",
    "reference_order_id: REF-VNPAWIC1S-Silver-OneSize",
  ].join("\n")
);

assert.equal(
  buildOrderStartMessage(
    { sku: "ABC-123", carrier: "USPS" },
    { country: "us", referenceOrderId: "REF-ABC-123" }
  ),
  [
    "catalog_sku: ABC-123",
    "quantity: 1",
    "shipping_country: US",
    "shipping_carrier: USPS",
    "reference_order_id: REF-ABC-123",
  ].join("\n")
);
