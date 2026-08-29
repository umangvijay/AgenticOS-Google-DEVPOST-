import io
from backend.models.resume import Resume

class ResumeRendererService:
    def _generate_html(self, resume: Resume) -> str:
        # A simple, semantic, ATS-friendly HTML template
        html_parts = []
        html_parts.append("<html><head><style>")
        html_parts.append("""
            body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 11pt; line-height: 1.4; color: #333; margin: 40px; }
            h1 { font-size: 24pt; margin-bottom: 5px; text-align: center; }
            .contact { text-align: center; font-size: 10pt; margin-bottom: 20px; }
            h2 { font-size: 14pt; border-bottom: 1px solid #000; margin-top: 20px; margin-bottom: 10px; padding-bottom: 2px; text-transform: uppercase; }
            h3 { font-size: 12pt; margin: 10px 0 5px 0; }
            .date { float: right; font-style: italic; font-weight: normal; }
            .company { font-style: italic; margin-bottom: 5px; }
            ul { margin-top: 5px; padding-left: 20px; }
            li { margin-bottom: 5px; }
            .skills { line-height: 1.6; }
        """)
        html_parts.append("</style></head><body>")
        
        # Header
        html_parts.append(f"<h1>{self._escape(resume.contact.name)}</h1>")
        contact_info = [self._escape(resume.contact.email)]
        if resume.contact.phone:
            contact_info.append(self._escape(resume.contact.phone))
        if resume.contact.location:
            contact_info.append(self._escape(resume.contact.location))
        if resume.contact.linkedin:
            contact_info.append(self._escape(resume.contact.linkedin))
        
        html_parts.append(f"<div class='contact'>{' | '.join(contact_info)}</div>")
        
        # Summary
        if resume.summary:
            html_parts.append(f"<p>{self._escape(resume.summary)}</p>")
            
        # Skills
        if resume.skills:
            html_parts.append("<h2>Skills</h2>")
            html_parts.append(f"<div class='skills'><b>Core Competencies:</b> {self._escape(', '.join(resume.skills))}</div>")
            
        # Experience
        if resume.experience:
            html_parts.append("<h2>Experience</h2>")
            for exp in resume.experience:
                end_date = exp.end_date or "Present"
                html_parts.append(f"<h3>{self._escape(exp.title)} <span class='date'>{self._escape(exp.start_date)} - {self._escape(end_date)}</span></h3>")
                loc_str = f" - {self._escape(exp.location)}" if exp.location else ""
                html_parts.append(f"<div class='company'>{self._escape(exp.company)}{loc_str}</div>")
                
                if exp.bullets:
                    html_parts.append("<ul>")
                    for bullet in exp.bullets:
                        html_parts.append(f"<li>{self._escape(bullet)}</li>")
                    html_parts.append("</ul>")
                    
        # Education
        if resume.education:
            html_parts.append("<h2>Education</h2>")
            for ed in resume.education:
                date_str = f"<span class='date'>{self._escape(ed.graduation_date)}</span>" if ed.graduation_date else ""
                html_parts.append(f"<h3>{self._escape(ed.degree)} {date_str}</h3>")
                html_parts.append(f"<div class='company'>{self._escape(ed.institution)}</div>")
                
        # Projects
        if resume.projects:
            html_parts.append("<h2>Projects</h2>")
            for proj in resume.projects:
                html_parts.append(f"<h3>{self._escape(proj.name)}</h3>")
                if proj.description:
                    html_parts.append(f"<p>{self._escape(proj.description)}</p>")
                if proj.bullets:
                    html_parts.append("<ul>")
                    for bullet in proj.bullets:
                        html_parts.append(f"<li>{self._escape(bullet)}</li>")
                    html_parts.append("</ul>")
                    
        html_parts.append("</body></html>")
        return "".join(html_parts)
        
    def _escape(self, text: str) -> str:
        if not text:
            return ""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def render_html(self, resume: Resume) -> str:
        return self._generate_html(resume)

    def render_pdf(self, resume: Resume) -> bytes:
        """Renders a Resume object to a PDF byte string via WeasyPrint."""
        html_string = self._generate_html(resume)
        from weasyprint import HTML

        pdf_buffer = io.BytesIO()
        HTML(string=html_string).write_pdf(pdf_buffer)
        
        pdf_bytes = pdf_buffer.getvalue()
        pdf_buffer.close()
        return pdf_bytes
