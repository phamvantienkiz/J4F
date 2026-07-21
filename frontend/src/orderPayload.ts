type OrderPayloadItem = {
  sku?: string;
  quantity?: number;
  print_sides?: "front" | "both" | "back";
  carrier?: string[] | string;
};

type BuildOrderStartMessageOptions = {
  country: string;
  carrier?: string;
  printSides?: "front" | "both" | "back";
  referenceOrderId?: string;
};

function itemCarrier(item: OrderPayloadItem) {
  if (Array.isArray(item.carrier)) return item.carrier[0] || "";
  return item.carrier || "";
}

export function buildOrderStartMessage(item: OrderPayloadItem, options: BuildOrderStartMessageOptions) {
  const lines: string[] = [];
  const sku = item.sku?.trim();
  if (sku) lines.push(`catalog_sku: ${sku}`);
  lines.push(`quantity: ${item.quantity || 1}`);

  const country = options.country.trim().toUpperCase();
  if (country) lines.push(`shipping_country: ${country}`);

  const carrier = options.carrier?.trim() || itemCarrier(item).trim();
  if (carrier) lines.push(`shipping_carrier: ${carrier}`);

  const printSides = options.printSides || item.print_sides;
  if (printSides) lines.push(`print_sides: ${printSides}`);

  const referenceOrderId = options.referenceOrderId?.trim();
  if (referenceOrderId) lines.push(`reference_order_id: ${referenceOrderId}`);

  return lines.join("\n");
}
