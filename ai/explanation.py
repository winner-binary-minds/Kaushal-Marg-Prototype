"""
Explanation Generator - Recommendation Result Narrator

Produces a short, beneficiary-friendly plain-language explanation of the
recommendation pipeline output. Uses GeminiClient.generate_text().

Responsibilities:
- Convert structured recommendation_result dict into a readable narrative
- Support English, Hindi, and Marathi
- Only describe facts present in the supplied recommendation_result
- Handle missing/empty result data gracefully (no crash, fallback message)
- Never log sensitive beneficiary data or API keys

Does NOT:
- Invent job facts, salaries, schemes, or eligibility criteria
- Perform recommendations (separate module)
- Extract profiles (separate module)
- Access database or render UI
"""

import logging
from typing import Optional

from ai.gemini import GeminiClient, GeminiAPIError

logger = logging.getLogger(__name__)

# Language codes supported (must match ConversationManager)
_SUPPORTED_LANGUAGES = {"en", "hi", "mr"}

# System instruction prefix per language — tells the model its role and constraints
_SYSTEM_INSTRUCTIONS = {
    "en": (
        "You are a helpful assistant for Kaushal Marg, a skills and livelihood "
        "discovery platform for Indian youth. "
        "Your task: write a short, encouraging, plain-language explanation "
        "(3-5 sentences) of the recommendation result provided below. "
        "IMPORTANT RULES: "
        "1. Use ONLY the facts given in the data below. "
        "2. Do NOT invent salaries, government schemes, eligibility criteria, "
        "or opportunities not present in the data. "
        "3. Speak directly to the beneficiary (use 'you'). "
        "4. Keep it simple, warm, and motivating. "
        "5. Write in English."
    ),
    "hi": (
        "aap Kaushal Marg ke liye ek sahayak hain - Bharatiya yuvaon ke liye "
        "kaushal aur aajivika khoj manch. "
        "aapka kary: niche diye gaye anushansa parinam ki ek sankshipt, "
        "protsahak aur saral vyakhya (3-5 vakya) likhna hai. "
        "mahatvapurn niyam: "
        "1. keval niche diye gaye tathyon ka upyog karen. "
        "2. vetan, sarkari yojanaen, patrata manadand, ya aise avsar na banaen "
        "jo data mein nahin hain. "
        "3. seedhe labharti se baat karen ('aap' ka upyog karen). "
        "4. saral, garmajosha bhari aur preranadayak bhasha rakhen. "
        "5. Hindi mein likhen."
    ),
    "mr": (
        "aap Kaushal Margasathi ek madadgar sahayak ahat - Bharatiya yuvanansathi "
        "kaushal aani aajivika shodh platform. "
        "aapale kary: khali dilelya shipharis parinamacha ek sankshipt, "
        "protsahak aani sopi vyakhya (3-5 vakye) likhane. "
        "mahattvache niyam: "
        "1. kevaL khali dilelya tathyanche vapra kara. "
        "2. pagar, sarkari yojana, patrata nikash kiva datamadhe naslelya "
        "sandhi tayar karu naka. "
        "3. labhartyashi thete bola ('tumhi' vapra). "
        "4. sadhi, ubadhar aani preranadayi bhasha theva. "
        "5. Marathit likha."
    ),
}

# Fallback messages when no usable data is available
_FALLBACK_MESSAGES = {
    "en": (
        "We could not find enough information to generate a detailed explanation. "
        "Please continue the conversation so we can learn more about your skills."
    ),
    "hi": (
        "Hum ek vistrit vyakhya tayar karne ke liye paryapt jankari nahi pa sake. "
        "Kripaya batcit jari rakhen taki hum aapke kaushal ke bare mein adhik jan saken."
    ),
    "mr": (
        "Tapshilvaar vyakhya tayar karnyasathi amhala pureshee mahiti milu shakli nahi. "
        "Kripaya sambhashan suru theva jenekrun amhi tumchya kaushalyanbaddal adhik janum."
    ),
}


