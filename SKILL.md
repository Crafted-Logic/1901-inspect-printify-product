---
name: 1901-inspect-printify-product
description: Reads one exact Printify product or draft by product id and returns its verified production metadata as one JSON object; read-only, every request a GET, nothing inferred.
---

# 1901 Inspect Printify Product

Skill #8 in the 1901 Main Street production workflow: a read-only window
onto one Printify product or draft. Given exactly one Printify product id it
returns what Printify actually says about that product: shop, title,
blueprint, print provider, visibility and publishing fields, enabled
variants with their option ids, garment colours with Printify's own hex
values, print areas with the exact placement coordinates Printify exposes,
the image ids and files assigned to each position, variant price and cost,
placeholder dimensions, and shipping metadata.

Core rule: **VERIFY, DON'T ASSUME.** Every value is Printify's raw value for
that product, read in this run. A field Printify did not return is the
string `UNAVAILABLE`; nothing is inferred, defaulted, rounded, converted, or
filled from memory, a filename, another product, or chat.

Expected use: inspect a design's Printify draft (for example 1901-093), then
let a human write that design's governed product specification from the
verified result. This skill never writes that specification, or anything
else.

## When to Use

- "Inspect Printify product 6ab2812a4fba5f26c6069462."
- "What blueprint, provider and colours does 1901-093's Printify draft use?"
- "Which image is on the front of this Printify product, and where?"
- Before anyone writes or changes a governed product spec from Printify data.

Not for: creating or editing products, enabling or disabling variants,
publishing or unpublishing, uploading images, changing prices, reading
orders, or reading Etsy. Any such request → explain that this skill is
read-only and stop.

## Authoritative Sources

| Source | Identifier |
|---|---|
| Printify REST API | `https://api.printify.com/v1` |
| Credential | environment variable `PRINTIFY_API_TOKEN` (set in the OpenMausBot service environment; shared by every bot on the box) |
| Inspection script | `/home/claude/agents/1901/1901-inspect-printify-product/inspect_product.py` |

The credential is **full scope** at the account level. Read-only is a rule
of this skill, not a property of the token: the script knows no HTTP method
but GET, and Walter never calls Printify any other way. Never print, echo,
log, quote, or pass the token as an argument; the script reads it from the
environment itself. Memory, chat history, prior runs, the Idea Queue, and
Drive are not evidence of what Printify holds; only this run's responses are.

## Input

Exactly one Printify product id, for example `6ab2812a4fba5f26c6069462`:
24 lowercase hexadecimal characters. Trim surrounding whitespace and nothing
else. No case folding, no guessing from a design id, a title, or a URL
fragment; a design id such as `1901-093` is not a product id. Anything else
→ `INVALID_INPUT` with no request made. The shop is discovered from the
credential's account, never supplied or assumed.

## Procedure

Run the script; it performs every step below and prints the JSON object.

```bash
python3 /home/claude/agents/1901/1901-inspect-printify-product/inspect_product.py --product-id <id>
```

1. **Input.** Validate the id as above.
2. **Credential.** `PRINTIFY_API_TOKEN` must be present; absent →
   `CREDENTIAL_MISSING`, no request made.
3. **Shops.** `GET /shops.json`. `401`/`403` → `AUTH_FAILED`; any other
   failure → `SOURCE_UNAVAILABLE`; an account with no shop → `NOT_FOUND`.
4. **Product.** `GET /shops/{shop_id}/products/{id}.json` in every shop on
   the account. Exactly one shop answers `200` → continue with that shop.
   None → `NOT_FOUND`. More than one → `AMBIGUOUS_SHOP`, nothing chosen. A
   `200` whose `id` differs from the request → `SOURCE_UNAVAILABLE`.
5. **Publishing fields.** `visible`, `is_locked`, `external`,
   `sales_channel_properties` as returned. `published_to_sales_channel` is
   `true` only when Printify returned an `external` listing id; otherwise
   `UNAVAILABLE`, never `false`, because absence is not proof.
6. **Options and variants.** Every variant with `is_enabled = true`, with
   its raw variant id, SKU, title, option value ids mapped through the
   product's own `options` (colour values carry Printify's hex `colors`),
   `price`, `cost`, `grams`, `is_default`, `is_available`. Price and cost
   are the integers Printify returns (minor units); no currency is returned
   by this endpoint and none is assumed.
