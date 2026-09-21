"""Opt-in, self-cleaning 15-guest HTTP/WebSocket capacity probe.

Example (isolated server only):
  python tools/load_benchmark.py --url http://127.0.0.1:8001 --password TEST_PASSWORD --push-rounds 3

The probe creates temporary, unseated guests and removes only those guests on
exit. It never changes seating, roles, or game phase. Push rounds change each
guest's lobby wish; they are refused outside a loopback, non-8000 lobby.
"""

from __future__ import annotations

import argparse
import asyncio
from http.cookiejar import CookieJar
import json
import math
import secrets
import sys
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener

from websockets.asyncio.client import connect


def validate_target(url: str, *, allow_live: bool, allow_remote: bool) -> str:
    parsed = urlsplit(url)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username
            or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
        raise ValueError("target must be an http(s) origin without credentials, path, query, or fragment")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("invalid target port") from exc
    if port == 8000 and not allow_live:
        raise ValueError("port 8000 requires --allow-live")
    if parsed.hostname not in {"127.0.0.1", "::1", "localhost"} and not allow_remote:
        raise ValueError("non-loopback target requires --allow-remote")
    return url.rstrip("/")


def websocket_url(origin: str) -> str:
    parsed = urlsplit(origin)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return f"{scheme}://{parsed.netloc}/ws"


def percentile_ms(samples: list[float], percentile: int) -> float | None:
    if not samples:
        return None
    ordered = sorted(samples)
    return round(ordered[max(0, math.ceil(percentile / 100 * len(ordered)) - 1)], 2)


def summary(samples: list[float], errors: int = 0) -> dict:
    return {"samples": len(samples), "errors": errors,
            "p50_ms": percentile_ms(samples, 50),
            "p95_ms": percentile_ms(samples, 95),
            "p99_ms": percentile_ms(samples, 99),
            "max_ms": round(max(samples), 2) if samples else None}


class Client:
    def __init__(self, origin: str):
        self.origin = origin
        self.cookies = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookies))
        self.player_id: str | None = None
        self.csrf_token: str | None = None
        self.socket = None

    def request(self, method: str, path: str, body: dict | None = None,
                password: str | None = None) -> dict:
        headers = {"Origin": self.origin}
        if password is not None:
            headers["X-Storyteller-Password"] = password
        if self.csrf_token is not None and method not in {"GET", "HEAD", "OPTIONS"}:
            headers["X-CSRF-Token"] = self.csrf_token
        if body is not None:
            headers["Content-Type"] = "application/json"
        payload = json.dumps(body).encode() if body is not None else None
        request = Request(self.origin + path, data=payload, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=10) as response:
                return json.load(response)
        except HTTPError as exc:
            detail = exc.read(300).decode(errors="replace")
            raise RuntimeError(f"{method} {path}: HTTP {exc.code}: {detail}") from exc

    async def open_socket(self) -> float:
        token = next((cookie.value for cookie in self.cookies if cookie.name == "botc_session"), None)
        if not token:
            raise RuntimeError("join did not return a session cookie")
        ws_url = websocket_url(self.origin)
        started = time.perf_counter()
        self.socket = await connect(ws_url, origin=self.origin,
                                    additional_headers={"Cookie": f"botc_session={token}"},
                                    proxy=None, open_timeout=10)
        snapshot = json.loads(await asyncio.wait_for(self.socket.recv(), 10))
        if snapshot.get("me", {}).get("id") != self.player_id:
            raise RuntimeError("WebSocket initial snapshot belongs to another player")
        return (time.perf_counter() - started) * 1000

    async def close_socket(self) -> None:
        if self.socket is not None:
            await self.socket.close()
            self.socket = None


async def measure_http(client: Client) -> float:
    started = time.perf_counter()
    view = await asyncio.to_thread(client.request, "GET", f"/api/me/{client.player_id}")
    if view.get("me", {}).get("id") != client.player_id:
        raise RuntimeError("HTTP view belongs to another player")
    return (time.perf_counter() - started) * 1000


async def receive_wish(client: Client, marker: str, started: float) -> float:
    while True:
        view = json.loads(await asyncio.wait_for(client.socket.recv(), 10))
        if view.get("me_wish") == marker:
            return (time.perf_counter() - started) * 1000


async def measure_push(client: Client, marker: str) -> float:
    started = time.perf_counter()
    receiver = asyncio.create_task(receive_wish(client, marker, started))
    try:
        await asyncio.to_thread(client.request, "POST", f"/api/player/{client.player_id}/wish",
                                {"wish": marker})
        return await receiver
    finally:
        if not receiver.done():
            receiver.cancel()
        await asyncio.gather(receiver, return_exceptions=True)


