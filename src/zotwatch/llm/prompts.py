"""Prompt templates for LLM summarization."""

BULLET_SUMMARY_PROMPT = """Analyze this academic paper and provide a concise summary.

Title: {title}
Abstract: {abstract}
Authors: {authors}
Venue: {venue}

Provide exactly 5 bullet points covering:
1. **Research Question**: What problem does this paper address?
2. **Methodology**: What approach or methods were used?
3. **Key Findings**: What are the main results?
4. **Innovation**: What is novel about this work?
5. **Relevance**: Why might this be important to researchers in related fields?

Format your response as a JSON object with keys: research_question, methodology, key_findings, innovation, relevance_note
Each value should be a single, concise sentence (max 50 words).

IMPORTANT: Return ONLY the JSON object, no additional text or markdown formatting."""

DETAILED_ANALYSIS_PROMPT = """Provide a detailed analysis of this academic paper.

Title: {title}
Abstract: {abstract}
Authors: {authors}
Venue: {venue}

Write a comprehensive analysis covering:

1. **Background**: Context and motivation for this research (2-3 sentences)
2. **Methodology Details**: Detailed explanation of the approach (3-4 sentences)
3. **Results**: Key findings and their significance (3-4 sentences)
4. **Limitations**: Known limitations or potential issues (2-3 sentences)
5. **Future Directions**: Potential follow-up research (1-2 sentences)
6. **Relevance to Interests**: Why this paper might be relevant to a researcher studying similar topics

Format your response as a JSON object with keys: background, methodology_details, results, limitations, future_directions, relevance_to_interests

IMPORTANT: Return ONLY the JSON object, no additional text or markdown formatting."""


__all__ = ["BULLET_SUMMARY_PROMPT", "DETAILED_ANALYSIS_PROMPT"]