7. **Garment colours.** Each colour option value attached to at least one
   enabled variant: option value id, title, hex, enabled variant ids.
   Disabled colours are not garment colours of this product.
8. **Print areas and placements.** `print_areas` exactly as returned, plus
   a per-position view (`front`, `back`, sleeves, …) of each assigned image:
   image id, name, type, `x`, `y`, `scale`, `angle`, `width`, `height`, as
   Printify stores them (`x`/`y` relative to the print area, `angle` in
   degrees). An empty position is reported as having no image.
9. **Images.** `GET /uploads/{image_id}.json` for each assigned image id:
   file name, dimensions, size, MIME type, upload time, preview URL. A `404`
   means the image is not in this account's uploads library → that image is
   `UNAVAILABLE`, with a warning.
10. **Catalog.** Blueprint (`GET /catalog/blueprints/{id}.json`), print
    provider (`GET /catalog/print_providers/{id}.json`), placeholder
    dimensions for the enabled variants (`…/variants.json`), and shipping
    (`…/shipping.json`: handling time and the profiles that cover an enabled
    variant). Each is independently `UNAVAILABLE` on failure; the result is
    still `INSPECTED`.
11. **Record.** Every request appears in `requests` with its method (always
    `GET`), path, and status. Every field that came back `UNAVAILABLE` is
    listed in `unavailable_fields` with a warning saying why.

Return the script's JSON object unchanged as the reply. Do not summarise
away ids, do not round coordinates, do not translate hex values, do not
re-order or dedupe Printify's lists, and do not add fields the script did
not return.

## Output

```json
{
  "skill": "1901-inspect-printify-product",
  "product_id": "",
  "result": "INSPECTED | INVALID_INPUT | CREDENTIAL_MISSING | AUTH_FAILED | NOT_FOUND | AMBIGUOUS_SHOP | SOURCE_UNAVAILABLE",
  "read_only": true,
  "timestamp": "ISO 8601 UTC",
  "shop": { "id": 0, "title": "", "sales_channel": "" },
  "product": { "id": "", "title": "", "tags": [], "created_at": "", "updated_at": "", "blueprint_id": 0, "print_provider_id": 0, "shop_id": 0, "user_id": 0, "description_length": 0, "print_details": {}, "is_printify_express_eligible": false, "is_printify_express_enabled": false, "is_economy_shipping_eligible": false, "is_economy_shipping_enabled": false },
  "blueprint": { "id": 0, "title": "", "brand": "", "model": "" },
  "print_provider": { "id": 0, "title": "", "location": {} },
  "publishing": { "visible": false, "is_locked": false, "external": {}, "sales_channel_properties": {}, "published_to_sales_channel": true },
  "options": [],
  "variants": { "total_count": 0, "enabled_count": 0, "price_cost_unit": "", "enabled": [ { "id": 0, "sku": "", "title": "", "options": { "color": { "option": "", "type": "color", "id": 0, "title": "", "colors": [] }, "size": { "option": "", "type": "size", "id": 0, "title": "" } }, "price": 0, "cost": 0, "grams": 0, "is_default": false, "is_available": true } ] },
  "garment_colors": [ { "option_value_id": 0, "title": "", "hex": [], "enabled_variant_ids": [] } ],
  "print_areas": [],
  "placements": { "front": [ { "variant_ids": [], "images": [ { "id": "", "name": "", "type": "", "x": 0, "y": 0, "scale": 0, "angle": 0, "height": 0, "width": 0 } ] } ] },
  "images": { "<image id>": { "id": "", "file_name": "", "height": 0, "width": 0, "size": 0, "mime_type": "", "upload_time": "", "preview_url": "" } },
  "placeholder_dimensions": [ { "position": "", "width": 0, "height": 0, "variant_ids": [] } ],
  "shipping": { "handling_time": {}, "profiles_for_enabled_variants": [] },
  "unavailable_fields": [],
  "warnings": [],
  "requests": [ { "method": "GET", "path": "", "status": 200 } ],
  "checks": [ { "check": "", "status": "PASS | FAIL | INFO", "detail": "" } ],
  "human_action_required": null
}
```

