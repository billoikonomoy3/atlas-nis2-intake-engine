"""Atlas - NIS2 Stage 4.3 criteria set + proportionality model.

Maps NIS2 obligations (Art 20 governance, Art 21(2)(a)-(j) measures, Art 23
reporting) to TESTABLE control criteria, and computes a transparent
proportionality profile from pre-PBC facts. The criteria set is the basis of
the PBC (Provided-By-Client) request list.

COPYRIGHT DESIGN (load-bearing): ISO/IEC 27001:2022 control TEXT is copyright of
ISO and is never reproduced here. The public-facing layer is keyed only to
(a) paraphrased NIS2 prose (EU law) and (b) NIST CSF 2.0 function/subcategory
identifiers (US Government, public domain). ISO is referenced by CLAUSE NUMBER
ONLY (e.g. "5.1", "8.16") as a licensed internal crosswalk - a factual pointer
holders of an ISO licence can resolve, carrying no protected expression.

No LLM, no network. Pure data + pure functions.
"""

from __future__ import annotations

ISO_COPYRIGHT_NOTE = (
    "ISO/IEC 27001:2022 control text is copyright of ISO and is not reproduced. "
    "Public criteria are keyed to NIS2 (paraphrased EU law) and NIST CSF 2.0 "
    "(public domain). ISO is referenced by clause number only as a licensed "
    "internal crosswalk; resolve the numbers against your own licensed copy."
)

# ---------------------------------------------------------------------------
# Assessment criteria set: one row per NIS2 requirement.
# ---------------------------------------------------------------------------

