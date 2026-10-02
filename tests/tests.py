"""Fixture tests for 1901-inspect-printify-product. A fake transport stands in for Printify; no network."""
import json, os, sys, copy, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, ".."))
import inspect_product as skill

PID = "6ab2812a4fba5f26c6069462"; TS = "2026-10-02T15:00:00Z"
SHOPS = [{"id": 29030392, "title": "1901 Main Street", "sales_channel": "etsy"}]
PRODUCT = {"id": PID, "title": "1901-093 Porch Cat Tee", "description": "Soft cotton tee.", "tags": ["1901", "cat"], "visible": True, "is_locked": False,
           "blueprint_id": 6, "print_provider_id": 99, "shop_id": 29030392, "user_id": 1, "created_at": "2026-09-20 10:00:00+00:00", "updated_at": "2026-10-01 12:00:00+00:00",
           "print_details": {"print_on_side": "regular"}, "is_printify_express_eligible": False,
           "options": [{"name": "Colors", "type": "color", "values": [{"id": 521, "title": "Black", "colors": ["#000000"]}, {"id": 418, "title": "Heather Navy", "colors": ["#2b3a55"]}, {"id": 999, "title": "White", "colors": ["#ffffff"]}]},
                       {"name": "Sizes", "type": "size", "values": [{"id": 14, "title": "S"}, {"id": 15, "title": "M"}]}],
           "variants": [{"id": 12100, "sku": "1901-093-BLK-S", "title": "Black / S", "options": [521, 14], "price": 2499, "cost": 1180, "grams": 180, "is_enabled": True, "is_default": True, "is_available": True},
                        {"id": 12101, "sku": "1901-093-BLK-M", "title": "Black / M", "options": [521, 15], "price": 2499, "cost": 1180, "grams": 190, "is_enabled": True, "is_default": False, "is_available": True},
                        {"id": 12200, "sku": "1901-093-NVY-S", "title": "Heather Navy / S", "options": [418, 14], "price": 2499, "cost": 1180, "grams": 180, "is_enabled": True, "is_default": False, "is_available": True},
                        {"id": 12300, "sku": "1901-093-WHT-S", "title": "White / S", "options": [999, 14], "price": 2499, "cost": 1180, "grams": 180, "is_enabled": False, "is_default": False, "is_available": True}],
           "images": [{"src": "https://images.example/mock.png", "variant_ids": [12100], "position": "front", "is_default": True}],
           "print_areas": [{"variant_ids": [12100, 12101, 12200, 12300], "placeholders": [
               {"position": "front", "images": [{"id": "68e0a1b2c3d4e5f60718293a", "name": "1901-093-B-transparent-prep-v2.png", "type": "image/png", "height": 4500, "width": 4500, "x": 0.5, "y": 0.42, "scale": 0.85, "angle": 0}]},
               {"position": "back", "images": []}]}],
           "sales_channel_properties": {"free_shipping": False}, "external": {"id": "1899001122", "handle": "https://www.etsy.com/listing/1899001122"}}
UPLOAD = {"id": "68e0a1b2c3d4e5f60718293a", "file_name": "1901-093-B-transparent-prep-v2.png", "height": 4500, "width": 4500, "size": 1823345, "mime_type": "image/png", "preview_url": "https://images.example/preview.png", "upload_time": "2026-10-01 13:40:12"}
BLUEPRINT = {"id": 6, "title": "Unisex Heavy Cotton Tee", "brand": "Gildan", "model": "5000", "images": []}
PROVIDER = {"id": 99, "title": "Monster Digital", "location": {"address1": "16085 NW 52nd Ave", "city": "Miami", "country": "US", "zip": "33014"}}
CAT_VARIANTS = {"id": 99, "title": "Monster Digital", "variants": [
    {"id": 12100, "title": "Black / S", "options": {"color": "Black", "size": "S"}, "placeholders": [{"position": "front", "height": 4800, "width": 4000}, {"position": "back", "height": 4800, "width": 4000}]},
    {"id": 12101, "title": "Black / M", "options": {"color": "Black", "size": "M"}, "placeholders": [{"position": "front", "height": 4800, "width": 4000}, {"position": "back", "height": 4800, "width": 4000}]},
    {"id": 12200, "title": "Heather Navy / S", "options": {"color": "Heather Navy", "size": "S"}, "placeholders": [{"position": "front", "height": 4800, "width": 4000}, {"position": "back", "height": 4800, "width": 4000}]},
    {"id": 12300, "title": "White / S", "options": {"color": "White", "size": "S"}, "placeholders": [{"position": "front", "height": 4800, "width": 4000}]}]}
SHIPPING = {"handling_time": {"value": 3, "unit": "day"}, "profiles": [
    {"variant_ids": [12100, 12101, 12200, 12300], "first_item": {"cost": 475, "currency": "USD"}, "additional_items": {"cost": 240, "currency": "USD"}, "countries": ["US"]},
    {"variant_ids": [77777], "first_item": {"cost": 999, "currency": "USD"}, "additional_items": {"cost": 500, "currency": "USD"}, "countries": ["REST_OF_THE_WORLD"]}]}