Any top-level block, and any field inside one, may instead be the string
`UNAVAILABLE`. Before the product is read, every block is `UNAVAILABLE`.

## Results

| result | requests | meaning |
|---|---|---|
| `INSPECTED` | yes | The product was read; the object holds what Printify returned, with `UNAVAILABLE` where it returned nothing |
| `INVALID_INPUT` | none | Not one exact 24-hex product id |
| `CREDENTIAL_MISSING` | none | `PRINTIFY_API_TOKEN` is not in the runtime environment |
| `AUTH_FAILED` | shops only | Printify rejected the credential |
| `NOT_FOUND` | shops + products | No shop on the account has the product, or the account has no shop |
| `AMBIGUOUS_SHOP` | shops + products | More than one shop answered for the id; nothing chosen |
| `SOURCE_UNAVAILABLE` | partial | Printify could not be read, or returned a different product than requested |

## Never Do

- Send anything but `GET`: no product create, update, publish, unpublish,
  lock, delete; no variant enable/disable; no price change; no upload; no
  order read or write; no webhook.
- Write to the Idea Queue, Google Drive, the governing documents, the
  staging root, or any file. The script prints to stdout only.
- Print, echo, quote, or pass the token. Report the credential by name only.
- Fill a missing field from a filename, a title, a design id, another
  product, the Idea Queue, memory, or chat. `UNAVAILABLE` is the answer.
- Convert prices to dollars, round coordinates, normalise hex case, or
  translate Printify's titles.
- Decide whether a product is "correct", "ready", or "the right draft".
  This skill reports; governance decides.

## Pitfalls

- **"Inspect 1901-093."** A design id is not a product id. Ask for the
  Printify product id, or read it from the design's governed record through
  the skill that owns that record; never guess it.
- **`external` is absent, so the product is unpublished.** Not proven.
  `published_to_sales_channel` is `UNAVAILABLE`; the raw `visible` and
  `is_locked` values are reported as they are.
- **The back carries `test-navy-reuse.png`.** Report it exactly. Whether a
  test image belongs on the product is a human question.
- **579 variants, 93 enabled.** Report only the enabled ones in `variants`,
  with the totals; the full raw `print_areas` keep every variant id.
- **The uploads lookup 404s for an image.** The image is on the product but
  not in this account's uploads library; `UNAVAILABLE` plus a warning, no
  substitute.
- **Price is `2636`.** That is Printify's integer. Do not write `$26.36`.

## Live Test Policy

Fixture tests (`tests/tests.py`, a fake transport, no network) are the
development verification. Live reads are read-only and free, and may be run
on request against any product id the Architect names. Nothing in this
skill is ever authorised to write.

## Examples

Fixture outputs from `tests/tests.py`. Ids, titles and values are fixtures;
live output carries what Printify actually returned.

### A. Full product: INSPECTED