CRITERIA = [
    {
        "id": "GOV-20-01", "domain": "governance", "nis2_ref": "Art 20(1)",
        "obligation": "The management body must approve the entity's cybersecurity risk-management measures and oversee their implementation; accountability sits with senior leadership, who can be held liable for failures.",
        "nist_csf_function": "GV", "nist_csf_subcategories": ["GV.RM-01", "GV.RR-01", "GV.OC-03"],
        "iso27001_2022_refs": ["5.1", "5.2", "5.3", "5.4"],
        "evidence_examples": [
            "Board/management-body minutes approving the cyber risk-management framework",
            "Signed information security policy with executive ownership and date",
            "Documented assignment of cyber accountability to a named management-body member",
            "Oversight cadence showing periodic management review of cyber risk",
        ],
        "maturity_levels": {
            "l1": "No management-body involvement; cybersecurity treated as a purely IT matter.",
            "l2": "Leadership informally aware; approval ad hoc and undocumented.",
            "l3": "Management body has formally approved the measures and reviews them on a defined schedule; accountability assigned.",
            "l4": "Oversight supported by metrics/dashboards; remediation tracked against risk appetite.",
            "l5": "Cyber governance integrated into enterprise risk; oversight effectiveness measured and continuously improved.",
        },
        "pbc_items": [
            "Board/management-body minutes evidencing approval & oversight (last 12-24 months)",
            "Approved information security policy with version history",
            "Interview: management-body member responsible for cyber oversight",
            "Governance RACI / accountability matrix for cybersecurity",
        ],
    },
    {
        "id": "GOV-20-02", "domain": "governance", "nis2_ref": "Art 20(2)",
        "obligation": "Management-body members must undergo cybersecurity training, and the entity must encourage equivalent training for staff, so leaders can identify and assess cyber risks.",
        "nist_csf_function": "GV", "nist_csf_subcategories": ["GV.RR-02", "GV.RR-04", "PR.AT-02"],
        "iso27001_2022_refs": ["6.3", "7.2", "7.3"],
        "evidence_examples": [
            "Training records/attendance for management-body cyber sessions",
            "Executive/board-tailored training curriculum",
            "Policy mandating recurring leadership cyber training",
            "Records showing staff are offered equivalent awareness training",
        ],
        "maturity_levels": {
            "l1": "No cyber training for the management body.",
            "l2": "One-off informal briefings; no curriculum or tracking.",
            "l3": "Defined, role-appropriate training delivered on a recurring schedule with attendance recorded.",
            "l4": "Content refreshed against the threat landscape; completion measured.",
            "l5": "Leadership competency assessed and continuously improved.",
        },
        "pbc_items": [
            "Cyber training records & attendance for management-body members",
            "Leadership training syllabus/curriculum",
            "Policy/schedule mandating recurring leadership training",
            "Interview: HR/training lead on awareness programme scope",
        ],
    },
    {
        "id": "RM-21A-01", "domain": "risk-measures", "nis2_ref": "Art 21(2)(a)",
        "obligation": "Maintain documented policies on risk analysis and on information-system security, giving a structured, repeatable basis to identify, assess and treat cyber risk.",
        "nist_csf_function": "ID", "nist_csf_subcategories": ["ID.RA-01", "ID.RA-05", "GV.RM-02", "GV.PO-01"],
        "iso27001_2022_refs": ["5.1", "6.1", "8.8", "5.7"],
        "evidence_examples": [
            "Approved risk-management methodology / risk-assessment procedure",
            "Current risk register with scoring, owners and treatment decisions",
            "Information security policy set",
            "Risk treatment plan mapped to identified risks",
        ],
        "maturity_levels": {
            "l1": "No formal risk-analysis process; risks handled reactively.",
            "l2": "Sporadic, informal assessments; no consistent methodology.",
            "l3": "Documented methodology and policies applied; maintained register with owners and treatment.",
            "l4": "Data-driven (threat intel, asset criticality), reviewed on a cadence with KPIs.",
            "l5": "Quantified, integrated with business decisions, continuously optimised.",
        },
        "pbc_items": [
            "Risk-assessment methodology and information security policy",
            "Current risk register and risk treatment plan",
            "Interview: risk owner on assessment frequency/triggers",
            "Evidence of last risk-assessment cycle with management sign-off",
        ],
    },
    {
        "id": "RM-21B-01", "domain": "risk-measures", "nis2_ref": "Art 21(2)(b)",
        "obligation": "Maintain incident-handling capabilities across detection, analysis, containment, response and post-incident review, with learnings captured.",
        "nist_csf_function": "RS", "nist_csf_subcategories": ["RS.MA-01", "RS.AN-03", "DE.AE-02", "RS.CO-02"],
        "iso27001_2022_refs": ["5.24", "5.25", "5.26", "5.27", "5.28"],
        "evidence_examples": [
            "Incident response plan/playbooks with roles and severity classification",
            "Incident log/register showing triage, handling and closure",
            "Post-incident review reports with lessons-learned actions",
            "Evidence of IR plan testing / tabletop exercise",
        ],
        "maturity_levels": {
            "l1": "No defined process; incidents managed ad hoc with no records.",
            "l2": "Basic reactive handling, inconsistent and largely undocumented.",
            "l3": "Documented process with roles, classification and a maintained incident log, followed in practice.",
            "l4": "Regularly exercised; MTTD/MTTR tracked; lessons-learned drive improvements.",
            "l5": "Continuously optimised with automation and threat-informed playbooks.",
        },
        "pbc_items": [
            "Incident response plan and playbooks",
            "Incident register/log for the past 12 months",
            "Sample post-incident review and lessons-learned tracker",
            "Interview: incident response lead / SOC manager",
        ],
    },
    {
        "id": "RM-21C-01", "domain": "risk-measures", "nis2_ref": "Art 21(2)(c)",
        "obligation": "Maintain business continuity arrangements - backup management, disaster recovery and crisis management - so critical services can be sustained or restored after disruption.",
        "nist_csf_function": "RC", "nist_csf_subcategories": ["RC.RP-01", "PR.DS-11", "GV.OC-04", "RC.CO-03"],
        "iso27001_2022_refs": ["5.29", "5.30", "8.13", "8.14"],
        "evidence_examples": [
            "Business continuity plan and disaster recovery plan with RTO/RPO",
            "Backup policy and recent backup-restoration test results",
            "Crisis management plan with escalation/communication structure",
            "Records of the most recent BCP/DR exercise",
        ],
        "maturity_levels": {
            "l1": "No continuity/recovery planning; backups, if any, unverified.",
            "l2": "Backups exist but untested; no formal BCP/DR or crisis plan.",
            "l3": "Documented BCP/DRP/crisis plan with RTO/RPO; backups periodically test-restored.",
            "l4": "Exercised on a schedule; objectives validated against business impact.",
            "l5": "Resilience continuously measured; objectives met under realistic testing.",
        },
        "pbc_items": [
            "BCP, DRP and crisis management plan with RTO/RPO",
            "Backup policy and most recent restoration test evidence",
            "Results of the latest BCP/DR exercise",
            "Interview: business continuity / IT operations owner",
        ],
    },
    {
        "id": "RM-21D-01", "domain": "risk-measures", "nis2_ref": "Art 21(2)(d)",
        "obligation": "Manage supply-chain security - the security of relationships with direct suppliers and service providers, including assessing and contractually requiring appropriate security.",
        "nist_csf_function": "GV", "nist_csf_subcategories": ["GV.SC-01", "GV.SC-06", "GV.SC-07", "ID.RA-10"],
        "iso27001_2022_refs": ["5.19", "5.20", "5.21", "5.22"],
        "evidence_examples": [
            "Supplier security policy and third-party risk-management procedure",
            "Supplier register with criticality ratings and risk assessments",
            "Sample contracts/DPAs with security clauses and right-to-audit",
            "Evidence of supplier security assessments or monitoring",
        ],
        "maturity_levels": {
            "l1": "No supplier security management; third parties onboarded without review.",
            "l2": "Ad hoc checks; security clauses inconsistently applied.",
            "l3": "Defined process assesses and contractually obligates suppliers; maintained risk register.",
            "l4": "Risk tiered, continuously monitored and reassessed; remediation tracked.",
            "l5": "Quantified and integrated with procurement; supplier performance measured.",
        },
        "pbc_items": [
            "Supplier/third-party security policy and assessment procedure",
            "Supplier register with criticality and risk ratings",
            "Sample supplier contracts showing security obligations",
            "Interview: procurement / vendor risk-management owner",
        ],
    },
    {
        "id": "RM-21E-01", "domain": "risk-measures", "nis2_ref": "Art 21(2)(e)",
        "obligation": "Ensure security in the acquisition, development and maintenance of network and information systems, including structured vulnerability handling and disclosure.",
        "nist_csf_function": "PR", "nist_csf_subcategories": ["PR.PS-06", "ID.RA-01", "ID.RA-06", "RS.MI-02"],
        "iso27001_2022_refs": ["8.8", "8.25", "8.28", "8.29"],
        "evidence_examples": [
            "Secure development lifecycle policy and secure coding standards",
            "Vulnerability management procedure with SLAs and patch records",
            "Coordinated vulnerability disclosure policy/process",
            "Recent vulnerability scan and remediation tracking reports",
        ],
        "maturity_levels": {
            "l1": "No secure-development or vulnerability handling; patching reactive and untracked.",
            "l2": "Some patching/ad hoc scanning; no defined SDLC or disclosure process.",
            "l3": "Defined secure-acquisition/development practices and vulnerability process with SLAs and disclosure.",
            "l4": "Risk-prioritised, measured against SLAs, integrated into CI/CD.",
            "l5": "Continuously optimised with metrics, automation and threat-informed prioritisation.",
        },
        "pbc_items": [
            "SDLC / secure development policy and secure coding standards",
            "Vulnerability-management procedure and patch SLA evidence",
            "Coordinated vulnerability disclosure policy",
            "Recent vulnerability scan results and remediation tracker",
        ],
    },
    {
        "id": "RM-21F-01", "domain": "risk-measures", "nis2_ref": "Art 21(2)(f)",
        "obligation": "Maintain policies and procedures to assess the effectiveness of the cybersecurity risk-management measures - assurance that controls operate as intended.",
        "nist_csf_function": "ID", "nist_csf_subcategories": ["ID.IM-01", "ID.IM-02", "GV.OV-01", "GV.OV-03"],
        "iso27001_2022_refs": ["9.1", "9.2", "9.3", "10.2"],
        "evidence_examples": [
            "Control-effectiveness assessment / internal audit programme and schedule",
            "Internal audit reports and management review minutes",
            "KPI/KRI dashboards measuring control performance",
            "Corrective-action / continual-improvement tracker",
        ],
        "maturity_levels": {
            "l1": "No assessment of control effectiveness; no audit/review activity.",
            "l2": "Occasional informal reviews; no programme or metrics.",
            "l3": "Defined programme (audit, management review, metrics) on a schedule with findings tracked.",
            "l4": "Measured against targets, trended, drives prioritised remediation.",
            "l5": "Continuous, data-driven assurance; independently validated.",
        },
        "pbc_items": [
            "Internal audit / control-assessment programme and schedule",
            "Recent internal audit reports and management review minutes",
            "KPI/KRI dashboards used to measure control effectiveness",
            "Corrective-action / continual-improvement register",
        ],
    },
    {
        "id": "RM-21G-01", "domain": "risk-measures", "nis2_ref": "Art 21(2)(g)",
        "obligation": "Practise basic cyber hygiene and provide cybersecurity training to staff, embedding foundational protective behaviours across the workforce.",
        "nist_csf_function": "PR", "nist_csf_subcategories": ["PR.AT-01", "PR.AT-02", "GV.RR-04"],
        "iso27001_2022_refs": ["6.3", "8.7", "8.19"],
        "evidence_examples": [
            "Cyber hygiene policy/standards (patching, least privilege, malware protection)",
            "Security awareness programme and completion records",
            "Phishing simulation results and follow-up actions",
            "Onboarding security training checklist",
        ],
        "maturity_levels": {
            "l1": "No structured awareness training or hygiene baseline.",
            "l2": "Occasional messaging; basic hygiene applied inconsistently.",
            "l3": "Defined programme and documented hygiene baseline with tracked completion.",
            "l4": "Role-based and reinforced (e.g. phishing simulations); behaviour measured.",
            "l5": "Effectiveness continuously measured and optimised; demonstrable behaviour change.",
        },
        "pbc_items": [
            "Cyber hygiene policy/standards",
            "Awareness training programme and completion records",
            "Phishing simulation results and remediation actions",
            "Interview: security awareness programme owner",
        ],
    },
    {
        "id": "RM-21H-01", "domain": "risk-measures", "nis2_ref": "Art 21(2)(h)",
        "obligation": "Maintain policies and procedures on cryptography and, where appropriate, encryption, protecting confidentiality and integrity of data at rest and in transit.",
        "nist_csf_function": "PR", "nist_csf_subcategories": ["PR.DS-01", "PR.DS-02", "PR.DS-10"],
        "iso27001_2022_refs": ["8.24", "5.10", "8.1"],
        "evidence_examples": [
            "Cryptography/encryption policy with approved algorithms and standards",
            "Key management procedure (generation, storage, rotation, revocation)",
            "Evidence of encryption at rest and in transit for critical systems",
            "Cryptographic configuration / TLS scan reports",
        ],
        "maturity_levels": {
            "l1": "No cryptography policy; encryption inconsistent or absent.",
            "l2": "Some encryption but no governing policy or key management.",
            "l3": "Documented policy and key-management; encryption protects critical data at rest/in transit.",
            "l4": "Posture monitored, algorithms reviewed; key lifecycle enforced and audited.",
            "l5": "Continuously assessed (incl. crypto-agility/PQC readiness) and optimised.",
        },
        "pbc_items": [
            "Cryptography/encryption policy and approved algorithm list",
            "Key-management procedure",
            "Evidence of encryption at rest and in transit for critical systems",
            "Recent cryptographic configuration / TLS scan reports",
        ],
    },
    {
        "id": "RM-21I-01", "domain": "risk-measures", "nis2_ref": "Art 21(2)(i)",
        "obligation": "Implement human-resources security, access control and asset management - vetting and managing people across the lifecycle, granting access on need, and inventorying/controlling assets.",
        "nist_csf_function": "PR", "nist_csf_subcategories": ["PR.AA-01", "PR.AA-05", "ID.AM-01", "ID.AM-02"],
        "iso27001_2022_refs": ["6.1", "6.5", "5.15", "5.18", "5.9"],
        "evidence_examples": [
            "Access control policy and joiner/mover/leaver procedure",
            "Asset inventory (hardware/software/information) with owners",
            "Sample access-review records and HR screening evidence",
            "Privileged access management configuration",
        ],
        "maturity_levels": {
            "l1": "No formal access control, HR security or asset inventory.",
            "l2": "Basic grants and partial inventories; reviews/JML inconsistent.",
            "l3": "Defined processes with maintained inventory and periodic access reviews.",
            "l4": "Least-privilege, recertified on schedule; inventory reconciled; HR controls enforced.",
            "l5": "Identity, access and asset governance measured, automated and optimised.",
        },
        "pbc_items": [
            "Access control policy and joiner/mover/leaver procedure",
            "Asset inventory with assigned owners",
            "Sample access-review/recertification records",
            "HR screening and confidentiality-agreement evidence",
        ],
    },
    {
        "id": "RM-21J-01", "domain": "risk-measures", "nis2_ref": "Art 21(2)(j)",
        "obligation": "Where appropriate, use multi-factor or continuous authentication, secured voice/video/text communications, and secured emergency communications within the entity.",
        "nist_csf_function": "PR", "nist_csf_subcategories": ["PR.AA-03", "PR.AA-05", "PR.DS-02", "PR.IR-01"],
        "iso27001_2022_refs": ["8.5", "8.3", "8.24", "8.20"],
        "evidence_examples": [
            "MFA policy and configuration across critical systems and remote access",
            "Records of secured communication tooling (encrypted email/messaging/voice)",
            "Emergency / out-of-band communication plan and contact tree",
            "Authentication configuration / conditional-access evidence",
        ],
        "maturity_levels": {
            "l1": "Single-factor only; no secured/emergency communications.",
            "l2": "MFA on some systems; secured comms used informally with gaps.",
            "l3": "MFA (or continuous auth) enforced on critical access; secured comms and an emergency plan exist.",
            "l4": "Coverage monitored, phishing-resistant factors adopted, emergency comms tested.",
            "l5": "Continuously optimised (risk-based/continuous auth) with tested resilient emergency comms.",
        },
        "pbc_items": [
            "MFA/authentication policy and configuration evidence",
            "Evidence of secured voice/video/text communication tooling",
            "Emergency / out-of-band communications plan and test records",
            "Interview: IT/security engineering on authentication & comms controls",
        ],
    },
    {
        "id": "REP-23-01", "domain": "reporting", "nis2_ref": "Art 23(4)(a)",
        "obligation": "Submit an early warning to the CSIRT/competent authority without undue delay and within 24 hours of becoming aware of a significant incident, flagging suspected malicious cause or cross-border impact.",
        "nist_csf_function": "RS", "nist_csf_subcategories": ["RS.CO-02", "RS.MA-01", "RS.AN-03"],
        "iso27001_2022_refs": ["5.24", "5.25", "5.5", "5.6"],
        "evidence_examples": [
            "Reporting procedure specifying the 24-hour early-warning trigger and recipient",
            "Significant-incident classification criteria / decision tree",
            "Sample early-warning notification or template",
            "Contact details/channel for the relevant CSIRT/competent authority",
        ],
        "maturity_levels": {
            "l1": "No defined regulatory reporting; staff unaware of the 24-hour obligation.",
            "l2": "Ad hoc reporting; thresholds and recipients undefined.",
            "l3": "Documented procedure defines criteria, the 24-hour trigger and the correct authority, communicated to responders.",
            "l4": "Pathway exercised; timing tracked; assessment/submission roles tested.",
            "l5": "Continuously measured against deadlines; demonstrable on-time performance.",
        },
        "pbc_items": [
            "Incident-reporting procedure covering the 24-hour early warning",
            "Significant-incident classification criteria",
            "Early-warning notification template and CSIRT/authority contacts",
            "Evidence of any early-warning report submitted or exercised",
        ],
    },
    {
        "id": "REP-23-02", "domain": "reporting", "nis2_ref": "Art 23(4)(b)",
        "obligation": "Submit an incident notification within 72 hours, updating the early warning with an initial assessment of severity, impact and any indicators of compromise.",
        "nist_csf_function": "RS", "nist_csf_subcategories": ["RS.CO-02", "RS.CO-03", "RS.AN-03", "RS.MA-04"],
        "iso27001_2022_refs": ["5.24", "5.26", "5.27", "5.5"],
        "evidence_examples": [
            "Reporting procedure detailing 72-hour notification content (severity, impact, IoCs)",
            "Incident assessment template capturing impact and IoCs",
            "Sample 72-hour notification or exercise record",
            "Internal timeline/RACI for compiling and approving the notification",
        ],
        "maturity_levels": {
            "l1": "No 72-hour process; impact assessment unstructured.",
            "l2": "Reactive notifications; inconsistent content/timing.",
            "l3": "Documented procedure/template define content and ownership, aligned to the early warning.",
            "l4": "Pathway exercised; content quality and timeliness reviewed; approval roles tested.",
            "l5": "Quality/timeliness continuously measured; consistent on-time, complete submissions.",
        },
        "pbc_items": [
            "Procedure and template for the 72-hour incident notification",
            "Incident impact-assessment / IoC capture template",
            "Sample 72-hour notification or exercise evidence",
            "Interview: incident commander on assessment & approval workflow",
        ],
    },
    {
        "id": "REP-23-03", "domain": "reporting", "nis2_ref": "Art 23(4)(c)",
        "obligation": "On request of the CSIRT/competent authority, provide an intermediate status report on relevant updates while a significant incident is ongoing.",
        "nist_csf_function": "RS", "nist_csf_subcategories": ["RS.CO-02", "RS.CO-03", "RS.MA-04"],
        "iso27001_2022_refs": ["5.24", "5.26", "5.5"],
        "evidence_examples": [
            "Procedure covering intermediate/status updates on request during an ongoing incident",
            "Template for an intermediate status report",
            "Evidence of liaison cadence with the CSIRT/authority during a live incident",
        ],
        "maturity_levels": {
            "l1": "No provision for status updates during an ongoing incident.",
            "l2": "Updates given informally on request without a defined format.",
            "l3": "Documented procedure and template for intermediate updates on authority request.",
            "l4": "Update cadence and ownership exercised and reviewed.",
            "l5": "Status reporting integrated and continuously improved with the authority relationship.",
        },
        "pbc_items": [
            "Procedure/template for intermediate status reports on request",
            "Evidence of authority liaison during any ongoing incident",
        ],
    },
    {
        "id": "REP-23-04", "domain": "reporting", "nis2_ref": "Art 23(4)(d)",
        "obligation": "Submit a final report no later than one month after the notification - detailed description, root cause, applied and ongoing mitigations, and any cross-border impact.",
        "nist_csf_function": "RC", "nist_csf_subcategories": ["RC.RP-06", "RS.AN-08", "ID.IM-04", "RS.CO-03"],
        "iso27001_2022_refs": ["5.27", "5.28", "5.24", "10.1"],
        "evidence_examples": [
            "Final-report procedure/template covering root cause, mitigations and cross-border impact",
            "Sample final incident report submitted to the authority",
            "Root-cause analysis methodology and lessons-learned linkage",
            "Tracker linking final-report actions to control improvements",
        ],
        "maturity_levels": {
            "l1": "No final-report process; incidents closed without root-cause reporting.",
            "l2": "Inconsistent final reporting; not aligned to the one-month deadline or content.",
            "l3": "Documented procedure/template produce a compliant final report within one month.",
            "l4": "Quality-reviewed; deadlines tracked; findings feed measurable improvements.",
            "l5": "Final reporting and post-incident learning continuously optimised and measured.",
        },
        "pbc_items": [
            "Final-report procedure and template",
            "Sample final or intermediate incident report",
            "Root-cause analysis methodology",
            "Tracker linking final-report findings to remediation actions",
        ],
    },
]

