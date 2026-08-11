from datetime import UTC, datetime, timedelta

import pytest
from agentlens_worker.identity import (
    IdentityError,
    identity_from_certificate,
    overwrite_resource_identity,
    parse_spiffe_uri,
)
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
from opentelemetry.proto.resource.v1.resource_pb2 import Resource
from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans


def test_parse_spiffe_uri() -> None:
    identity = parse_spiffe_uri("spiffe://agentlens/tenant/acme/cluster/prod-a")
    assert identity.tenant_id == "acme"
    assert identity.cluster_id == "prod-a"


def test_parse_spiffe_uri_rejects_spoofed_shape() -> None:
    with pytest.raises(IdentityError):
        parse_spiffe_uri("spiffe://evil/tenant/acme/cluster/prod-a")


def _cert_with_uri(uri: str) -> x509.Certificate:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "edge-collector")])
    return (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC) - timedelta(minutes=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.UniformResourceIdentifier(uri)]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )


def test_identity_from_certificate_reads_uri_san() -> None:
    cert = _cert_with_uri("spiffe://agentlens/tenant/acme/cluster/prod-a")
    identity = identity_from_certificate(cert)
    assert identity.tenant_id == "acme"
    assert identity.cluster_id == "prod-a"


def test_overwrite_resource_identity_replaces_untrusted_claims() -> None:
    request = ExportTraceServiceRequest(
        resource_spans=[
            ResourceSpans(
                resource=Resource(
                    attributes=[
                        KeyValue(
                            key="agentlens.tenant_id",
                            value=AnyValue(string_value="spoofed-tenant"),
                        ),
                        KeyValue(
                            key="agentlens.cluster_id",
                            value=AnyValue(string_value="spoofed-cluster"),
                        ),
                    ]
                )
            )
        ]
    )
    identity = parse_spiffe_uri("spiffe://agentlens/tenant/acme/cluster/prod-a")
    overwrite_resource_identity(request, identity)
    attrs = {
        item.key: item.value.string_value for item in request.resource_spans[0].resource.attributes
    }
    assert attrs["agentlens.tenant_id"] == "acme"
    assert attrs["agentlens.cluster_id"] == "prod-a"
    assert attrs["agentlens.identity_source"] == "collector_credential"