```json
{
 "skill": "1901-inspect-printify-product",
 "product_id": "6ab2812a4fba5f26c6069462",
 "result": "INSPECTED",
 "read_only": true,
 "timestamp": "2026-10-02T15:00:00Z",
 "shop": {
  "id": 29030392,
  "title": "1901 Main Street",
  "sales_channel": "etsy"
 },
 "product": {
  "id": "6ab2812a4fba5f26c6069462",
  "title": "1901-093 Porch Cat Tee",
  "tags": [
   "1901",
   "cat"
  ],
  "created_at": "2026-09-20 10:00:00+00:00",
  "updated_at": "2026-10-01 12:00:00+00:00",
  "blueprint_id": 6,
  "print_provider_id": 99,
  "shop_id": 29030392,
  "user_id": 1,
  "description_length": 16,
  "print_details": {
   "print_on_side": "regular"
  },
  "is_printify_express_eligible": false,
  "is_printify_express_enabled": "UNAVAILABLE",
  "is_economy_shipping_eligible": "UNAVAILABLE",
  "is_economy_shipping_enabled": "UNAVAILABLE"
 },
 "blueprint": {
  "id": 6,
  "title": "Unisex Heavy Cotton Tee",
  "brand": "Gildan",
  "model": "5000"
 },
 "print_provider": {
  "id": 99,
  "title": "Monster Digital",
  "location": {
   "address1": "16085 NW 52nd Ave",
   "city": "Miami",
   "country": "US",
   "zip": "33014"
  }
 },
 "publishing": {
  "visible": true,
  "is_locked": false,
  "external": {
   "id": "1899001122",
   "handle": "https://www.etsy.com/listing/1899001122"
  },
  "sales_channel_properties": {
   "free_shipping": false
  },
  "published_to_sales_channel": true
 },
 "options": [
  {
   "name": "Colors",
   "type": "color",
   "values": [
    {
     "id": 521,
     "title": "Black",
     "colors": [
      "#000000"
     ]
    },
    {
     "id": 418,
     "title": "Heather Navy",
     "colors": [
      "#2b3a55"
     ]
    },
    {
     "id": 999,
     "title": "White",
     "colors": [
      "#ffffff"
     ]
    }
   ]
  },
  {
   "name": "Sizes",
   "type": "size",
   "values": [
    {
     "id": 14,
     "title": "S"
    },
    {
     "id": 15,
     "title": "M"
    }
   ]
  }
 ],
 "variants": {
  "total_count": 4,
  "enabled_count": 3,
  "price_cost_unit": "integer minor units as returned by Printify (cents); currency not returned by this endpoint",
  "enabled": [
   {
    "id": 12100,
    "sku": "1901-093-BLK-S",
    "title": "Black / S",
    "options": {
     "color": {
      "option": "Colors",
      "type": "color",
      "id": 521,
      "title": "Black",
      "colors": [
       "#000000"
      ]
     },
     "size": {
      "option": "Sizes",
      "type": "size",
      "id": 14,
      "title": "S"
     }
    },
    "price": 2499,
    "cost": 1180,
    "grams": 180,
    "is_default": true,
    "is_available": true
   },
   {
    "id": 12101,
    "sku": "1901-093-BLK-M",
    "title": "Black / M",
    "options": {
     "color": {
      "option": "Colors",
      "type": "color",
      "id": 521,
      "title": "Black",
      "colors": [
       "#000000"
      ]
     },
     "size": {
      "option": "Sizes",
      "type": "size",
      "id": 15,
      "title": "M"
     }
    },
    "price": 2499,
    "cost": 1180,
    "grams": 190,
    "is_default": false,
    "is_available": true
   },
   {
    "id": 12200,
    "sku": "1901-093-NVY-S",
    "title": "Heather Navy / S",
    "options": {
     "color": {
      "option": "Colors",
      "type": "color",
      "id": 418,
      "title": "Heather Navy",
      "colors": [
       "#2b3a55"
      ]
     },
     "size": {
      "option": "Sizes",
      "type": "size",
      "id": 14,
      "title": "S"
     }
    },
    "price": 2499,
    "cost": 1180,
    "grams": 180,
    "is_default": false,
    "is_available": true
   }
  ]
 },
 "garment_colors": [
  {
   "option_value_id": 521,
   "title": "Black",
   "hex": [
    "#000000"
   ],
   "enabled_variant_ids": [
    12100,
    12101
   ]
  },
  {
   "option_value_id": 418,
   "title": "Heather Navy",
   "hex": [
    "#2b3a55"
   ],
   "enabled_variant_ids": [
    12200
   ]
  }
 ],
 "print_areas": [
  {
   "variant_ids": [
    12100,
    12101,
    12200,
    12300
   ],
   "placeholders": [
    {
     "position": "front",
     "images": [
      {
       "id": "68e0a1b2c3d4e5f60718293a",
       "name": "1901-093-B-transparent-prep-v2.png",
       "type": "image/png",
       "height": 4500,
       "width": 4500,
       "x": 0.5,
       "y": 0.42,
       "scale": 0.85,
       "angle": 0
      }
     ]
    },
    {
     "position": "back",
     "images": []
    }
   ]
  }
 ],
 "placements": {
  "front": [
   {
    "variant_ids": [
     12100,
     12101,
     12200,
     12300
    ],
    "images": [
     {
      "id": "68e0a1b2c3d4e5f60718293a",
      "name": "1901-093-B-transparent-prep-v2.png",
      "type": "image/png",
      "x": 0.5,
      "y": 0.42,
      "scale": 0.85,
      "angle": 0,
      "height": 4500,
      "width": 4500
     }
    ]
   }
  ],
  "back": [
   {
    "variant_ids": [
     12100,
     12101,
     12200,
     12300
    ],
    "images": []
   }
  ]
 },
 "images": {
  "68e0a1b2c3d4e5f60718293a": {
   "id": "68e0a1b2c3d4e5f60718293a",
   "file_name": "1901-093-B-transparent-prep-v2.png",
   "height": 4500,
   "width": 4500,
   "size": 1823345,
   "mime_type": "image/png",
   "upload_time": "2026-10-01 13:40:12",
   "preview_url": "https://images.example/preview.png"
  }
 },
 "placeholder_dimensions": [
  {
   "position": "front",
   "width": 4000,
   "height": 4800,
   "variant_ids": [
    12100,
    12101,
    12200
   ]
  },
  {
   "position": "back",
   "width": 4000,
   "height": 4800,
   "variant_ids": [
    12100,
    12101,
    12200
   ]
  }
 ],
 "shipping": {
  "handling_time": {
   "value": 3,
   "unit": "day"
  },
  "profiles_for_enabled_variants": [
   {
    "variant_ids": [
     12100,
     12101,
     12200,
     12300
    ],
    "first_item": {
     "cost": 475,
     "currency": "USD"
    },
    "additional_items": {
     "cost": 240,
     "currency": "USD"
    },
    "countries": [
     "US"
    ]
   }
  ]
 },
 "unavailable_fields": [],
 "warnings": [],
 "requests": [
  {
   "method": "GET",
   "path": "/shops.json",
   "status": 200
  },
  {
   "method": "GET",
   "path": "/shops/29030392/products/6ab2812a4fba5f26c6069462.json",
   "status": 200
  },
  {
   "method": "GET",
   "path": "/uploads/68e0a1b2c3d4e5f60718293a.json",
   "status": 200
  },
  {
   "method": "GET",
   "path": "/catalog/blueprints/6.json",
   "status": 200
  },
  {
   "method": "GET",
   "path": "/catalog/print_providers/99.json",
   "status": 200
  },
  {
   "method": "GET",
   "path": "/catalog/blueprints/6/print_providers/99/variants.json",
   "status": 200
  },
  {
   "method": "GET",
   "path": "/catalog/blueprints/6/print_providers/99/shipping.json",
   "status": 200
  }
 ],
 "checks": [
  {
   "check": "input",
   "status": "PASS",
   "detail": "product id 6ab2812a4fba5f26c6069462"
  },
  {
   "check": "credential",
   "status": "PASS",
   "detail": "PRINTIFY_API_TOKEN present (value never printed)"
  },
  {
   "check": "shops",
   "status": "PASS",
   "detail": "1 shop(s) on the account: 29030392 '1901 Main Street'"
  },
  {
   "check": "product",
   "status": "PASS",
   "detail": "product 6ab2812a4fba5f26c6069462 '1901-093 Porch Cat Tee' read from shop 29030392"
  },
  {
   "check": "variants",
   "status": "PASS",
   "detail": "3 of 4 variants enabled"
  },
  {
   "check": "garment_colors",
   "status": "PASS",
   "detail": "Black ['#000000'], Heather Navy ['#2b3a55']"
  },
  {
   "check": "print_areas",
   "status": "PASS",
   "detail": "positions: front, back; 1 distinct image id(s)"
  },
  {
   "check": "catalog",
   "status": "PASS",
   "detail": "blueprint 6: 'Unisex Heavy Cotton Tee'; provider 99: 'Monster Digital'"
  },
  {
   "check": "read_only",
   "status": "PASS",
   "detail": "7 request(s), all GET; nothing written anywhere"
  }
 ],
 "human_action_required": null
}
```