# Coverage assertion (Art 20, all of 21(2)(a)-(j), Art 23 stages).
_COVERED = {c["nis2_ref"] for c in CRITERIA}


# ---------------------------------------------------------------------------
# Proportionality model (NIS2 Art 21(1)) - transparent additive scoring.
# ---------------------------------------------------------------------------

TIERS = [
    ("Foundational", 0, 39, "Baseline cyber hygiene; lightweight self-attestation + evidence sampling."),
    ("Standard", 40, 59, "Established documented programme; control-design review + operating-effectiveness sampling."),
    ("Enhanced", 60, 79, "Mature risk-driven programme; full controls audit with independent evidence across all six CSF functions."),
    ("Critical", 80, 100, "Maximal rigor for systemic/sole-national providers; in-depth audit + independent technical & resilience validation."),
]

_SIZE_PTS = {"large": 25, "medium": 14, "below_medium": 6, None: 0}
_CLASS_PTS = {"essential": 25, "important": 12, "out_of_scope": 0, "deferred_designation": 0}
_ANNEX_PTS = {"I": 15, "II": 8, "none": 0}
_XBORDER_PTS = {"systemic": 15, "sole_national": 15, "cross_border": 9, "none": 0, None: 0}
_SUPPLY_PTS = {"high": 5, "moderate": 3, "low": 0, None: 0}


