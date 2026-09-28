/* Interactive demo of the proposed Shipley Farms partner API.
 *
 * Everything is local. There is no network call, no account and no server. The "API calls" shown
 * are the PROPOSED contract rendered from the same local data the screens use, so the screens
 * and the documentation cannot drift apart while we are still designing it.
 */
(function () {
  var D = window.DEMO, cart = {}, placed = [];
  D.standing.forEach(function (l) { cart[l.sku] = l.qty; });

  var SCREENS = [
    ["auth", "Authentication"], ["catalog", "Your catalog"],
    ["order", "Place an order"], ["orders", "Orders"], ["invoices", "Invoices"]
  ];
  var current = "auth";

  function el(t, a, kids) {
    var n = document.createElement(t); a = a || {};
    Object.keys(a).forEach(function (k) {
      if (k === "html") n.innerHTML = a[k]; else if (k === "text") n.textContent = a[k];
      else n.setAttribute(k, a[k]);
    });
    (kids || []).forEach(function (c) { n.appendChild(c); });
    return n;
  }
  function money(n) { return "$" + n.toFixed(2); }
  function prod(sku) {
    for (var i = 0; i < D.products.length; i++) if (D.products[i].sku === sku) return D.products[i];
    return null;
  }
  function stockPill(s) {
    var c = s === "in stock" ? "ok" : (s === "low" ? "low" : "no");
    return '<span class="pill ' + c + '">' + s + "</span>";
  }
  function hl(s) {
    return s.replace(/^(GET|POST|PUT|PATCH|DELETE) /gm, '<span class="mth">$1</span> ')
            .replace(/"([^"]+)":/g, '<span class="k">"$1"</span>:')
            .replace(/# (.*)$/gm, '<span class="cmt"># $1</span>');
  }
  function apiPanel(title, body) {
    var d = el("details", { class: "api" });
    d.appendChild(el("summary", { text: title || "Show the API call behind this screen" }));
    d.appendChild(el("pre", { html: hl(body) }));
    return d;
  }

  var views = {};

  views.auth = function () {
    var w = el("div");
    w.appendChild(el("div", { class: "card", html:
      '<h1>Authentication</h1>' +
      '<p class="lead">One key per partner account. It identifies you, and everything you can ' +
      'see is scoped to your account by the server, not by the client asking nicely.</p>' +
      '<div class="grid">' +
        '<div><strong>Account</strong><br>' + D.account.name + '<br><code>' + D.account.id + '</code></div>' +
        '<div><strong>Contact</strong><br>' + D.account.contact + '</div>' +
        '<div><strong>Terms</strong><br>' + D.account.terms + '</div>' +
      '</div>' +
      '<div class="note"><strong>Scoping is the whole design.</strong> There is no endpoint that ' +
      'returns another partner\'s pricing, orders or invoices, and no parameter that widens what ' +
      'a key can reach. If a request would cross accounts it fails, rather than filtering after ' +
      'the fact.</div>'
    }));
    w.appendChild(apiPanel("Show how a request is authenticated",
      '# Every request carries the account key. Nothing is passed in the URL.\n' +
      'GET /api/partner/v1/catalog HTTP/1.1\n' +
      'Host: shipleyfarmsbeef.com\n' +
      'Authorization: Bearer ' + D.account.key + '\n' +
      'Accept: application/json\n\n' +
      '# The server resolves the key to ONE account and scopes every read and write to it.\n' +
      '# 401 if the key is unknown or revoked. 403 if the account is suspended.\n' +
      '# There is no "account_id" parameter, because there is nothing to pass.'));
    return w;
  };

  views.catalog = function () {
    var rows = D.products.map(function (p) {
      return "<tr><td><code>" + p.sku + "</code></td><td>" + p.name +
        (p.catch ? '<span class="est">sold by weight, price is an estimate</span>' : "") +
        '</td><td class="hide">' + p.pack + '</td><td class="num">' + money(p.price) + " / " + p.uom +
        '</td><td class="hide">' + p.lead + " days</td><td>" + stockPill(p.stock) + "</td></tr>";
    }).join("");
    var w = el("div");
    w.appendChild(el("div", { class: "card", html:
      "<h1>Your catalog</h1>" +
      '<p class="lead">The same products anyone can read publicly, plus the four things a ' +
      'business actually needs and the public feed does not carry: <strong>your price, pack ' +
      'size, lead time and stock</strong>.</p>' +
      '<table><thead><tr><th>SKU</th><th>Product</th><th class="hide">Pack</th>' +
      '<th class="num">Your price</th><th class="hide">Lead</th><th>Stock</th></tr></thead>' +
      "<tbody>" + rows + "</tbody></table>" +
      '<div class="note"><strong>Catch weight is not a rounding detail.</strong> Items sold by ' +
      'the pound are priced from an average weight. The invoice reflects what was actually ' +
      'packed, so a client that renders these as firm prices will disagree with the invoice.</div>'
    }));
    w.appendChild(apiPanel(null,
      'GET /api/partner/v1/catalog\n' +
      'Authorization: Bearer ' + D.account.key + '\n\n' +
      '200 OK\n' +
      '{\n' +
      '  "account": "' + D.account.id + '",\n' +
      '  "currency": "USD",\n' +
      '  "generated_at": "2026-09-28T17:50:00Z",\n' +
      '  "items": [\n' +
      '    {\n' +
      '      "sku": "SS1231",\n' +
      '      "name": "Signature Huston Ribeye",\n' +
      '      "your_price": 42.00,\n' +
      '      "uom": "lb",\n' +
      '      "catch_weight": true,        # price is an estimate, invoice is by actual weight\n' +
      '      "pack": "Case of 8",\n' +
      '      "lead_time_days": 3,\n' +
      '      "availability": "in_stock"\n' +
      '    }\n' +
      '  ]\n' +
      '}'));
    return w;
  };

  views.order = function () {
    var w = el("div"), total = 0;
    var rows = D.products.map(function (p) {
      var q = cart[p.sku] || 0; total += q * p.price;
      return '<tr><td><code>' + p.sku + '</code></td><td>' + p.name + '</td>' +
        '<td class="num">' + money(p.price) + "</td>" +
        '<td class="num"><input type="number" min="0" step="1" value="' + q +
        '" data-sku="' + p.sku + '"></td>' +
        '<td class="num" id="line-' + p.sku + '">' + money(q * p.price) + "</td></tr>";
    }).join("");
    w.appendChild(el("div", { class: "card", html:
      "<h1>Place an order</h1>" +
      '<p class="lead">Pre-filled with this account\'s standing weekly order, which is the point: ' +
      'a kitchen that buys the same thing every week should not rebuild it every week.</p>' +
      '<table><thead><tr><th>SKU</th><th>Product</th><th class="num">Price</th>' +
      '<th class="num">Qty</th><th class="num">Line</th></tr></thead><tbody>' + rows +
      '</tbody><tfoot><tr><th colspan="4" class="num">Estimated total</th>' +
      '<th class="num" id="total">' + money(total) + "</th></tr></tfoot></table>" +
      '<p style="margin-top:1rem"><button class="act" id="place">Place this order</button> ' +
      '<button class="ghost" id="reset">Reset to standing order</button></p>' +
      '<div class="note"><strong>Estimated, because of catch weight.</strong> The confirmed total ' +
      'comes back on the order and the final figure is on the invoice, after packing.</div>' +
      '<div id="placed"></div>'
    }));
    w.appendChild(apiPanel(null,
      'POST /api/partner/v1/orders\n' +
      'Authorization: Bearer ' + D.account.key + '\n' +
      'Idempotency-Key: 7f3a1c2e-demo   # safe to retry; a repeat returns the same order\n\n' +
      '{\n' +
      '  "requested_delivery": "2026-10-05",\n' +
      '  "reference": "week 40",\n' +
      '  "lines": [\n' +
      '    { "sku": "SG3600", "quantity": 40 },\n' +
      '    { "sku": "SB3611", "quantity": 2 }\n' +
      '  ]\n' +
      '}\n\n' +
      '201 Created\n' +
      '{\n' +
      '  "order_id": "SO-2026-01234",\n' +
      '  "status": "received",\n' +
      '  "estimated_total": 440.00,\n' +
      '  "estimate_only": true,          # catch weight lines are not final until packed\n' +
      '  "confirmed_delivery": null      # set when a person confirms the date\n' +
      '}'));
    return w;
  };

  views.orders = function () {
    // Newest first. D.orders is oldest-to-newest and anything placed in this session is
    // newer still, so concatenate in chronological order THEN reverse.
    var all = D.orders.concat(placed).slice().reverse();
    var rows = all.map(function (o) {
      return "<tr><td><code>" + o.id + "</code></td><td>" + o.placed +
        '</td><td class="hide">' + (o.note || "") + '</td><td><span class="pill">' + o.status +
        '</span></td><td class="hide">' + (o.tracking ? "<code>" + o.tracking + "</code>" : "not shipped") +
        '</td><td class="num">' + money(o.total) + "</td></tr>";
    }).join("");
    var w = el("div");
    w.appendChild(el("div", { class: "card", html:
      "<h1>Orders</h1>" +
      '<p class="lead">Every order this account has placed, however it was placed: through this ' +
      'API, over the phone, or by a member of our team keying it in. One list, not two.</p>' +
      '<table><thead><tr><th>Order</th><th>Placed</th><th class="hide">Reference</th>' +
      '<th>Status</th><th class="hide">Tracking</th><th class="num">Total</th></tr></thead>' +
      "<tbody>" + rows + "</tbody></table>"
    }));
    w.appendChild(apiPanel(null,
      'GET /api/partner/v1/orders?since=2026-09-01\n' +
      'Authorization: Bearer ' + D.account.key + '\n\n' +
      '200 OK\n' +
      '{\n' +
      '  "orders": [\n' +
      '    {\n' +
      '      "order_id": "SO-DEMO-0147",\n' +
      '      "placed_at": "2026-09-26",\n' +
      '      "status": "packed",         # received | confirmed | packed | shipped | delivered | cancelled\n' +
      '      "total": 1284.00,\n' +
      '      "final": false,             # true once weighed and invoiced\n' +
      '      "tracking": "1Z...",\n' +
      '      "channel": "api"            # api | phone | staff, so your system sees ALL of them\n' +
      '    }\n' +
      '  ]\n' +
      '}'));
    return w;
  };

  views.invoices = function () {
    var rows = D.invoices.map(function (i) {
      return "<tr><td><code>" + i.id + "</code></td><td><code>" + i.order +
        '</code></td><td class="hide">' + i.issued + "</td><td>" + i.due +
        '</td><td><span class="pill ' + (i.status === "Paid" ? "ok" : "") + '">' + i.status +
        '</span></td><td class="num">' + money(i.total) + "</td></tr>";
    }).join("");
    var w = el("div");
    w.appendChild(el("div", { class: "card", html:
      "<h1>Invoices</h1>" +
      '<p class="lead">Read-only. Your invoices, what they were for, and what is outstanding.</p>' +
      '<table><thead><tr><th>Invoice</th><th>Order</th><th class="hide">Issued</th><th>Due</th>' +
      '<th>Status</th><th class="num">Total</th></tr></thead><tbody>' + rows + "</tbody></table>" +
      '<div class="note"><strong>Reading only.</strong> Paying through this API is not proposed. ' +
      'Payment stays on the rails you already have with us, because putting a payment path in a ' +
      'partner integration is a liability neither of us needs.</div>'
    }));
    w.appendChild(apiPanel(null,
      'GET /api/partner/v1/invoices?status=open\n' +
      'Authorization: Bearer ' + D.account.key + '\n\n' +
      '200 OK\n' +
      '{\n' +
      '  "invoices": [\n' +
      '    {\n' +
      '      "invoice_id": "INV-2026-0088",\n' +
      '      "order_id": "SO-2026-0142",\n' +
      '      "issued": "2026-09-22",\n' +
      '      "due": "2026-10-22",\n' +
      '      "total": 1284.00,          # final: actual packed weight, not the estimate\n' +
      '      "status": "open",\n' +
      '      "pdf": "https://.../invoice.pdf"\n' +
      '    }\n' +
      '  ]\n' +
      '}'));
    return w;
  };

  function render() {
    document.getElementById("acct").innerHTML =
      "<strong>" + D.account.name + "</strong><br>" + D.account.id;
    var nav = document.getElementById("nav"); nav.innerHTML = "";
    SCREENS.forEach(function (s) {
      var b = el("button", { text: s[1] });
      if (s[0] === current) b.setAttribute("aria-current", "true");
      b.onclick = function () { current = s[0]; render(); };
      nav.appendChild(b);
    });
    var v = document.getElementById("view");
    v.innerHTML = ""; v.appendChild(views[current]());
    if (current === "order") wireOrder();
  }

  function wireOrder() {
    var inputs = document.querySelectorAll('input[data-sku]');
    function recalc() {
      var t = 0;
      Array.prototype.forEach.call(inputs, function (i) {
        var sku = i.getAttribute("data-sku"), q = parseInt(i.value, 10) || 0;
        cart[sku] = q;
        var line = q * prod(sku).price; t += line;
        document.getElementById("line-" + sku).textContent = money(line);
      });
      document.getElementById("total").textContent = money(t);
      return t;
    }
    Array.prototype.forEach.call(inputs, function (i) { i.oninput = recalc; });
    document.getElementById("reset").onclick = function () {
      Object.keys(cart).forEach(function (k) { cart[k] = 0; });
      D.standing.forEach(function (l) { cart[l.sku] = l.qty; });
      render();
    };
    document.getElementById("place").onclick = function () {
      var t = recalc();
      if (t <= 0) return;
      var id = "SO-DEMO-0" + (152 + placed.length);
      placed.push({ id: id, placed: "2026-09-28", status: "Received", total: t,
                    note: "Placed in this demo", tracking: null, lines: [] });
      document.getElementById("placed").innerHTML =
        '<div class="note" style="border-left-color:var(--ok)"><strong>Order ' + id +
        " received.</strong> Estimated total " + money(t) +
        ". It now appears under Orders. Nothing was sent anywhere: this is a demo.</div>";
      document.getElementById("place").disabled = true;
    };
  }

  render();
})();