### B. Fields Printify did not return: UNAVAILABLE, never inferred

`external` absent, uploads `404`, shipping `500`, catalog variants `429`, no colour-type option on an enabled variant.

```json
{
 "skill": "1901-inspect-printify-product",
 "product_id": "6ab2812a4fba5f26c6069462",
 "result": "INSPECTED",
 "read_only": true,
 "timestamp": "2026-10-02T15:00:00Z",
 "shop": {
  "id": 29030392,
  "title": "1901 Main Street",
  "sales_channel": "etsy"
 },
 "product": {
  "id": "6ab2812a4fba5f26c6069462",
  "title": "1901-093 Porch Cat Tee",
  "tags": [
   "1901",
   "cat"
  ],
  "created_at": "2026-09-20 10:00:00+00:00",
  "updated_at": "2026-10-01 12:00:00+00:00",
  "blueprint_id": 6,
  "print_provider_id": 99,
  "shop_id": 29030392,
  "user_id": 1,
  "description_length": 16,
  "print_details": {
   "print_on_side": "regular"
  },
  "is_printify_express_eligible": false,
  "is_printify_express_enabled": "UNAVAILABLE",
  "is_economy_shipping_eligible": "UNAVAILABLE",
  "is_economy_shipping_enabled": "UNAVAILABLE"
 },
 "blueprint": {
  "id": 6,
  "title": "Unisex Heavy Cotton Tee",
  "brand": "Gildan",
  "model": "5000"
 },
 "print_provider": {
  "id": 99,
  "title": "Monster Digital",
  "location": {
   "address1": "16085 NW 52nd Ave",
   "city": "Miami",
   "country": "US",
   "zip": "33014"
  }
 },
 "publishing": {
  "visible": true,
  "is_locked": false,
  "external": "UNAVAILABLE",
  "sales_channel_properties": {
   "free_shipping": false
  },
  "published_to_sales_channel": "UNAVAILABLE"
 },
 "options": [
  {
   "name": "Colors",
   "type": "colour-ish",
   "values": [
    {
     "id": 521,
     "title": "Black",
     "colors": [
      "#000000"
     ]
    },
    {
     "id": 418,
     "title": "Heather Navy",
     "colors": [
      "#2b3a55"
     ]
    },
    {
     "id": 999,
     "title": "White",
     "colors": [
      "#ffffff"
     ]
    }
   ]
  },
  {
   "name": "Sizes",
   "type": "size",
   "values": [
    {
     "id": 14,
     "title": "S"
    },
    {
     "id": 15,
     "title": "M"
    }
   ]
  }
 ],
 "variants": {
  "total_count": 4,
  "enabled_count": 3,
  "price_cost_unit": "integer minor units as returned by Printify (cents); currency not returned by this endpoint",
  "enabled": [
   {
    "id": 12100,
    "sku": "1901-093-BLK-S",
    "title": "Black / S",
    "options": {
     "colour-ish": {
      "option": "Colors",
      "type": "colour-ish",
      "id": 521,
      "title": "Black"
     },
     "size": {
      "option": "Sizes",
      "type": "size",
      "id": 14,
      "title": "S"
     }
    },
    "price": 2499,
    "cost": 1180,
    "grams": 180,
    "is_default": true,
    "is_available": true
   },
   {
    "id": 12101,
    "sku": "1901-093-BLK-M",
    "title": "Black / M",
    "options": {
     "colour-ish": {
      "option": "Colors",
      "type": "colour-ish",
      "id": 521,
      "title": "Black"
     },
     "size": {
      "option": "Sizes",
      "type": "size",
      "id": 15,
      "title": "M"
     }
    },
    "price": 2499,
    "cost": 1180,
    "grams": 190,
    "is_default": false,
    "is_available": true
   },
   {
    "id": 12200,
    "sku": "1901-093-NVY-S",
    "title": "Heather Navy / S",
    "options": {
     "colour-ish": {
      "option": "Colors",
      "type": "colour-ish",
      "id": 418,
      "title": "Heather Navy"
     },
     "size": {
      "option": "Sizes",
      "type": "size",
      "id": 14,
      "title": "S"
     }
    },
    "price": 2499,
    "cost": 1180,
    "grams": 180,
    "is_default": false,
    "is_available": true
   }
  ]
 },
 "garment_colors": "UNAVAILABLE",
 "print_areas": [
  {
   "variant_ids": [
    12100,
    12101,
    12200,
    12300
   ],
   "placeholders": [
    {
     "position": "front",
     "images": [
      {
       "id": "68e0a1b2c3d4e5f60718293a",
       "name": "1901-093-B-transparent-prep-v2.png",
       "type": "image/png",
       "height": 4500,
       "width": 4500,
       "x": 0.5,
       "y": 0.42,
       "scale": 0.85,
       "angle": 0
      }
     ]
    },
    {
     "position": "back",
     "images": []
    }
   ]
  }
 ],
 "placements": {
  "front": [
   {
    "variant_ids": [
     12100,
     12101,
     12200,
     12300
    ],
    "images": [
     {
      "id": "68e0a1b2c3d4e5f60718293a",
      "name": "1901-093-B-transparent-prep-v2.png",
      "type": "image/png",
      "x": 0.5,
      "y": 0.42,
      "scale": 0.85,
      "angle": 0,
      "height": 4500,
      "width": 4500
     }
    ]
   }
  ],
  "back": [
   {
    "variant_ids": [
     12100,
     12101,
     12200,
     12300
    ],
    "images": []
   }
  ]
 },
 "images": {
  "68e0a1b2c3d4e5f60718293a": "UNAVAILABLE"
 },
 "placeholder_dimensions": "UNAVAILABLE",
 "shipping": "UNAVAILABLE",
 "unavailable_fields": [
  "publishing.published_to_sales_channel",
  "garment_colors",
  "images.68e0a1b2c3d4e5f60718293a",
  "placeholder_dimensions",
  "shipping"
 ],
 "warnings": [
  "publishing.published_to_sales_channel: UNAVAILABLE (Printify returned no external listing id; absence is not proof of an unpublished state)",
  "garment_colors: UNAVAILABLE (no color-type option is attached to an enabled variant)",
  "images.68e0a1b2c3d4e5f60718293a: UNAVAILABLE (uploads lookup returned HTTP 404)",
  "placeholder_dimensions: UNAVAILABLE (catalog variants lookup returned HTTP 429)",
  "shipping: UNAVAILABLE (catalog shipping lookup returned HTTP 500)"
 ],
 "requests": [
  {
   "method": "GET",
   "path": "/shops.json",
   "status": 200
  },
  {
   "method": "GET",
   "path": "/shops/29030392/products/6ab2812a4fba5f26c6069462.json",
   "status": 200
  },
  {
   "method": "GET",
   "path": "/uploads/68e0a1b2c3d4e5f60718293a.json",
   "status": 404
  },
  {
   "method": "GET",
   "path": "/catalog/blueprints/6.json",
   "status": 200
  },
  {
   "method": "GET",
   "path": "/catalog/print_providers/99.json",
   "status": 200
  },
  {
   "method": "GET",
   "path": "/catalog/blueprints/6/print_providers/99/variants.json",
   "status": 429
  },
  {
   "method": "GET",
   "path": "/catalog/blueprints/6/print_providers/99/shipping.json",
   "status": 500
  }
 ],
 "checks": [
  {
   "check": "input",
   "status": "PASS",
   "detail": "product id 6ab2812a4fba5f26c6069462"
  },
  {
   "check": "credential",
   "status": "PASS",
   "detail": "PRINTIFY_API_TOKEN present (value never printed)"
  },
  {
   "check": "shops",
   "status": "PASS",
   "detail": "1 shop(s) on the account: 29030392 '1901 Main Street'"
  },
  {
   "check": "product",
   "status": "PASS",
   "detail": "product 6ab2812a4fba5f26c6069462 '1901-093 Porch Cat Tee' read from shop 29030392"
  },
  {
   "check": "variants",
   "status": "PASS",
   "detail": "3 of 4 variants enabled"
  },
  {
   "check": "garment_colors",
   "status": "FAIL",
   "detail": "none"
  },
  {
   "check": "print_areas",
   "status": "PASS",
   "detail": "positions: front, back; 1 distinct image id(s)"
  },
  {
   "check": "catalog",
   "status": "PASS",
   "detail": "blueprint 6: 'Unisex Heavy Cotton Tee'; provider 99: 'Monster Digital'"
  },
  {
   "check": "read_only",
   "status": "PASS",
   "detail": "7 request(s), all GET; nothing written anywhere"
  }
 ],
 "human_action_required": null
}
```