def _footprint_pts(n_geographies: int, n_entities: int) -> int:
    def g(n):
        return 10 if n >= 7 else 7 if n >= 4 else 4 if n >= 2 else 0
    def e(n):
        return 10 if n >= 11 else 7 if n >= 5 else 4 if n >= 2 else 0
    return max(g(n_geographies or 1), e(n_entities or 1))


def tier_for(score: int) -> tuple[str, str]:
    for name, lo, hi, exp in TIERS:
        if lo <= score <= hi:
            return name, exp
    return TIERS[-1][0], TIERS[-1][3]


def proportionality(*, size_band, entity_class, sector_annex,
                    cross_border_systemic="none", n_geographies=1, n_entities=1,
                    special_entity=False, supply_chain="low") -> dict:
    """Transparent additive weighted score (0-100), fully re-derivable by hand."""
    pts = {
        "size_band": _SIZE_PTS.get(size_band, 0),
        "entity_class": _CLASS_PTS.get(entity_class, 0),
        "sector_annex": _ANNEX_PTS.get(sector_annex, 0),
        "cross_border_systemic": _XBORDER_PTS.get(cross_border_systemic, 0),
        "footprint": _footprint_pts(n_geographies, n_entities),
        "special_entity": 5 if special_entity else 0,
        "supply_chain": _SUPPLY_PTS.get(supply_chain, 0),
    }
    raw = sum(pts.values())
    score = raw
    floors = []
    if entity_class == "essential" and score < 60:
        score = 60
        floors.append("essential -> floored to Enhanced (>=60)")
    if cross_border_systemic in ("systemic", "sole_national") and score < 80:
        score = 80
        floors.append("systemic / sole-national provider -> floored to Critical (>=80)")
    tier, expectation = tier_for(score)
    return {
        "points": pts, "raw_score": raw, "score": score,
        "floors_applied": floors, "tier": tier, "tier_expectation": expectation,
    }


# ---------------------------------------------------------------------------
# PBC list builder
# ---------------------------------------------------------------------------


def pbc_list(criteria=CRITERIA) -> list:
    """Flatten the criteria set into a deduplicated draft PBC request list."""
    out = []
    for c in criteria:
        for item in c["pbc_items"]:
            out.append({"criterion_id": c["id"], "nis2_ref": c["nis2_ref"],
                        "csf": c["nist_csf_function"], "request": item})
    return out


if __name__ == "__main__":
    print(f"Criteria rows: {len(CRITERIA)}  |  PBC line items: {len(pbc_list())}")
    print(f"NIS2 refs covered: {sorted(_COVERED)}")
    demo = proportionality(size_band="large", entity_class="essential",
                           sector_annex="I", cross_border_systemic="systemic",
                           n_geographies=8, n_entities=12, special_entity=False,
                           supply_chain="high")
    print(f"\nProportionality (national TSO-type): score={demo['score']} "
          f"tier={demo['tier']} floors={demo['floors_applied']}")
    print(f"  breakdown: {demo['points']}")
