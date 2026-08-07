"""mTLS OTLP/HTTP gateway that stamps tenant/cluster from client certificates."""

from __future__ import annotations

import argparse
import logging
import os
import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
from cryptography import x509
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

from .identity import IdentityError, identity_from_certificate, overwrite_resource_identity

LOGGER = logging.getLogger("agentlens.identity_gateway")


class IdentityGatewayHandler(BaseHTTPRequestHandler):
    server: IdentityGatewayServer  # type: ignore[assignment]

    def log_message(self, format: str, *args: object) -> None:
        LOGGER.info("%s - %s", self.address_string(), format % args)

    def do_POST(self) -> None:
        if self.path not in {"/v1/traces", "/v1/traces/"}:
            self.send_error(404, "not found")
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            identity = identity_from_certificate(self.server.peer_certificate(self))
            request = ExportTraceServiceRequest()
            request.ParseFromString(body)
            overwrite_resource_identity(request, identity)
            response = httpx.post(
                self.server.upstream_url,
                content=request.SerializeToString(),
                headers={"Content-Type": "application/x-protobuf"},
                timeout=30.0,
            )
            self.send_response(response.status_code)
            content_type = response.headers.get("Content-Type", "application/x-protobuf")
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(response.content)
        except IdentityError as exc:
            LOGGER.warning("rejected untrusted collector credential: %s", exc)
            self.send_error(401, str(exc))
        except Exception:
            LOGGER.exception("identity gateway failed")
            self.send_error(502, "upstream forward failed")


class IdentityGatewayServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        upstream_url: str,
        ssl_context: ssl.SSLContext,
    ) -> None:
        super().__init__(server_address, IdentityGatewayHandler)
        self.upstream_url = upstream_url
        self.socket = ssl_context.wrap_socket(self.socket, server_side=True)

    def peer_certificate(self, handler: BaseHTTPRequestHandler) -> x509.Certificate:
        cert_binary = handler.connection.getpeercert(binary_form=True)  # type: ignore[attr-defined]
        if not cert_binary:
            raise IdentityError("client certificate required")
        return x509.load_der_x509_certificate(cert_binary)


def build_ssl_context(*, cert_file: Path, key_file: Path, client_ca_file: Path) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))
    context.load_verify_locations(cafile=str(client_ca_file))
    return context


def run() -> None:
    parser = argparse.ArgumentParser(description="Agent Lens mTLS OTLP identity gateway")
    parser.add_argument("--host", default=os.getenv("AGENTLENS_IDENTITY_HOST", "0.0.0.0"))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("AGENTLENS_IDENTITY_PORT", "4318")),
    )
    parser.add_argument(
        "--upstream-url",
        default=os.getenv("AGENTLENS_IDENTITY_UPSTREAM", "http://127.0.0.1:4319/v1/traces"),
    )
    parser.add_argument("--cert-file", type=Path, default=Path("/etc/agentlens/tls/tls.crt"))
    parser.add_argument("--key-file", type=Path, default=Path("/etc/agentlens/tls/tls.key"))
    parser.add_argument("--client-ca-file", type=Path, default=Path("/etc/agentlens/tls/ca.crt"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    context = build_ssl_context(
        cert_file=args.cert_file,
        key_file=args.key_file,
        client_ca_file=args.client_ca_file,
    )
    server = IdentityGatewayServer(
        (args.host, args.port),
        upstream_url=args.upstream_url,
        ssl_context=context,
    )
    LOGGER.info(
        "identity gateway listening on %s:%s → %s",
        args.host,
        args.port,
        args.upstream_url,
    )
    server.serve_forever()


if __name__ == "__main__":
    run()