### C. Product in no shop: NOT_FOUND

```json
{
 "skill": "1901-inspect-printify-product",
 "product_id": "6ab2812a4fba5f26c6069462",
 "result": "NOT_FOUND",
 "read_only": true,
 "timestamp": "2026-10-02T15:00:00Z",
 "shop": "UNAVAILABLE",
 "product": "UNAVAILABLE",
 "blueprint": "UNAVAILABLE",
 "print_provider": "UNAVAILABLE",
 "publishing": "UNAVAILABLE",
 "options": "UNAVAILABLE",
 "variants": "UNAVAILABLE",
 "garment_colors": "UNAVAILABLE",
 "print_areas": "UNAVAILABLE",
 "placements": "UNAVAILABLE",
 "images": "UNAVAILABLE",
 "placeholder_dimensions": "UNAVAILABLE",
 "shipping": "UNAVAILABLE",
 "unavailable_fields": [],
 "warnings": [],
 "requests": [
  {
   "method": "GET",
   "path": "/shops.json",
   "status": 200
  },
  {
   "method": "GET",
   "path": "/shops/29030392/products/6ab2812a4fba5f26c6069462.json",
   "status": 404
  }
 ],
 "checks": [
  {
   "check": "input",
   "status": "PASS",
   "detail": "product id 6ab2812a4fba5f26c6069462"
  },
  {
   "check": "credential",
   "status": "PASS",
   "detail": "PRINTIFY_API_TOKEN present (value never printed)"
  },
  {
   "check": "shops",
   "status": "PASS",
   "detail": "1 shop(s) on the account: 29030392 '1901 Main Street'"
  },
  {
   "check": "product",
   "status": "FAIL",
   "detail": "no shop on this account has a product with id 6ab2812a4fba5f26c6069462"
  }
 ],
 "human_action_required": "Printify has no product 6ab2812a4fba5f26c6069462 in any shop of this account; a human must confirm the id."
}
```

