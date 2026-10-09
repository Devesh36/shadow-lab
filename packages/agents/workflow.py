import asyncio
import re
from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph

from packages.agents.hypotheses import generate
from packages.agents.llm import prioritize
from packages.analyzers.nextjs import discover
from packages.core.models import FindingState, TestPlan
from packages.execution.gateway import Gateway
from packages.policies.engine import PolicyEngine
from packages.scanners.tools import osv, semgrep


class Investigation(TypedDict, total=False):
    surface: dict
    scanners: dict
    hypotheses: list[dict]
    findings: list[str]


class Workflow:
    def __init__(self, store, scan_id, cancelled=None):
        self.store = store
        self.scan_id = scan_id
        self.cancelled = cancelled or asyncio.Event()
        self.scan = store.get("scan", scan_id)
        self.settings = store.settings()
        self.root = Path(store.get("repository", self.scan["repository_id"])["path"])

    def stage(self, name, message):
        if self.cancelled.is_set():
            raise asyncio.CancelledError
        self.store.put("scan", {"stage": name}, id=self.scan_id)
        self.store.event(self.scan_id, name, message)

    async def recon(self, state):
        self.stage("reconnaissance", "Parsing source routes and running available scanners")
        surface = await asyncio.to_thread(discover, self.root)
        static = await semgrep(self.root)
        dependencies = await osv(self.root) if "dependency" in self.settings.categories else {
            "status": "disabled", "findings": [], "reason": "Dependency category disabled by operator"}
        scanners = {"semgrep": static, "osv": dependencies}
        self.store.put("scan", {"surface": surface, "scanners": scanners, "commit": surface["commit"]}, id=self.scan_id)
        return {"surface": surface, "scanners": scanners}

    async def hypothesize(self, state):
        self.stage("hypotheses", "Generating evidence-linked hypotheses; these are not confirmed findings")
        hypotheses = [h.model_dump() for h in generate(state["surface"], state["scanners"]["semgrep"])
                      if h.category in self.settings.categories][:self.settings.max_hypotheses]
        for hit in state["scanners"]["osv"].get("findings", []):
            if "dependency" in self.settings.categories and len(hypotheses) < self.settings.max_hypotheses:
                hypotheses.append({"category": "dependency", "endpoint": "dependencies", "sources": [],
                                   "title": hit["id"], "observations": [hit["summary"]],
                                   "conditions": ["Review affected version and reachability"],
                                   "expected": "Dependencies have no known advisories", "severity": "medium", "cwe": None})
        if self.settings.llm_enabled:
            # One bounded provider call; no shell, network, or policy override is exposed.
            hypotheses = await prioritize(hypotheses, self.settings)
        self.store.put("scan", {"hypotheses": hypotheses, "engine": "llm-prioritized" if self.settings.llm_enabled else "rule-based"}, id=self.scan_id)
        return {"hypotheses": hypotheses}

    def concrete_path(self, endpoint):
        if "[" not in endpoint:
            return endpoint
        fixture = self.settings.fixture
        pattern = "^" + re.sub(r"\\\[[^]]+\\\]", "[^/]+", re.escape(endpoint)) + "$"
        if fixture and re.fullmatch(pattern, fixture.endpoint):
            return fixture.endpoint
        return None

    async def plan(self, state):
        self.stage("planning", "Selecting GET-only tests within scope and request budgets")
        ids = []
        for h in state["hypotheses"]:
            path = self.concrete_path(h["endpoint"])
            plans = []
            if path and path.startswith("/"):
                if h["category"] == "bola" and self.settings.fixture:
                    plans = [TestPlan(category="bola", path=path, identity="owner"),
                             TestPlan(category="bola", path=self.settings.fixture.other_endpoint, identity="other"),
                             TestPlan(category="bola", path=path, identity="other")]
                elif h["category"] == "authentication" and self.settings.fixture:
                    plans = [TestPlan(category="authentication", path=path, identity=i) for i in ("owner", "anonymous")]
                elif h["category"] in ("exposure", "headers"):
                    plans = [TestPlan(category=h["category"], path=path,
                                      identity="owner" if self.settings.fixture and h["category"] == "exposure" else "anonymous")]
            finding = self.store.put("finding", {**h, "state": FindingState.PLANNED if plans else FindingState.DISCOVERED,
                "plans": [p.model_dump() for p in plans], "evidence": [], "root_cause": h["observations"][0],
                "remediation": remediation(h["category"]), "validation": "Not yet tested"}, parent_id=self.scan_id)
            ids.append(finding["id"])
        return {"findings": ids}

    async def validate(self, state):
        self.stage("validation", "Executing typed tests through the policy gateway")
        if not self.scan["dynamic"]:
            for id in state["findings"]:
                self.store.put("finding", {"state": FindingState.INCONCLUSIVE,
                    "validation": "Static hypothesis; dynamic validation was not requested"}, id=id)
            return {}
        policy = PolicyEngine(self.settings, self.scan["target"],
            audit=lambda **details: self.store.event(self.scan_id, "policy", "Execution policy decision", **details))
        gateway = Gateway(policy, self.cancelled)
        for id in state["findings"]:
            if self.cancelled.is_set():
                raise asyncio.CancelledError
            finding = self.store.get("finding", id)
            if not finding["plans"]:
                self.store.put("finding", {"state": FindingState.INCONCLUSIVE,
                    "validation": "No bounded runtime test or required fixture is unavailable"}, id=id)
                continue
            self.store.put("finding", {"state": FindingState.TESTING}, id=id)
            evidence = []
            try:
                for plan in finding["plans"]:
                    result = await gateway.request(TestPlan.model_validate(plan))
                    record = self.store.put("execution", result, parent_id=self.scan_id)
                    evidence.append({**result, "execution_id": record["id"]})
                status, explanation = classify(finding["category"], evidence)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                status, explanation = FindingState.INCONCLUSIVE, f"{type(exc).__name__}: test could not complete"
                self.store.event(self.scan_id, "validation", "Test did not complete", error_type=type(exc).__name__)
            self.store.put("finding", {"state": status, "evidence": evidence, "validation": explanation}, id=id)
            self.store.event(self.scan_id, "evidence", explanation, finding_id=id, state=status)
        return {}

    async def report(self, state):
        self.stage("reporting", "Persisting findings and completing the investigation")
        self.store.put("scan", {"status": "completed", "stage": "completed"}, id=self.scan_id)
        return {}

    async def run(self):
        self.store.put("scan", {"status": "running"}, id=self.scan_id)
        try:
            async with AsyncSqliteSaver.from_conn_string(str(self.store.data_dir / "checkpoints.db")) as saver:
                graph = StateGraph(Investigation)
                for name in ("recon", "hypothesize", "plan", "validate", "report"):
                    graph.add_node(name, getattr(self, name))
                for left, right in zip([START, "recon", "hypothesize", "plan", "validate", "report"],
                                       ["recon", "hypothesize", "plan", "validate", "report", END]):
                    graph.add_edge(left, right)
                async with asyncio.timeout(self.settings.scan_timeout_seconds):
                    await graph.compile(checkpointer=saver).ainvoke({}, {"configurable": {"thread_id": self.scan_id},
                                                                        "recursion_limit": 12})
        except asyncio.CancelledError:
            self.store.put("scan", {"status": "cancelled", "stage": "cancelled"}, id=self.scan_id)
            for finding in self.store.list("finding", self.scan_id):
                if finding["state"] == FindingState.TESTING:
                    self.store.put("finding", {"state": FindingState.INCONCLUSIVE,
                        "validation": "Scan cancelled during validation"}, id=finding["id"])
            self.store.event(self.scan_id, "cancelled", "Scan cancelled by operator")
        except Exception as exc:
            self.store.put("scan", {"status": "failed", "stage": "failed", "error": type(exc).__name__}, id=self.scan_id)
            self.store.event(self.scan_id, "failed", "Investigation failed", error_type=type(exc).__name__)


