import re
import math
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

# ============================================================
# OCR CONFUSION MATRIX & CHARACTER SUBSTITUTION COSTS
# ============================================================

# Bi-directional pairs of commonly confused characters in license plate OCR
CONFUSION_PAIRS = {
    ('B', '8'): 0.25,
    ('8', 'B'): 0.25,
    ('O', '0'): 0.20,
    ('0', 'O'): 0.20,
    ('I', '1'): 0.25,
    ('1', 'I'): 0.25,
    ('L', '1'): 0.35,
    ('1', 'L'): 0.35,
    ('S', '5'): 0.25,
    ('5', 'S'): 0.25,
    ('Z', '2'): 0.30,
    ('2', 'Z'): 0.30,
    ('G', '6'): 0.30,
    ('6', 'G'): 0.30,
    ('Q', '0'): 0.30,
    ('0', 'Q'): 0.30,
    ('D', '0'): 0.35,
    ('0', 'D'): 0.35,
    ('A', '4'): 0.35,
    ('4', 'A'): 0.35,
    ('T', '7'): 0.35,
    ('7', 'T'): 0.35,
}

# Standard Indian State/UT 2-letter prefixes
INDIAN_STATES = {
    "AN", "AP", "AR", "AS", "BR", "CH", "CG", "DD", "DL", "DN", "GA", "GJ", "HR",
    "HP", "JH", "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN", "MP", "MZ", "NL",
    "OD", "OR", "PB", "PY", "RJ", "SK", "TN", "TR", "TS", "UK", "UA", "UP", "WB"
}

