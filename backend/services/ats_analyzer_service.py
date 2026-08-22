import re
from typing import List, Set
from backend.models.resume import Resume, JobDescription, ATSScore

class ATSAnalyzerService:
    def _normalize(self, term: str) -> str:
        # Lowercase and remove all non-alphanumeric characters for robust exact matching
        return re.sub(r'[^a-z0-9]', '', term.lower())

    def _extract_all_resume_text(self, resume: Resume) -> str:
        text = [resume.summary or ""]
        text.extend(resume.skills)
        for exp in resume.experience:
            text.append(exp.title)
            text.append(exp.company)
            text.extend(exp.bullets)
        for ed in resume.education:
            text.append(ed.degree)
            text.append(ed.institution)
        for proj in resume.projects:
            text.append(proj.name)
            text.extend(proj.technologies)
            text.extend(proj.bullets)
        return " ".join(text)

    def analyze(self, resume: Resume, jd: JobDescription) -> ATSScore:
        # 1. Skill Match (35%)
        # Extract skills from resume explicitly
        resume_skills_norm = {self._normalize(s) for s in resume.skills}
        for proj in resume.projects:
            resume_skills_norm.update(self._normalize(s) for s in proj.technologies)
            
        jd_req_skills_norm = {self._normalize(s) for s in jd.required_skills}
        jd_pref_skills_norm = {self._normalize(s) for s in jd.preferred_skills}
        
        missing_required = []
        for req in jd.required_skills:
            if self._normalize(req) not in resume_skills_norm:
                missing_required.append(req)
                
        missing_preferred = []
        for pref in jd.preferred_skills:
            if self._normalize(pref) not in resume_skills_norm:
                missing_preferred.append(pref)

        total_skills = len(jd.required_skills) + len(jd.preferred_skills)
        if total_skills == 0:
            skill_score = 100.0
        else:
            matched = total_skills - len(missing_required) - len(missing_preferred)
            # Required skills weigh more (say 2x)
            total_weight = len(jd.required_skills) * 2 + len(jd.preferred_skills)
            matched_weight = (len(jd.required_skills) - len(missing_required)) * 2 + (len(jd.preferred_skills) - len(missing_preferred))
            skill_score = (matched_weight / total_weight) * 100.0 if total_weight > 0 else 100.0
            
        # 2. Keyword Match (25%)
        resume_full_text = self._normalize(self._extract_all_resume_text(resume))
        matched_keywords = []
        for kw in jd.keywords:
            if self._normalize(kw) in resume_full_text:
                matched_keywords.append(kw)
                
        kw_score = (len(matched_keywords) / len(jd.keywords)) * 100.0 if jd.keywords else 100.0
        
        # 3. Experience Match (20%)
        exp_score = 100.0
        if jd.required_experience_years:
            # Very basic deterministic calculation of total years of experience
            total_years = 0
            for exp in resume.experience:
                # Mock calculation, assuming standard parsing or missing dates
                # For Phase 8 we will assume 1 year per experience block if dates are unparseable
                total_years += 1 
            if total_years < jd.required_experience_years:
                exp_score = (total_years / jd.required_experience_years) * 100.0
                
        # 4. Education Match (10%)
        edu_score = 100.0
        if jd.education_requirements:
            edu_norm = {self._normalize(ed.degree) for ed in resume.education}
            edu_matched = any(self._normalize(req) in e for req in jd.education_requirements for e in edu_norm)
            if not edu_matched:
                edu_score = 0.0

        # 5. Completeness Score (10%)
        completeness = 100.0
        if not resume.contact.email or not resume.contact.phone:
            completeness -= 20.0
        if not resume.experience:
            completeness -= 40.0
        if not resume.education:
            completeness -= 20.0
        if not resume.skills:
            completeness -= 20.0
            
        completeness = max(0.0, completeness)
        
        # Overall Score
        overall = (
            (skill_score * 0.35) +
            (kw_score * 0.25) +
            (exp_score * 0.20) +
            (edu_score * 0.10) +
            (completeness * 0.10)
        )
        
        return ATSScore(
            overall_score=overall,
            skill_match_score=skill_score,
            keyword_match_score=kw_score,
            experience_match_score=exp_score,
            education_match_score=edu_score,
            completeness_score=completeness,
            missing_required_skills=missing_required,
            missing_preferred_skills=missing_preferred,
            matched_keywords=matched_keywords
        )