class ExplanationGenerator:
    """
    Generates a beneficiary-friendly explanation of recommendation pipeline results.

    Takes the dict returned by run_recommendation_pipeline() and produces a
    short plain-language narrative using GeminiClient.generate_text().

    Only facts present in the supplied recommendation_result are used.
    The model is explicitly instructed not to invent job data, salaries,
    government schemes, eligibility criteria, or local opportunities.

    Supports English ('en'), Hindi ('hi'), and Marathi ('mr').
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the ExplanationGenerator.

        Args:
            api_key: Gemini API key. If None, reads from GEMINI_API_KEY env var.
        """
        try:
            self._gemini_client = GeminiClient(api_key=api_key, max_output_tokens=512)
            logger.debug("ExplanationGenerator initialized successfully with Gemini")
        except Exception as e:
            logger.warning(
                "Gemini API key not configured or client initialization failed (%s). Using template generator fallback.",
                str(e)
            )
            self._gemini_client = None

    def generate_explanation(
        self,
        recommendation_result: dict,
        language: str = "en",
    ) -> str:
        """
        Generate a plain-language explanation of a recommendation result.

        Args:
            recommendation_result: Dict returned by run_recommendation_pipeline() or direct rec dict.
            language: Language code. Must be 'en', 'hi', or 'mr'. Defaults to 'en'.

        Returns:
            A short, beneficiary-friendly narrative string.
        """
        # Normalise and validate language — fall back silently to English
        if not isinstance(language, str) or language.strip() not in _SUPPORTED_LANGUAGES:
            logger.warning(
                "Unsupported language '%s' requested; falling back to 'en'", language
            )
            language = "en"
        else:
            language = language.strip()

        # Validate recommendation_result type
        if not isinstance(recommendation_result, dict):
            logger.warning("recommendation_result is not a dict; returning fallback")
            return _FALLBACK_MESSAGES[language]

        # Extract only the facts we need — safe .get() throughout
        summary_data = self._extract_summary_facts(recommendation_result)

        # If there is nothing meaningful to explain, return fallback
        if not summary_data.get("has_data"):
            logger.debug("No usable recommendation data; returning fallback message")
            return _FALLBACK_MESSAGES[language]

        # If Gemini client is not initialized, generate formatted template explanation
        if self._gemini_client is None:
            return self._generate_template_explanation(summary_data, language)

        # Build the prompt
        prompt = self._build_prompt(summary_data, language)

        try:
            explanation = self._gemini_client.generate_text(prompt)
            logger.debug("Explanation generated successfully")
            return explanation
        except Exception as e:
            logger.warning("Gemini text generation failed (%s); using template fallback.", str(e))
            return self._generate_template_explanation(summary_data, language)

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _extract_summary_facts(self, result: dict) -> dict:
        """
        Extract only the facts present in the result dict.

        Returns a flat dict of safe, displayable facts. Nothing is invented.
        All values come exclusively from the supplied result.

        Args:
            result: recommendation_result dict from pipeline.

        Returns:
            Dict of extracted facts plus a 'has_data' bool flag.
        """
        facts: dict = {"has_data": False}

        # --- Top recommendation ---
        if "job_role" in result:
            top = result
        else:
            recommendations = result.get("recommendations") or []
            top = recommendations[0] if (recommendations and isinstance(recommendations, list)) else {}

        if isinstance(top, dict) and top:
            job_role = top.get("job_role") or ""
            sector = top.get("sector") or ""
            nsqf_level = top.get("nsqf_level") or ""
            score = top.get("score")
            employment_type = top.get("employment_type") or ""
            matched_skills = top.get("matched_skills") or []
            missing_skills = top.get("missing_skills") or []
            skill_coverage = top.get("skill_coverage")
            local_opportunity = top.get("local_opportunity") or ""
            why_recommended = top.get("why_recommended") or []

            if job_role:
                facts["has_data"] = True
                facts["job_role"] = job_role
            if sector:
                facts["sector"] = sector
            if nsqf_level:
                facts["nsqf_level"] = nsqf_level
            if score is not None:
                facts["score"] = score
            if employment_type:
                facts["employment_type"] = employment_type
            if matched_skills:
                facts["matched_skills"] = matched_skills
            if missing_skills:
                facts["missing_skills"] = missing_skills
            if skill_coverage is not None:
                facts["skill_coverage"] = skill_coverage
            if local_opportunity and "no verified" not in local_opportunity.lower():
                facts["local_opportunity"] = local_opportunity
            if why_recommended:
                facts["why_recommended"] = why_recommended

        # --- Skill gap summary ---
        skill_gaps = result.get("skill_gaps") or {}
        if isinstance(skill_gaps, dict):
            gap_summary = skill_gaps.get("summary") or ""
            if gap_summary:
                facts["gap_summary"] = gap_summary

        # --- Pathway target role ---
        pathway = result.get("pathway") or {}
        if isinstance(pathway, dict):
            target_role = pathway.get("target_role") or {}
            if isinstance(target_role, dict) and target_role.get("job_role"):
                facts["target_role"] = target_role["job_role"]

        return facts

    def _generate_template_explanation(self, facts: dict, language: str) -> str:
        """Generates a structured, beneficiary-friendly template narrative."""
        role = facts.get("job_role", "Target Role")
        sector = facts.get("sector", "Skilling")
        nsqf = facts.get("nsqf_level", "Unknown")
        score = facts.get("score", 0)
        matched = ", ".join(facts.get("matched_skills", [])) or ("None" if language == "en" else ("कोई नहीं" if language == "hi" else "काहीही नाही"))
        missing = ", ".join(facts.get("missing_skills", [])) or ("None" if language == "en" else ("कोई नहीं" if language == "hi" else "काहीही नाही"))
        local_opp = facts.get("local_opportunity", "No verified data" if language == "en" else ("कोई सत्यापित डेटा नहीं" if language == "hi" else "कोणताही सत्यापित डेटा नाही"))

        if language == "hi":
            return (
                f"**अनुशंसित भूमिका:** {role}\n\n"
                f"**क्षेत्र:** {sector}\n\n"
                f"**NSQF स्तर:** {nsqf}\n\n"
                f"**स्कोर:** {score}%\n\n"
                f"**मिलान कौशल्य:** {matched}\n\n"
                f"**आवश्यक प्रशिक्षण:** {missing}\n\n"
                f"**स्थानीय अवसर:** {local_opp}"
            )
        elif language == "mr":
            return (
                f"**शिफारस केलेली भूमिका:** {role}\n\n"
                f"**क्षेत्र:** {sector}\n\n"
                f"**NSQF स्तर:** {nsqf}\n\n"
                f"**स्कोर:** {score}%\n\n"
                f"**जुळलेले कौशल्ये:** {matched}\n\n"
                f"**आवश्यक कौशल्ये:** {missing}\n\n"
                f"**स्थानिक संधी:** {local_opp}"
            )
        else:
            return (
                f"**Recommended Role:** {role}\n\n"
                f"**Sector:** {sector}\n\n"
                f"**NSQF Level:** {nsqf}\n\n"
                f"**Match Score:** {score}%\n\n"
                f"**Matched Skills:** {matched}\n\n"
                f"**Missing Skills:** {missing}\n\n"
                f"**Local Opportunity:** {local_opp}"
            )

    def _build_prompt(self, facts: dict, language: str) -> str:
        """
        Construct the prompt sent to Gemini.

        Includes only the facts extracted from the result — no invented data.

        Args:
            facts: Dict from _extract_summary_facts().
            language: Validated language code ('en', 'hi', 'mr').

        Returns:
            Full prompt string ready for GeminiClient.generate_text().
        """
        system_instruction = _SYSTEM_INSTRUCTIONS[language]

        # Build structured facts block — only include keys that exist
        lines = []
        if "job_role" in facts:
            lines.append(f"Recommended Job Role: {facts['job_role']}")
        if "sector" in facts:
            lines.append(f"Sector: {facts['sector']}")
        if "score" in facts:
            lines.append(f"Match Score: {facts['score']}/100")
        if "employment_type" in facts:
            lines.append(f"Employment Type: {facts['employment_type']}")
        if "skill_coverage" in facts:
            lines.append(f"Skill Coverage: {facts['skill_coverage']}%")
        if "matched_skills" in facts:
            lines.append(f"Skills You Already Have: {', '.join(facts['matched_skills'])}")
        if "missing_skills" in facts:
            lines.append(f"Skills to Learn: {', '.join(facts['missing_skills'])}")
        if "local_opportunity" in facts:
            lines.append(f"Local Opportunity: {facts['local_opportunity']}")
        if "gap_summary" in facts:
            lines.append(f"Skill Assessment: {facts['gap_summary']}")
        if "why_recommended" in facts:
            lines.append(f"Why Recommended: {'; '.join(facts['why_recommended'])}")

        facts_block = "\n".join(lines)

        prompt = (
            f"{system_instruction}\n\n"
            f"--- RECOMMENDATION DATA ---\n"
            f"{facts_block}\n"
            f"--- END OF DATA ---\n\n"
            f"Now write the explanation:"
        )

        return prompt