def routes(**over):
    r = {"/shops.json": (200, SHOPS), f"/shops/29030392/products/{PID}.json": (200, PRODUCT), "/uploads/68e0a1b2c3d4e5f60718293a.json": (200, UPLOAD),
         "/catalog/blueprints/6.json": (200, BLUEPRINT), "/catalog/print_providers/99.json": (200, PROVIDER),
         "/catalog/blueprints/6/print_providers/99/variants.json": (200, CAT_VARIANTS), "/catalog/blueprints/6/print_providers/99/shipping.json": (200, SHIPPING)}
    r.update(over); return r

class Fake:
    def __init__(self, routes, fail=False): self.routes, self.fail, self.log = routes, fail, []
    def get(self, path):
        self.log.append(("GET", path))
        if self.fail: return 0, None, "URLError: network unreachable"
        st, body = self.routes.get(path, (404, {"error": "Not found"}))
        return st, copy.deepcopy(body), None if st == 200 else f"HTTP {st}"

examples = {}
def T(n, name, out, result, extra=None):
    assert out["result"] == result, (n, out["result"], result, out["checks"][-1])
    assert out["read_only"] is True
    if extra: extra(out)
    print(f"{n:>3}. PASS {name}: {result}"); examples[n] = out

def full_ok(o):
    assert o["shop"] == {"id": 29030392, "title": "1901 Main Street", "sales_channel": "etsy"}
    assert o["product"]["id"] == PID and o["product"]["title"] == "1901-093 Porch Cat Tee" and o["product"]["blueprint_id"] == 6 and o["product"]["print_provider_id"] == 99
    assert o["blueprint"] == {"id": 6, "title": "Unisex Heavy Cotton Tee", "brand": "Gildan", "model": "5000"} and o["print_provider"]["title"] == "Monster Digital"
    assert o["publishing"]["visible"] is True and o["publishing"]["is_locked"] is False and o["publishing"]["published_to_sales_channel"] is True and o["publishing"]["external"]["id"] == "1899001122"
    assert o["variants"]["total_count"] == 4 and o["variants"]["enabled_count"] == 3 and [v["id"] for v in o["variants"]["enabled"]] == [12100, 12101, 12200]
    v = o["variants"]["enabled"][0]; assert v["sku"] == "1901-093-BLK-S" and v["price"] == 2499 and v["cost"] == 1180 and v["options"]["color"]["title"] == "Black" and v["options"]["color"]["colors"] == ["#000000"] and v["options"]["size"]["title"] == "S"
    assert o["garment_colors"] == [{"option_value_id": 521, "title": "Black", "hex": ["#000000"], "enabled_variant_ids": [12100, 12101]}, {"option_value_id": 418, "title": "Heather Navy", "hex": ["#2b3a55"], "enabled_variant_ids": [12200]}], o["garment_colors"]
    assert "White" not in json.dumps(o["garment_colors"])  # disabled colour never reported as a garment colour
    f = o["placements"]["front"][0]["images"][0]; assert f == {"id": "68e0a1b2c3d4e5f60718293a", "name": "1901-093-B-transparent-prep-v2.png", "type": "image/png", "x": 0.5, "y": 0.42, "scale": 0.85, "angle": 0, "height": 4500, "width": 4500}
    assert o["placements"]["back"][0]["images"] == [] and o["print_areas"] == PRODUCT["print_areas"]
    assert o["images"]["68e0a1b2c3d4e5f60718293a"]["file_name"] == "1901-093-B-transparent-prep-v2.png" and o["images"]["68e0a1b2c3d4e5f60718293a"]["size"] == 1823345
    assert o["placeholder_dimensions"] == [{"position": "front", "width": 4000, "height": 4800, "variant_ids": [12100, 12101, 12200]}, {"position": "back", "width": 4000, "height": 4800, "variant_ids": [12100, 12101, 12200]}], o["placeholder_dimensions"]
    assert o["shipping"]["handling_time"] == {"value": 3, "unit": "day"} and len(o["shipping"]["profiles_for_enabled_variants"]) == 1 and o["shipping"]["profiles_for_enabled_variants"][0]["first_item"]["cost"] == 475
    assert o["unavailable_fields"] == [] and o["warnings"] == [] and o["human_action_required"] is None
    assert all(r["method"] == "GET" for r in o["requests"]) and len(o["requests"]) == 7
fk = Fake(routes()); T(1, "full product", skill.inspect(PID, fk, TS), "INSPECTED", full_ok); assert all(m == "GET" for m, _ in fk.log)

# 2 partial: uploads 404, shipping 500, catalog variants missing, no external, no color option on enabled variants
P2 = copy.deepcopy(PRODUCT); del P2["external"]; P2["options"][0]["type"] = "colour-ish"
fk = Fake(routes(**{f"/shops/29030392/products/{PID}.json": (200, P2), "/uploads/68e0a1b2c3d4e5f60718293a.json": (404, {"error": "Not found"}),
                    "/catalog/blueprints/6/print_providers/99/shipping.json": (500, None), "/catalog/blueprints/6/print_providers/99/variants.json": (429, None)}))
