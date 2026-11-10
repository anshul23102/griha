"""Central constants. Everything that is a business assumption lives here or in policy/*.yaml."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts"
POLICY_PATH = ROOT / "policy" / "v1.yaml"
DATA_DIR = Path(os.environ.get("GRIHA_DATA_DIR", ROOT / "data"))
AUDIT_PATH = DATA_DIR / "audit.db"     # SQLite; an older audit.jsonl in the same folder is imported once

ENGINE_VERSION = "1.4.0"          # bump when decision logic, compliance wording or output shape changes; recorded with every decision and checked on replay
RETENTION_YEARS = 5      # NBFC KYC Directions 2025 para 47(1), (2): five years from the transaction / after the business relationship ends
RIGHTS_RESPONSE_DAYS = 90   # DPDP Rules 2025 rule 14(3): grievance response within a reasonable period not exceeding ninety days
RETENTION_HOLD = os.getenv("GRIHA_RETENTION_HOLD", "1") == "1"   # 0 only where every record is synthetic (local development, the public demo)
COOLING_OFF_DAYS = 3            # ILLUSTRATIVE: the lender's Board sets this (Digital Lending Directions 2025 para 10: not less than one day)
AS_OF_DEFAULT = (2026, 11, 1)   # fixed evaluation date keeps synthetic cases reproducible
# Rate assumptions, each anchored to a published figure (see griha/sources.py and the Data sources page).
REPO_RATE = 0.055               # RBI policy repo rate: raised 25 bp on 7 Oct 2026 (MPC minutes published 21 Oct 2026)
LENDER_SPREAD = 0.040           # ILLUSTRATIVE lender spread over the repo benchmark (a lender sets its own)
STRESS_BUFFER = 0.020           # ILLUSTRATIVE stress buffer used to size eligibility
BASE_RATE = round(REPO_RATE + LENDER_SPREAD, 6)       # 9.5%: benchmark-linked base rate, moves one for one with the repo rate
UW_RATE = round(BASE_RATE + STRESS_BUFFER, 6)         # 11.5%: stress rate used for FOIR/eligibility (not the offer rate)
PROC_FEE_PCT = 0.01             # processing fee, included in APR
SELF_EMP_MARGIN = 0.30          # assumed net margin on business credits (replace with ITR/GST data)
CO_APPLICANT_HAIRCUT = 0.70     # share of co-applicant income counted
