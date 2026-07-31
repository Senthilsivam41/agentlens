{{- define "agentlens-platform.fullname" -}}
{{ printf "%s-agentlens" .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