def partial_ok(o):
    assert o["publishing"]["external"] == "UNAVAILABLE" and o["publishing"]["published_to_sales_channel"] == "UNAVAILABLE"
    assert o["images"]["68e0a1b2c3d4e5f60718293a"] == "UNAVAILABLE" and o["shipping"] == "UNAVAILABLE" and o["placeholder_dimensions"] == "UNAVAILABLE" and o["garment_colors"] == "UNAVAILABLE"
    assert set(o["unavailable_fields"]) == {"publishing.published_to_sales_channel", "garment_colors", "images.68e0a1b2c3d4e5f60718293a", "placeholder_dimensions", "shipping"}, o["unavailable_fields"]
    assert o["blueprint"]["title"] == "Unisex Heavy Cotton Tee" and o["variants"]["enabled_count"] == 3
    assert "false" not in json.dumps(o["publishing"]["published_to_sales_channel"])
T(2, "fields Printify did not return are UNAVAILABLE, never inferred", skill.inspect(PID, fk, TS), "INSPECTED", partial_ok)

# 3 not found anywhere
fk = Fake(routes(**{f"/shops/29030392/products/{PID}.json": (404, {"error": "Not found"})}))
T(3, "product not in any shop", skill.inspect(PID, fk, TS), "NOT_FOUND", lambda o: o["shop"] == "UNAVAILABLE" and len(o["requests"]) == 2 or sys.exit("3"))
# 4 auth failed
fk = Fake(routes(**{"/shops.json": (401, {"message": "Unauthenticated."})})); T(4, "credential rejected", skill.inspect(PID, fk, TS), "AUTH_FAILED", lambda o: len(o["requests"]) == 1 or sys.exit("4"))
# 5 credential missing → zero requests
T(5, "credential missing", skill.inspect(PID, None, TS), "CREDENTIAL_MISSING", lambda o: o["requests"] == [] or sys.exit("5"))
# 6 network down
fk = Fake(routes(), fail=True); T(6, "Printify unreachable", skill.inspect(PID, fk, TS), "SOURCE_UNAVAILABLE")
# 7 invalid inputs → zero requests
for bad in ("", " ", "1901-093", PID.upper(), PID + "x", "6ab2812a 4fba5f26c6069462", None):
    o = skill.inspect(bad, Fake(routes()), TS); assert o["result"] == "INVALID_INPUT" and o["requests"] == [], bad
print("  7. PASS invalid inputs: INVALID_INPUT, nothing requested")
assert skill.inspect(f"  {PID}\n", Fake(routes()), TS)["result"] == "INSPECTED"; print(" 7b. PASS surrounding whitespace trimmed")
# 8 ambiguous: two shops both answer
fk = Fake(routes(**{"/shops.json": (200, SHOPS + [{"id": 1, "title": "Other", "sales_channel": "shopify"}]), f"/shops/1/products/{PID}.json": (200, PRODUCT)}))
T(8, "same id in two shops", skill.inspect(PID, fk, TS), "AMBIGUOUS_SHOP", lambda o: o["shop"] == "UNAVAILABLE" or sys.exit("8"))
# 8b second shop 404 → still exactly one hit
fk = Fake(routes(**{"/shops.json": (200, SHOPS + [{"id": 1, "title": "Other", "sales_channel": "shopify"}])})); T("8b", "two shops, one hit", skill.inspect(PID, fk, TS), "INSPECTED")
# 9 no shops
fk = Fake(routes(**{"/shops.json": (200, [])})); T(9, "account has no shops", skill.inspect(PID, fk, TS), "NOT_FOUND")
# 10 Printify returns a different id than requested
P10 = copy.deepcopy(PRODUCT); P10["id"] = "000000000000000000000000"
fk = Fake(routes(**{f"/shops/29030392/products/{PID}.json": (200, P10)})); T(10, "returned id differs from request", skill.inspect(PID, fk, TS), "SOURCE_UNAVAILABLE")
# 11 static: the script knows no verb but GET, writes no file, and nothing in it mutates Printify/Sheets/Drive
src = open(os.path.join(HERE, "..", "inspect_product.py")).read()
for label, pat in (("non-GET verb", r"method\s*=\s*[\"'](POST|PUT|PATCH|DELETE)|\.(post|put|patch|delete)\("), ("file write", r"open\([^)]*[\"'](w|a|wb|ab)[\"']"), ("Sheets/Drive", r"spreadsheets|gspread|googleapis|drive\.")):
    assert not re.search(pat, src, re.I), label
assert src.count('METHOD = "GET"') == 1 and "urlopen" in src
print(" 11. PASS static: GET is the only HTTP method; no file writes; no Sheets/Drive")
print("ALL PASS")
if "--dump" in sys.argv:
    for n in (1, 2, 3, 4, 5):
        open(os.path.join(HERE, f"ex{n}.json"), "w").write(json.dumps(examples[n], indent=1, ensure_ascii=False) + "\n")
