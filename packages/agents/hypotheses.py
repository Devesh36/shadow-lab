from packages.core.models import Hypothesis, SourceRef


def generate(surface: dict, scanner: dict):
    hypotheses = []
    for route in surface["routes"]:
        if "GET" not in route["methods"] or not route["path"].startswith("/api/"):
            continue
        ref = SourceRef.model_validate(route["source"])
        common = {"endpoint": route["path"], "sources": [ref], "severity": "high"}
        if "[" in route["path"] and not route["ownership_observed"]:
            hypotheses.append(Hypothesis(**common, category="bola", cwe="CWE-639",
                title="Object access may omit ownership validation",
                observations=["Dynamic object route without a recognized ownership guard"],
                conditions=["Two synthetic identities", "Owner fixture returns the seeded record"],
                expected="A different identity receives 401, 403, or 404 instead of the owner's record"))
        if not route["authentication_observed"]:
            hypotheses.append(Hypothesis(**common, category="authentication", cwe="CWE-306",
                title="Endpoint may be missing authentication",
                observations=["No recognized authentication guard in this handler"],
                conditions=["Authenticated fixture response identifies a protected resource"],
                expected="An anonymous request receives 401, 403, or 404"))
        if route["sensitive_fields"]:
            hypotheses.append(Hypothesis(**{**common, "severity": "medium"}, category="exposure", cwe="CWE-200",
                title="Response may expose sensitive fields",
                observations=["Sensitive field names appear in the handler"],
                conditions=["A JSON response contains a sensitive field"],
                expected="Responses omit credential and secret fields"))
    for hit in scanner.get("findings", []):
        hypotheses.append(Hypothesis(category="injection", endpoint=hit["file"],
            sources=[SourceRef(file=hit["file"], line=hit["line"])], title=hit["message"],
            observations=["Semgrep rule: " + hit["rule"]], conditions=["Manual data-flow review"],
            expected="User-controlled inputs cross only validated or parameterized boundaries",
            severity="medium", cwe="CWE-89" if "sql" in hit["rule"] else "CWE-79"))
    if surface["routes"]:
        route = next((r for r in surface["routes"] if "[" not in r["path"]), surface["routes"][0])
        hypotheses.append(Hypothesis(category="headers", endpoint=route["path"],
            sources=[SourceRef.model_validate(route["source"])], title="Security headers may be missing",
            observations=["Runtime security headers require verification"], conditions=["Authorized GET response"],
            expected="Content-Type protection, CSP, and Referrer-Policy are present", severity="low", cwe="CWE-693"))
    return hypotheses