class IdentityEngine:
    """
    Confidence-Aware Vehicle Identity Engine.
    Handles noisy OCR outputs, resolves candidate identity distributions,
    and performs Bayesian confidence updates across multi-camera sightings.
    """

    def __init__(self):
        # In-memory candidate identity tracks: track_id -> VehicleTrackEntity
        self.active_tracks: Dict[str, Dict[str, Any]] = {}

    def clean_plate(self, text: str) -> str:
        """Strip non-alphanumeric chars and uppercase."""
        if not text:
            return ""
        return re.sub(r"[^A-Z0-9]", "", str(text).upper().strip())

    def get_substitution_cost(self, c1: str, c2: str) -> float:
        """Returns substitution cost between two characters."""
        if c1 == c2:
            return 0.0
        return CONFUSION_PAIRS.get((c1, c2), 1.0)

    def weighted_levenshtein(self, s1: str, s2: str) -> float:
        """
        Calculates weighted Levenshtein distance incorporating OCR confusion costs.
        Lower distance = higher similarity.
        """
        s1 = self.clean_plate(s1)
        s2 = self.clean_plate(s2)

        len1, len2 = len(s1), len(s2)
        if len1 == 0:
            return float(len2)
        if len2 == 0:
            return float(len1)

        dp = [[0.0] * (len2 + 1) for _ in range(len1 + 1)]

        for i in range(len1 + 1):
            dp[i][0] = float(i)
        for j in range(len2 + 1):
            dp[0][j] = float(j)

        for i in range(1, len1 + 1):
            c1 = s1[i - 1]
            for j in range(1, len2 + 1):
                c2 = s2[j - 1]
                cost = self.get_substitution_cost(c1, c2)
                dp[i][j] = min(
                    dp[i - 1][j] + 1.0,        # Deletion
                    dp[i][j - 1] + 1.0,        # Insertion
                    dp[i - 1][j - 1] + cost    # Substitution
                )

        return dp[len1][len2]

    def plate_similarity(self, s1: str, s2: str) -> float:
        """
        Returns normalized similarity score in range [0.0, 1.0].
        1.0 means identical, values > 0.80 indicate strong OCR variants.
        """
        s1 = self.clean_plate(s1)
        s2 = self.clean_plate(s2)
        if not s1 or not s2:
            return 0.0
        if s1 == s2:
            return 1.0

        max_len = max(len(s1), len(s2))
        dist = self.weighted_levenshtein(s1, s2)
        sim = max(0.0, 1.0 - (dist / max(max_len, 1)))
        return round(sim, 4)

    def validate_indian_structure(self, plate: str) -> Tuple[bool, str]:
        """
        Validates Indian license plate formats strictly:
        1. Standard State Series: e.g. DL01CA1234, MH12AB9999 (State code MUST be in INDIAN_STATES)
        2. Bharat (BH) Series: e.g. 25BH2534O, 24BH1234A
        Returns (is_valid, format_type).
        """
        plate = self.clean_plate(plate)
        if not plate:
            return False, "EMPTY"

        # Bharat Series: 2 digits (year) + BH + 4 digits + 1-2 letters
        bh_pattern = r"^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$"
        if re.match(bh_pattern, plate):
            return True, "BHARAT_SERIES"

        # Standard State Pattern: 2 letters (State) + 1-2 digits (RTO) + 1-3 letters (Series) + 3-4 digits
        std_pattern = r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4}$"
        if re.match(std_pattern, plate):
            state = plate[:2]
            if state in INDIAN_STATES:
                return True, "STANDARD_STATE"
            return False, "INVALID_STATE_CODE"

        return False, "UNKNOWN_STRUCTURE"

    def normalize_plate(self, raw_plate: str) -> str:
        """
        Syntactically normalizes raw OCR text using Indian plate structural rules.
        Corrects common OCR digit/letter flips based on positional syntax.
        """
        plate = self.clean_plate(raw_plate)
        if not plate:
            return ""

        chars = list(plate)
        length = len(chars)

        # 1. Bharat Series correction: e.g. '258H25340' -> '25BH2534O' or '25BH2534A'
        # Position 0,1 should be digits.
        # Position 2,3 should be 'BH'. ('8H' -> 'BH')
        # Position 4..7 should be 4 digits. ('O' -> '0', 'B' -> '8', etc.)
        # Position 8..end should be letters. ('0' -> 'O')
        if length >= 9 and chars[2] in ['8', 'B'] and chars[3] in ['H', 'h', '4']:
            # Force first 2 digits
            for i in range(2):
                if chars[i] in ['O', 'Q', 'D']:
                    chars[i] = '0'
                elif chars[i] in ['I', 'L']:
                    chars[i] = '1'
                elif chars[i] == 'Z':
                    chars[i] = '2'
                elif chars[i] == 'S':
                    chars[i] = '5'
                elif chars[i] == 'B':
                    chars[i] = '8'

            chars[2] = 'B'
            chars[3] = 'H'

            # Digits in position 4 to 7
            for i in range(4, min(8, length)):
                if chars[i] in ['O', 'Q', 'D']:
                    chars[i] = '0'
                elif chars[i] in ['I', 'L']:
                    chars[i] = '1'
                elif chars[i] == 'Z':
                    chars[i] = '2'
                elif chars[i] == 'S':
                    chars[i] = '5'
                elif chars[i] == 'B':
                    chars[i] = '8'

            # Letters at position 8 onwards
            for i in range(8, length):
                if chars[i] == '0':
                    chars[i] = 'O'
                elif chars[i] == '1':
                    chars[i] = 'I'
                elif chars[i] == '8':
                    chars[i] = 'B'
                elif chars[i] == '5':
                    chars[i] = 'S'
                elif chars[i] == '2':
                    chars[i] = 'Z'

            return "".join(chars)

        # 2. Standard State Plate correction: e.g. '0L01CA1234' -> 'DL01CA1234', 'MH49HE2355' -> 'MH49AE2355', 'KA41MF6946' -> 'KA41MF6946'
        if length >= 8:
            # Positions 0,1 should be state letters (e.g., MH, DL, UP, HR, KA, WB, RJ, etc.)
            for i in range(2):
                if chars[i] == '0': chars[i] = 'O'
                elif chars[i] == '1': chars[i] = 'I'
                elif chars[i] == '8': chars[i] = 'B'
                elif chars[i] == '5': chars[i] = 'S'

            # Position 2,3 should be RTO numbers (e.g. DL01, MH49, KA41)
            for i in range(2, 4):
                if chars[i] in ['O', 'D']: chars[i] = '0'
                elif chars[i] in ['I', 'L']: chars[i] = '1'
                elif chars[i] == 'Z': chars[i] = '2'
                elif chars[i] == 'E': chars[i] = '3'
                elif chars[i] in ['A', 'H']: chars[i] = '4'
                elif chars[i] == 'S': chars[i] = '5'
                elif chars[i] == 'G': chars[i] = '6'
                elif chars[i] == 'T': chars[i] = '7'
                elif chars[i] == 'B': chars[i] = '8'
                elif chars[i] == 'Q': chars[i] = '0'

            # Determine series and number boundaries
            # In standard 10-char plate (e.g., MH49AE2355), pos 4,5 are series letters, pos 6..9 are digits.
            # In 9-char plate (e.g., MH49A2355 or MH49AE235), pos 4 is series, pos 5..8 are digits.
            series_end = 6 if length >= 10 else (5 if (length == 9 and chars[5].isdigit()) else 6)
            series_end = min(series_end, length - 3)

            # Series letters (e.g., AE, MF, CB, BC, AB, CD, DQ, Q)
            for i in range(4, series_end):
                if chars[i] == '0': chars[i] = 'O'
                elif chars[i] == '1': chars[i] = 'I'
                elif chars[i] == '8': chars[i] = 'B'
                elif chars[i] == '5': chars[i] = 'S'
                elif chars[i] == '2': chars[i] = 'Z'
                elif chars[i] == '3': chars[i] = 'E'
                # Preserve Q, M, F, D, A, etc. in series letters!

            # Tail digits (last 3 or 4 digits)
            for i in range(series_end, length):
                if chars[i] in ['O', 'D']: chars[i] = '0'
                elif chars[i] in ['I', 'L']: chars[i] = '1'
                elif chars[i] == 'Z': chars[i] = '2'
                elif chars[i] == 'E': chars[i] = '3'
                elif chars[i] in ['A', 'H']: chars[i] = '4'
                elif chars[i] == 'S': chars[i] = '5'
                elif chars[i] == 'G': chars[i] = '6'
                elif chars[i] == 'T': chars[i] = '7'
                elif chars[i] == 'B': chars[i] = '8'
                elif chars[i] == 'Q': chars[i] = '0'

            return "".join(chars)

        return plate

    def generate_candidate_variants(self, raw_plate: str, ocr_conf: float = 0.90) -> List[Dict[str, Any]]:
        """
        Generates plausible candidate identities for a raw OCR reading
        with probabilistic weights based on confusion costs and syntax validity.
        """
        cleaned = self.clean_plate(raw_plate)
        normalized = self.normalize_plate(raw_plate)

        candidates_map: Dict[str, float] = {}

        # 1. Normalized candidate (highest base prior)
        is_norm_valid, _ = self.validate_indian_structure(normalized)
        norm_weight = 1.0 if is_norm_valid else 0.70
        candidates_map[normalized] = norm_weight * (ocr_conf + 0.15)

        # 2. Raw OCR candidate
        if cleaned != normalized:
            is_clean_valid, _ = self.validate_indian_structure(cleaned)
            clean_weight = 0.85 if is_clean_valid else 0.50
            candidates_map[cleaned] = clean_weight * ocr_conf

        # 3. Generate common confusion permutations
        # If Bharat series candidate, generate permutations (e.g. 25BH2534O vs 25BH25340 vs 258H2534O)
        if "BH" in normalized or "8H" in cleaned:
            base = normalized
            if len(base) >= 9:
                v1 = base[:2] + "8H" + base[4:]
                v2 = base[:-1] + ("0" if base[-1] == "O" else "O")
                candidates_map[v1] = candidates_map.get(v1, 0.0) + 0.12
                candidates_map[v2] = candidates_map.get(v2, 0.0) + 0.15

        # Also add generic fallback
        # Normalize sum to 100%
        total_score = sum(candidates_map.values()) + 0.05 # Add small epsilon for 'Other'
        results = []

        for cand, score in candidates_map.items():
            prob = min(0.98, max(0.02, round(score / total_score, 3)))
            is_val, val_type = self.validate_indian_structure(cand)
            results.append({
                "plate": cand,
                "probability": prob,
                "percentage": int(prob * 100),
                "is_valid_structure": is_val,
                "structure_type": val_type
            })

        # Sort descending by probability
        results.sort(key=lambda x: x["probability"], reverse=True)

        # Ensure sum is well balanced
        assigned_sum = sum(r["probability"] for r in results)
        other_prob = max(0.01, round(1.0 - assigned_sum, 3))
        results.append({
            "plate": "Other",
            "probability": other_prob,
            "percentage": max(1, int(other_prob * 100)),
            "is_valid_structure": False,
            "structure_type": "UNRESOLVED_RESIDUAL"
        })

        return results

    def resolve_or_update_identity(
        self,
        raw_ocr: str,
        camera_id: str,
        detection_conf: float,
        ocr_conf: float,
        vehicle_type: str = "Sedan",
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Confidence-aware identity resolution across observation events.
        Matches with active vehicle tracks using weighted Levenshtein,
        updates candidate identity probability via Bayesian pooling,
        and returns the consolidated vehicle identity profile.
        """
        now_str = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cleaned_raw = self.clean_plate(raw_ocr)
        normalized = self.normalize_plate(cleaned_raw)

        # Look for matching active track in memory
        matched_track_id = None
        best_sim = 0.0

        now_dt = datetime.now()

        for track_id, track in list(self.active_tracks.items()):
            resolved_plate = track["resolved_plate"]
            sim = self.plate_similarity(resolved_plate, normalized)
            
            # Check time elapsed since last sighting
            last_t = datetime.strptime(track["last_seen_timestamp"], "%Y-%m-%d %H:%M:%S") if "last_seen_timestamp" in track else now_dt
            dt_sec = (now_dt - last_t).total_seconds()

            is_same_camera = (track.get("last_camera_id") == camera_id)
            same_prefix = (len(normalized) >= 6 and len(resolved_plate) >= 6 and normalized[:6] == resolved_plate[:6])

            # Match criteria: high similarity (>=0.75) OR (same camera within 60s & same prefix/similar)
            threshold = 0.65 if (is_same_camera and dt_sec < 60) else 0.78
            
            if (sim >= threshold or (is_same_camera and dt_sec < 60 and same_prefix)) and sim > best_sim:
                best_sim = sim
                matched_track_id = track_id

        if matched_track_id:
            # Multi-camera observation update (Bayesian confidence boost)
            track = self.active_tracks[matched_track_id]
            track["sightings_count"] += 1
            track["last_camera_id"] = camera_id
            track["last_seen_timestamp"] = now_str
            track["observations"].append({
                "camera_id": camera_id,
                "timestamp": now_str,
                "raw_ocr": cleaned_raw,
                "normalized_ocr": normalized,
                "detection_conf": detection_conf,
                "ocr_conf": ocr_conf
            })

            # Upgrade resolved_plate if incoming normalized OCR is valid Indian structure and longer/higher conf
            is_curr_valid, _ = self.validate_indian_structure(track["resolved_plate"])
            is_new_valid, _ = self.validate_indian_structure(normalized)

            if is_new_valid and (not is_curr_valid or len(normalized) > len(track["resolved_plate"]) or ocr_conf > track.get("best_ocr_conf", 0)):
                track["resolved_plate"] = normalized
                track["best_ocr_conf"] = ocr_conf

            # Bayesian update on identity confidence
            prior_conf = track["identity_confidence"]
            evidence_weight = (ocr_conf * 0.6 + detection_conf * 0.4) * max(best_sim, 0.85)
            updated_conf = min(0.99, prior_conf + (1.0 - prior_conf) * (evidence_weight * 0.35))
            track["identity_confidence"] = round(updated_conf, 3)

            # Rebalance candidate distribution
            for cand in track["candidate_identities"]:
                if cand["plate"] == track["resolved_plate"]:
                    cand["probability"] = min(0.98, cand["probability"] + 0.05)
                elif cand["plate"] != "Other":
                    cand["probability"] = max(0.01, cand["probability"] - 0.02)
                cand["percentage"] = int(cand["probability"] * 100)

            # Recalculate 'Other'
            known_sum = sum(c["probability"] for c in track["candidate_identities"] if c["plate"] != "Other")
            for cand in track["candidate_identities"]:
                if cand["plate"] == "Other":
                    cand["probability"] = max(0.01, round(1.0 - known_sum, 3))
                    cand["percentage"] = max(1, int(cand["probability"] * 100))

            return track

        # Create new track entity
        candidates = self.generate_candidate_variants(cleaned_raw, ocr_conf)
        resolved_plate = normalized if normalized else cleaned_raw
        best_cand = candidates[0] if candidates else {"probability": ocr_conf}

        initial_conf = round(min(0.98, max(0.40, ocr_conf * (1.05 if best_cand.get("is_valid_structure") else 0.85))), 3)

        track_id = f"VEH-{resolved_plate}-{int(datetime.now().timestamp()) % 100000}"
        track_data = {
            "track_id": track_id,
            "resolved_plate": resolved_plate,
            "raw_ocr": cleaned_raw,
            "normalized_ocr": normalized,
            "identity_confidence": initial_conf,
            "candidate_identities": candidates,
            "vehicle_type": vehicle_type,
            "first_camera_id": camera_id,
            "last_camera_id": camera_id,
            "first_seen_timestamp": now_str,
            "last_seen_timestamp": now_str,
            "sightings_count": 1,
            "observations": [
                {
                    "camera_id": camera_id,
                    "timestamp": now_str,
                    "raw_ocr": cleaned_raw,
                    "normalized_ocr": normalized,
                    "detection_conf": detection_conf,
                    "ocr_conf": ocr_conf
                }
            ]
        }

        self.active_tracks[track_id] = track_data
        # Prune old tracks if exceeding 200 items
        if len(self.active_tracks) > 200:
            oldest_key = list(self.active_tracks.keys())[0]
            del self.active_tracks[oldest_key]

        return track_data

identity_engine = IdentityEngine()