def classify(category, evidence):
    if category in ("bola", "authentication"):
        if category == "bola":
            owner, other_baseline, attempted = evidence
        else:
            owner, attempted = evidence
        # A valid owned resource is necessary; generic 200/HTML/error pages never establish BOLA.
        body = owner["body"]
        if owner["status"] != 200 or not isinstance(body, dict) or not body.get("id") or not body.get("ownerId"):
            return FindingState.INCONCLUSIVE, "Owner fixture did not return an identifiable owned resource"
        if category == "bola":
            baseline = other_baseline["body"]
            if (other_baseline["status"] != 200 or not isinstance(baseline, dict) or not baseline.get("id")
                    or not baseline.get("ownerId") or baseline["ownerId"] == body["ownerId"]):
                return FindingState.INCONCLUSIVE, "Second identity did not establish distinct ownership of its seeded resource"
        if attempted["status"] in (401, 403, 404):
            return FindingState.NOT_REPRODUCED, "The unauthorized identity was denied access"
        other = attempted["body"]
        if attempted["status"] == 200 and isinstance(other, dict) and all(
                other.get(k) == body[k] for k in ("id", "ownerId")):
            return FindingState.CONFIRMED, "Unauthorized identity retrieved the same seeded owned resource"
        return FindingState.INCONCLUSIVE, "Responses do not establish unauthorized access to the seeded record"
    if category == "exposure":
        if evidence[0]["status"] != 200:
            return FindingState.INCONCLUSIVE, "Endpoint did not return a successful response"
        if evidence[0]["sensitive_fields"]:
            return FindingState.CONFIRMED, "JSON response includes sensitive fields; values were redacted"
        return FindingState.NOT_REPRODUCED, "No sensitive fields were present in the tested response"
    if category == "headers":
        if evidence[0]["status"] >= 400:
            return FindingState.INCONCLUSIVE, "Endpoint did not return a successful response"
        required = ("content-security-policy", "x-content-type-options", "referrer-policy")
        missing = [key for key in required if not evidence[0]["security_headers"].get(key)]
        if missing:
            return FindingState.CONFIRMED, "Missing defense-in-depth headers: " + ", ".join(missing)
        return FindingState.NOT_REPRODUCED, "Required security headers were present"
    return FindingState.INCONCLUSIVE, "Static analysis needs manual validation"


def remediation(category):
    return {"bola": "Compare the authenticated user's ID against the resource owner before returning it.",
            "authentication": "Require a valid session before accessing the protected resource.",
            "exposure": "Project an explicit response allowlist; omit secrets and credential fields.",
            "headers": "Set CSP, X-Content-Type-Options, and Referrer-Policy appropriate to the application.",
            "injection": "Parameterize SQL and sanitize HTML at the rendering boundary.",
            "dependency": "Review advisory versions, upgrade, and run regression tests."}[category]
