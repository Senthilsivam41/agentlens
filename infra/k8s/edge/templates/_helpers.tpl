{{- define "agentlens-edge.name" -}}
agentlens-edge
{{- end }}

{{- define "agentlens-edge.fullname" -}}
{{ printf "%s-agentlens-edge" .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