async def collect(tasks) -> tuple[list[float], int]:
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if isinstance(r, (int, float))], sum(isinstance(r, BaseException) for r in results)


async def benchmark(args: argparse.Namespace) -> dict:
    origin = validate_target(args.url, allow_live=args.allow_live, allow_remote=args.allow_remote)
    if not 1 <= args.players <= 15 or not 1 <= args.http_rounds <= 100 or not 0 <= args.push_rounds <= 20:
        raise ValueError("players must be 1..15, HTTP rounds 1..100, push rounds 0..20")
    if args.push_rounds and (urlsplit(origin).hostname not in {"127.0.0.1", "::1", "localhost"}
                             or urlsplit(origin).port == 8000):
        raise ValueError("push rounds are restricted to a loopback, non-8000 server")
    admin = Client(origin)
    state = await asyncio.to_thread(admin.request, "GET", "/api/state", password=args.password)
    if args.push_rounds and state.get("status") != "lobby":
        raise ValueError("push rounds require a lobby; wish changes are unavailable during play")
    room_code = state["room_code"]
    clients: list[Client] = []
    report = {"origin": origin, "requested_players": args.players,
              "note": "Latency is client-observed, including local scheduling and network time."}
    try:
        prefix = "load-" + secrets.token_hex(3)
        for index in range(args.players):
            client = Client(origin)
            joined = await asyncio.to_thread(client.request, "POST", "/api/join",
                                             {"name": f"{prefix}-{index + 1:02d}", "room_code": room_code})
            client.player_id = joined["player_id"]
            clients.append(client)
            session = await asyncio.to_thread(client.request, "GET", "/api/session")
            client.csrf_token = session["csrf_token"]
        report["joined_players"] = len(clients)
        connection, connection_errors = await collect(c.open_socket() for c in clients)
        report["websocket_initial"] = summary(connection, connection_errors)
        if connection_errors:
            raise RuntimeError(f"{connection_errors} initial WebSocket connection(s) failed")

        http_samples: list[float] = []
        http_errors = 0
        for _ in range(args.http_rounds):
            samples, errors = await collect(measure_http(c) for c in clients)
            http_samples.extend(samples)
            http_errors += errors
        report["http_me"] = summary(http_samples, http_errors)

        if args.push_rounds:
            push_samples: list[float] = []
            push_errors = 0
            for round_index in range(args.push_rounds):
                samples, errors = await collect(
                    measure_push(c, f"{prefix}-{round_index:02d}-{index:02d}")
                    for index, c in enumerate(clients))
                push_samples.extend(samples)
                push_errors += errors
            report["websocket_push"] = summary(push_samples, push_errors)
        else:
            report["websocket_push"] = {"skipped": "add --push-rounds on an isolated lobby"}

        await asyncio.gather(*(c.close_socket() for c in clients))
        reconnect, reconnect_errors = await collect(c.open_socket() for c in clients)
        report["websocket_reconnect"] = summary(reconnect, reconnect_errors)
        return report
    finally:
        await asyncio.gather(*(c.close_socket() for c in clients), return_exceptions=True)
        cleanup_errors = []
        for client in clients:
            try:
                await asyncio.to_thread(admin.request, "POST", f"/api/player/{client.player_id}/remove",
                                        {}, args.password)
            except Exception as exc:
                cleanup_errors.append(f"{client.player_id}: {exc}")
        report["cleanup_errors"] = cleanup_errors
        if cleanup_errors:
            print("WARNING: benchmark guest cleanup failed: " + "; ".join(cleanup_errors), file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="HTTP origin, e.g. http://127.0.0.1:8001")
    parser.add_argument("--password", required=True, help="storyteller password; never written to report")
    parser.add_argument("--players", type=int, default=15)
    parser.add_argument("--http-rounds", type=int, default=20)
    parser.add_argument("--push-rounds", type=int, default=0,
                        help="wish-change push rounds; isolated loopback lobby only")
    parser.add_argument("--allow-live", action="store_true", help="explicitly allow port 8000")
    parser.add_argument("--allow-remote", action="store_true", help="explicitly allow non-loopback URL")
    args = parser.parse_args()
    try:
        report = asyncio.run(benchmark(args))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if not any(report[k].get("errors", 0) for k in
                            ("http_me", "websocket_initial", "websocket_reconnect", "websocket_push")) \
            and not report["cleanup_errors"] else 1
    except Exception as exc:
        print(f"benchmark failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