### D. Credential missing: CREDENTIAL_MISSING, no request made

```json
{
 "skill": "1901-inspect-printify-product",
 "product_id": "6ab2812a4fba5f26c6069462",
 "result": "CREDENTIAL_MISSING",
 "read_only": true,
 "timestamp": "2026-10-02T15:00:00Z",
 "shop": "UNAVAILABLE",
 "product": "UNAVAILABLE",
 "blueprint": "UNAVAILABLE",
 "print_provider": "UNAVAILABLE",
 "publishing": "UNAVAILABLE",
 "options": "UNAVAILABLE",
 "variants": "UNAVAILABLE",
 "garment_colors": "UNAVAILABLE",
 "print_areas": "UNAVAILABLE",
 "placements": "UNAVAILABLE",
 "images": "UNAVAILABLE",
 "placeholder_dimensions": "UNAVAILABLE",
 "shipping": "UNAVAILABLE",
 "unavailable_fields": [],
 "warnings": [],
 "requests": [],
 "checks": [
  {
   "check": "input",
   "status": "PASS",
   "detail": "product id 6ab2812a4fba5f26c6069462"
  },
  {
   "check": "credential",
   "status": "FAIL",
   "detail": "PRINTIFY_API_TOKEN is not set in the runtime environment; nothing was requested"
  }
 ],
 "human_action_required": "Install the Printify credential as PRINTIFY_API_TOKEN in the OpenMausBot service environment, then re-run."
}
```

## Verification

The skill worked if the reply is one JSON object in the shape above; every
entry in `requests` is a `GET`; the token appears nowhere in the reply; every
id, coordinate, hex value and price equals Printify's raw value; every field
Printify did not return is `UNAVAILABLE` and listed in `unavailable_fields`;
and no Printify object, sheet cell, Drive file, document, or local file
changed.

## Assumptions and Limits

- OpenMausBot imports `SKILL.md` only. `inspect_product.py` reaches the VPS
  through this repository's local clone at
  `/home/claude/agents/1901/1901-inspect-printify-product/`; keep that clone
  at the imported commit.
- Printify rate limits apply (global 600 requests per minute, catalog 100
  per minute). One inspection makes seven to ten requests.
- Printify's product endpoint returns no currency; `price` and `cost` are
  reported as returned. Shipping profiles carry their own currency.
- Placement `x`/`y` are Printify's relative coordinates and `scale` and
  `angle` its stored values; this skill does not convert them to pixels.
