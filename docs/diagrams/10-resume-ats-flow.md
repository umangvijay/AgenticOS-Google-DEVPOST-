# Resume ATS Flow

```mermaid
graph TD
    PDF[Resume PDF] -->|Extract Text| Parser[JD Parser Service]
    JD[Job Description] --> Parser
    Parser --> ATSAnalyzer[ATS Analyzer Service]
    ATSAnalyzer -->|Compare Skills/Gaps| Matcher[Evaluation Service]
    Matcher --> ResumeTailor[Resume Tailor Service]
    ResumeTailor --> Output[Tailored Resume]
```
