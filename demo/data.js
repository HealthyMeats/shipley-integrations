/* Demonstration data. FABRICATED.
 *
 * Product names and SKUs are real and already public in the catalog file.
 * EVERY PRICE HERE IS INVENTED for the demo and bears no relationship to what Shipley Farms
 * charges anyone. They are deliberately round numbers so nobody mistakes them for a quote, and
 * they are not derived from retail prices, so no discount structure can be inferred from them.
 *
 * There is no account, no key, and no server. Nothing here talks to Shipley Farms.
 */
window.DEMO = {
  account: {
    name: "Demo Kitchen Co.",
    id: "PARTNER-DEMO-0001",
    contact: "chef@demo-kitchen.example",
    terms: "Illustrative terms, set per account by a person",
    key: "sk_demo_0000000000000000"
  },
  products: [
    { sku: "SS1231", name: "Signature Huston Ribeye",        cat: "Dry-Aged Steaks", price: 42.00, uom: "lb",   catch: true,  pack: "Case of 8",  lead: 3, stock: "in stock" },
    { sku: "SS9B33", name: "Signature Filet Mignon",         cat: "Dry-Aged Steaks", price: 55.00, uom: "lb",   catch: true,  pack: "Case of 12", lead: 3, stock: "in stock" },
    { sku: "SS8032", name: "Signature Strip Steak",          cat: "Dry-Aged Steaks", price: 36.00, uom: "lb",   catch: true,  pack: "Case of 10", lead: 3, stock: "low" },
    { sku: "SS1430", name: "Signature Flat Iron Steak",      cat: "Dry-Aged Steaks", price: 25.00, uom: "lb",   catch: true,  pack: "Case of 10", lead: 5, stock: "in stock" },
    { sku: "SG3600", name: "Dry-Aged Signature Ground Beef", cat: "Ground & Burgers",price:  8.00, uom: "lb",   catch: false, pack: "Case of 20", lead: 2, stock: "in stock" },
    { sku: "SB3611", name: "Dry-Aged Burger Patties 5.3oz",  cat: "Ground & Burgers",price: 60.00, uom: "case", catch: false, pack: "Case of 40", lead: 2, stock: "in stock" },
    { sku: "SR2042", name: "SB Dry-Aged Brisket, Whole",     cat: "Roasts",          price: 18.00, uom: "lb",   catch: true,  pack: "Each",       lead: 7, stock: "on backorder" },
    { sku: "SR2344", name: "SB Dry-Aged Short Ribs",         cat: "Roasts",          price: 16.00, uom: "lb",   catch: true,  pack: "Case of 6",  lead: 5, stock: "in stock" }
  ],
  standing: [
    { sku: "SG3600", qty: 40 },
    { sku: "SB3611", qty: 2 },
    { sku: "SS8032", qty: 15 }
  ],
  orders: [
    { id: "SO-DEMO-0142", placed: "2026-09-22", status: "Delivered", total: 1284.00,
      note: "Weekly standing order", tracking: "1Z-DEMO-0000-0000-01",
      lines: [["SG3600", 40, 8.00], ["SB3611", 2, 60.00], ["SS8032", 15, 36.00]] },
    { id: "SO-DEMO-0147", placed: "2026-09-26", status: "Packed, awaiting pickup", total: 1284.00,
      note: "Weekly standing order", tracking: "1Z-DEMO-0000-0000-02",
      lines: [["SG3600", 40, 8.00], ["SB3611", 2, 60.00], ["SS8032", 15, 36.00]] },
    { id: "SO-DEMO-0151", placed: "2026-09-28", status: "Received", total: 946.00,
      note: "Added brisket for the weekend", tracking: null,
      lines: [["SG3600", 40, 8.00], ["SR2042", 18, 18.00]] }
  ],
  invoices: [
    { id: "INV-DEMO-0088", order: "SO-DEMO-0142", issued: "2026-09-22", due: "2026-10-22", total: 1284.00, status: "Open" },
    { id: "INV-DEMO-0081", order: "SO-DEMO-0136", issued: "2026-09-15", due: "2026-10-15", total: 1102.00, status: "Paid" }
  ]
};
