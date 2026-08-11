"""Derive authoritative tenant/cluster identity from edge collector credentials."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, cast

from cryptography import x509
from cryptography.x509.oid import ExtensionOID
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue

SPIFFE_PATTERN = re.compile(
    r"^spiffe://agentlens/tenant/(?P<tenant_id>[A-Za-z0-9._-]+)/cluster/(?P<cluster_id>[A-Za-z0-9._-]+)$"
)

TENANT_ATTR = "agentlens.tenant_id"
CLUSTER_ATTR = "agentlens.cluster_id"
IDENTITY_SOURCE_ATTR = "agentlens.identity_source"


class IdentityError(ValueError):
    """Raised when a client credential cannot yield a trusted Agent Lens identity."""


@dataclass(frozen=True, slots=True)
class CollectorIdentity:
    tenant_id: str
    cluster_id: str
    spiffe_id: str


def parse_spiffe_uri(uri: str) -> CollectorIdentity:
    match = SPIFFE_PATTERN.match(uri.strip())
    if match is None:
        raise IdentityError(
            "client certificate URI SAN must match "
            "spiffe://agentlens/tenant/<tenant_id>/cluster/<cluster_id>"
        )
    return CollectorIdentity(
        tenant_id=match.group("tenant_id"),
        cluster_id=match.group("cluster_id"),
        spiffe_id=uri.strip(),
    )


def identity_from_certificate(cert: x509.Certificate) -> CollectorIdentity:
    try:
        san = cast(
            x509.SubjectAlternativeName,
            cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME).value,
        )
    except x509.ExtensionNotFound as exc:
        raise IdentityError("client certificate is missing a Subject Alternative Name") from exc
    for general_name in san:
        if not isinstance(general_name, x509.UniformResourceIdentifier):
            continue
        uri = str(general_name.value)
        if uri.startswith("spiffe://agentlens/"):
            return parse_spiffe_uri(uri)
    raise IdentityError("client certificate URI SAN does not contain an Agent Lens SPIFFE ID")


def _set_string_attribute(attributes: Any, key: str, value: str) -> None:
    for item in attributes:
        if item.key == key:
            item.value.CopyFrom(AnyValue(string_value=value))
            return
    attributes.append(KeyValue(key=key, value=AnyValue(string_value=value)))


def overwrite_resource_identity(
    request: ExportTraceServiceRequest, identity: CollectorIdentity
) -> ExportTraceServiceRequest:
    """Overwrite untrusted tenant/cluster claims with credential-derived identity."""
    for resource_span in request.resource_spans:
        attrs = resource_span.resource.attributes
        _set_string_attribute(attrs, TENANT_ATTR, identity.tenant_id)
        _set_string_attribute(attrs, CLUSTER_ATTR, identity.cluster_id)
        _set_string_attribute(attrs, IDENTITY_SOURCE_ATTR, "collector_credential")
    return request
