#!/usr/bin/env python3
"""1901-inspect-printify-product: read one exact Printify product by id and return verified production
metadata as one JSON object. Read-only: every request is an HTTP GET; the script has no other verb.
It never creates, updates, publishes, unpublishes, locks, deletes, or touches variants, and it writes no
file. Values are Printify's raw values; anything Printify did not return is the string "UNAVAILABLE".

usage: inspect_product.py --product-id <24-hex id>        (credential: PRINTIFY_API_TOKEN in the environment)
"""
import argparse, datetime, json, os, re, sys, urllib.error, urllib.request

API = "https://api.printify.com/v1"
TOKEN_ENV = "PRINTIFY_API_TOKEN"
UNAVAILABLE = "UNAVAILABLE"
PRODUCT_ID = re.compile(r"^[0-9a-f]{24}$")
METHOD = "GET"  # the only HTTP method this skill knows


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class Transport:
    """Live HTTP transport. get() is the only request method; it returns (status, body_json_or_None, error)."""
    def __init__(self, token, timeout=30):
        self.token, self.timeout = token, timeout

    def get(self, path):
        req = urllib.request.Request(API + path, method=METHOD, headers={
            "Authorization": f"Bearer {self.token}", "User-Agent": "1901-inspect-printify-product (read-only)", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read().decode("utf-8", "replace")
                try:
                    return r.status, json.loads(raw), None
                except ValueError:
                    return r.status, None, "response was not JSON"
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read().decode("utf-8", "replace"))
            except Exception:  # noqa: BLE001
                body = None
            return e.code, body, f"HTTP {e.code}"
        except Exception as e:  # noqa: BLE001
            return 0, None, f"{e.__class__.__name__}: {str(e)[:120]}"


def inspect(product_id, transport, now=None):
    out = {"skill": "1901-inspect-printify-product", "product_id": "", "result": "", "read_only": True, "timestamp": now or now_iso(),
           "shop": UNAVAILABLE, "product": UNAVAILABLE, "blueprint": UNAVAILABLE, "print_provider": UNAVAILABLE, "publishing": UNAVAILABLE,
           "options": UNAVAILABLE, "variants": UNAVAILABLE, "garment_colors": UNAVAILABLE, "print_areas": UNAVAILABLE, "placements": UNAVAILABLE,
           "images": UNAVAILABLE, "placeholder_dimensions": UNAVAILABLE, "shipping": UNAVAILABLE,
           "unavailable_fields": [], "warnings": [], "requests": [], "checks": [], "human_action_required": None}
    checks, warnings, unavailable = out["checks"], out["warnings"], out["unavailable_fields"]
    def chk(name, status, detail): checks.append({"check": name, "status": status, "detail": detail})
    def done(result, action=None): out["result"] = result; out["human_action_required"] = action; return out
    def get(path):
        if transport is None:
            return 0, None, "no transport"
        status, body, err = transport.get(path)
        out["requests"].append({"method": METHOD, "path": path, "status": status})
        return status, body, err
    def unavail(field, why):
        unavailable.append(field); warnings.append(f"{field}: {UNAVAILABLE} ({why})")

    pid = product_id.strip() if isinstance(product_id, str) else ""
    out["product_id"] = pid
    if not PRODUCT_ID.match(pid):
        chk("input", "FAIL", f"{pid!r} is not one exact Printify product id (24 lowercase hex characters); nothing was requested")
        return done("INVALID_INPUT", "Supply exactly one Printify product id, then re-run.")
    chk("input", "PASS", f"product id {pid}")

    if transport is None:
        chk("credential", "FAIL", f"{TOKEN_ENV} is not set in the runtime environment; nothing was requested")
        return done("CREDENTIAL_MISSING", f"Install the Printify credential as {TOKEN_ENV} in the OpenMausBot service environment, then re-run.")
    chk("credential", "PASS", f"{TOKEN_ENV} present (value never printed)")

    # 1. shops
    status, shops, err = get("/shops.json")
    if status in (401, 403):
        chk("shops", "FAIL", f"Printify rejected the credential ({err})"); return done("AUTH_FAILED", "The Printify credential was rejected; a human must check the token's validity and scopes.")
    if status != 200 or not isinstance(shops, list):
        chk("shops", "FAIL", f"shops could not be listed ({err or status})"); return done("SOURCE_UNAVAILABLE", "Printify could not be read; re-run when the API is reachable.")
    if not shops:
        chk("shops", "FAIL", "the credential's account has no shops"); return done("NOT_FOUND", "No Printify shop is connected to this credential; a human must check the account.")
    chk("shops", "PASS", f"{len(shops)} shop(s) on the account: " + ", ".join(f"{s.get('id')} {s.get('title')!r}" for s in shops))

    # 2. the product, in exactly one shop
    hits, hard = [], []
    for s in shops:
        st, body, e = get(f"/shops/{s.get('id')}/products/{pid}.json")
        if st == 200 and isinstance(body, dict): hits.append((s, body))
        elif st == 404: continue
        else: hard.append(f"shop {s.get('id')}: {e or st}")
    if hard and not hits:
        chk("product", "FAIL", "; ".join(hard)); return done("SOURCE_UNAVAILABLE", "Printify could not be read for the product; re-run when the API is reachable.")
    if not hits:
        chk("product", "FAIL", f"no shop on this account has a product with id {pid}"); return done("NOT_FOUND", f"Printify has no product {pid} in any shop of this account; a human must confirm the id.")
    if len(hits) > 1:
        chk("product", "FAIL", f"product id {pid} exists in {len(hits)} shops ({', '.join(str(s.get('id')) for s, _ in hits)}); none chosen")
        return done("AMBIGUOUS_SHOP", f"Product {pid} exists in more than one shop; a human must say which shop governs.")
    if hard: warnings.append("some shops could not be read: " + "; ".join(hard))
    shop, p = hits[0]
    out["shop"] = {"id": shop.get("id"), "title": shop.get("title", UNAVAILABLE), "sales_channel": shop.get("sales_channel", UNAVAILABLE)}
    g = lambda k: p.get(k, UNAVAILABLE)  # noqa: E731
    out["product"] = {"id": g("id"), "title": g("title"), "tags": g("tags"), "created_at": g("created_at"), "updated_at": g("updated_at"),
                      "blueprint_id": g("blueprint_id"), "print_provider_id": g("print_provider_id"), "shop_id": g("shop_id"), "user_id": g("user_id"),
                      "description_length": len(p["description"]) if isinstance(p.get("description"), str) else UNAVAILABLE,
                      "print_details": g("print_details"), "is_printify_express_eligible": g("is_printify_express_eligible"),
                      "is_printify_express_enabled": g("is_printify_express_enabled"), "is_economy_shipping_eligible": g("is_economy_shipping_eligible"),
                      "is_economy_shipping_enabled": g("is_economy_shipping_enabled")}
    if p.get("id") != pid:
        chk("product", "FAIL", f"Printify returned id {p.get('id')!r} for a request of {pid}"); return done("SOURCE_UNAVAILABLE", "Printify returned a different product than requested; re-run and, if it repeats, a human must investigate.")
    chk("product", "PASS", f"product {pid} {p.get('title')!r} read from shop {shop.get('id')}")

    # 3. publishing / visibility: raw fields only; nothing derived except the documented meaning of `external`
    ext = p.get("external")
    out["publishing"] = {"visible": g("visible"), "is_locked": g("is_locked"), "external": ext if ext is not None else UNAVAILABLE,
                         "sales_channel_properties": g("sales_channel_properties"),
                         "published_to_sales_channel": True if isinstance(ext, dict) and ext.get("id") else UNAVAILABLE}
    if out["publishing"]["published_to_sales_channel"] == UNAVAILABLE:
        unavail("publishing.published_to_sales_channel", "Printify returned no external listing id; absence is not proof of an unpublished state")

    # 4. options and variants (raw ids preserved; titles mapped from the product's own options)
    options = p.get("options") if isinstance(p.get("options"), list) else []
    out["options"] = options if options else UNAVAILABLE
    value_index = {}
    for o in options:
        for v in o.get("values") or []:
            entry = {"option": o.get("name"), "type": o.get("type"), "id": v.get("id"), "title": v.get("title")}
            if o.get("type") == "color": entry["colors"] = v.get("colors", UNAVAILABLE)
            value_index[v.get("id")] = entry
    variants = p.get("variants") if isinstance(p.get("variants"), list) else []
    enabled = []
    for v in variants:
        if not v.get("is_enabled"): continue
        mapped = {}
        for vid in v.get("options") or []:
            m = value_index.get(vid)
            key = (m["type"] or m["option"] or str(vid)) if m else str(vid)
            mapped[key] = m or {"id": vid, "title": UNAVAILABLE}
        enabled.append({"id": v.get("id"), "sku": v.get("sku", UNAVAILABLE), "title": v.get("title", UNAVAILABLE), "options": mapped,
                        "price": v.get("price", UNAVAILABLE), "cost": v.get("cost", UNAVAILABLE), "grams": v.get("grams", UNAVAILABLE),
                        "is_default": v.get("is_default", UNAVAILABLE), "is_available": v.get("is_available", UNAVAILABLE)})
    out["variants"] = {"total_count": len(variants), "enabled_count": len(enabled), "price_cost_unit": "integer minor units as returned by Printify (cents); currency not returned by this endpoint", "enabled": enabled} if variants else UNAVAILABLE
    if not variants: unavail("variants", "product carries no variants array")
    chk("variants", "PASS" if variants else "FAIL", f"{len(enabled)} of {len(variants)} variants enabled")

    colors = []
    for o in options:
        if o.get("type") != "color": continue
        for v in o.get("values") or []:
            ev = [e["id"] for e in enabled if any(m.get("id") == v.get("id") for m in e["options"].values())]
            if ev: colors.append({"option_value_id": v.get("id"), "title": v.get("title"), "hex": v.get("colors", UNAVAILABLE), "enabled_variant_ids": ev})
    out["garment_colors"] = colors if colors else UNAVAILABLE
    if not colors: unavail("garment_colors", "no color-type option is attached to an enabled variant")
    chk("garment_colors", "PASS" if colors else "FAIL", ", ".join(f"{c['title']} {c['hex']}" for c in colors) if colors else "none")

    # 5. print areas and placements (raw coordinates as Printify returns them: x/y relative, scale, angle)
    areas = p.get("print_areas") if isinstance(p.get("print_areas"), list) else []
    out["print_areas"] = areas if areas else UNAVAILABLE
    placements, image_ids = {}, []
    for a in areas:
        for ph in a.get("placeholders") or []:
            pos = ph.get("position", UNAVAILABLE)
            imgs = []
            for im in ph.get("images") or []:
                imgs.append({k: im.get(k, UNAVAILABLE) for k in ("id", "name", "type", "x", "y", "scale", "angle", "height", "width")})
                if im.get("id") and im["id"] not in image_ids: image_ids.append(im["id"])
            placements.setdefault(pos, []).append({"variant_ids": a.get("variant_ids", UNAVAILABLE), "images": imgs})
    out["placements"] = placements if placements else UNAVAILABLE
    if not areas: unavail("print_areas", "product carries no print_areas array")
    chk("print_areas", "PASS" if areas else "FAIL", f"positions: {', '.join(placements) or 'none'}; {len(image_ids)} distinct image id(s)")

    # 6. the assigned images, by id, from the uploads library (404 → the image is not in this account's uploads)
    images = {}
    for iid in image_ids:
        st, body, e = get(f"/uploads/{iid}.json")
        if st == 200 and isinstance(body, dict):
            images[iid] = {k: body.get(k, UNAVAILABLE) for k in ("id", "file_name", "height", "width", "size", "mime_type", "upload_time", "preview_url")}
        else:
            images[iid] = UNAVAILABLE; unavail(f"images.{iid}", f"uploads lookup returned {e or st}")
    out["images"] = images if image_ids else UNAVAILABLE

    # 7. catalog: blueprint, print provider, placeholder dimensions, shipping (each UNAVAILABLE on its own)
    bid, ppid = p.get("blueprint_id"), p.get("print_provider_id")
    st, body, e = get(f"/catalog/blueprints/{bid}.json")
    if st == 200 and isinstance(body, dict): out["blueprint"] = {k: body.get(k, UNAVAILABLE) for k in ("id", "title", "brand", "model")}
    else: unavail("blueprint", f"catalog lookup returned {e or st}")
    st, body, e = get(f"/catalog/print_providers/{ppid}.json")
    if st == 200 and isinstance(body, dict): out["print_provider"] = {k: body.get(k, UNAVAILABLE) for k in ("id", "title", "location")}
    else: unavail("print_provider", f"catalog lookup returned {e or st}")
    st, body, e = get(f"/catalog/blueprints/{bid}/print_providers/{ppid}/variants.json")
    enabled_ids = {v["id"] for v in enabled}
    if st == 200 and isinstance(body, dict) and isinstance(body.get("variants"), list):
        dims = {}
        for cv in body["variants"]:
            if cv.get("id") not in enabled_ids: continue
            for ph in cv.get("placeholders") or []:
                key = (ph.get("position"), ph.get("width"), ph.get("height"))
                dims.setdefault(key, []).append(cv.get("id"))
        out["placeholder_dimensions"] = [{"position": k[0], "width": k[1], "height": k[2], "variant_ids": v} for k, v in dims.items()] or UNAVAILABLE
        if not dims: unavail("placeholder_dimensions", "catalog variants list no placeholders for the enabled variants")
    else: unavail("placeholder_dimensions", f"catalog variants lookup returned {e or st}")
    st, body, e = get(f"/catalog/blueprints/{bid}/print_providers/{ppid}/shipping.json")
    if st == 200 and isinstance(body, dict):
        profiles = [pr for pr in (body.get("profiles") or []) if set(pr.get("variant_ids") or []) & enabled_ids]
        out["shipping"] = {"handling_time": body.get("handling_time", UNAVAILABLE), "profiles_for_enabled_variants": profiles or UNAVAILABLE}
        if not profiles: unavail("shipping.profiles_for_enabled_variants", "no shipping profile covers an enabled variant")
    else: unavail("shipping", f"catalog shipping lookup returned {e or st}")
    chk("catalog", "PASS" if out["blueprint"] != UNAVAILABLE and out["print_provider"] != UNAVAILABLE else "INFO",
        f"blueprint {bid}: {out['blueprint'] if out['blueprint'] == UNAVAILABLE else out['blueprint'].get('title')!r}; provider {ppid}: {out['print_provider'] if out['print_provider'] == UNAVAILABLE else out['print_provider'].get('title')!r}")

    chk("read_only", "PASS", f"{len(out['requests'])} request(s), all {METHOD}; nothing written anywhere")
    return done("INSPECTED", None)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--product-id", required=True)
    a = ap.parse_args(argv)
    token = os.environ.get(TOKEN_ENV)
    print(json.dumps(inspect(a.product_id, Transport(token) if token else None), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
