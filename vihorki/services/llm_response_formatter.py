"""
LLM Response Formatter.
Transforms raw LLM analysis response into human-readable format.
"""

import re
import json
from typing import Dict, Any, Optional


def decode_unicode_escapes(text: str) -> str:
    """
    Decode Unicode escape sequences in text.
    Handles \\uXXXX patterns that may come from JSON encoding.
    """
    if not text:
        return text
    
    try:
        # Try to decode as JSON string to handle unicode escapes
        # Wrap in quotes if not already a JSON string
        if not text.startswith('"'):
            decoded = text.encode('utf-8').decode('unicode_escape')
        else:
            decoded = json.loads(text)
        return decoded
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Fallback: try regex-based decoding
        def replace_unicode(match):
            try:
                return chr(int(match.group(1), 16))
            except ValueError:
                return match.group(0)
        
        result = re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode, text)
        return result


def format_llm_analysis(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format LLM analysis result into human-readable structure.
    
    Args:
        analysis_result: Raw analysis result from orchestrator
        
    Returns:
        Formatted analysis with decoded text
    """
    formatted = {
        'status': analysis_result.get('status', 'unknown'),
        'timestamp': analysis_result.get('timestamp'),
        'project': analysis_result.get('project'),
        'releases_compared': analysis_result.get('releases', []),
    }
    
    # Format validation status
    validation = analysis_result.get('validation', {})
    formatted['validation'] = {
        'passed': validation.get('status') == 'passed',
        'error': validation.get('error')
    }
    
    # Format LLM analysis
    llm_analysis = analysis_result.get('llm_analysis', {})
    if llm_analysis.get('status') == 'success':
        raw_analysis = llm_analysis.get('analysis', '')
        
        # Decode unicode escapes
        decoded_analysis = decode_unicode_escapes(raw_analysis)
        
        # Parse and structure the analysis
        formatted['analysis'] = {
            'status': 'success',
            'text': decoded_analysis,
            'sections': parse_analysis_sections(decoded_analysis),
            'metadata': llm_analysis.get('metadata', {})
        }
    elif llm_analysis.get('status') == 'error':
        formatted['analysis'] = {
            'status': 'error',
            'error': llm_analysis.get('error', 'Unknown error'),
            'text': None,
            'sections': {}
        }
    else:
        formatted['analysis'] = {
            'status': llm_analysis.get('status', 'skipped'),
            'text': None,
            'sections': {}
        }
    
    return formatted


def parse_analysis_sections(text: str) -> Dict[str, str]:
    """
    Parse analysis text into logical sections.
    Attempts to extract key sections like summary, problems, recommendations.
    
    Args:
        text: Decoded analysis text
        
    Returns:
        Dictionary with section names as keys and content as values
    """
    if not text:
        return {}
    
    sections = {}
    
    # Common section headers in Russian and English
    section_patterns = [
        (r'(?:^|\n)#+\s*(?:Резюме|Summary|Краткое описание)[:\s]*\n?', 'summary'),
        (r'(?:^|\n)#+\s*(?:Проблемы|Problems|Issues|Выявленные проблемы)[:\s]*\n?', 'problems'),
        (r'(?:^|\n)#+\s*(?:Рекомендации|Recommendations|Предложения)[:\s]*\n?', 'recommendations'),
        (r'(?:^|\n)#+\s*(?:Ключевые изменения|Key Changes|Изменения)[:\s]*\n?', 'key_changes'),
        (r'(?:^|\n)#+\s*(?:Навигация|Navigation|Паттерны навигации)[:\s]*\n?', 'navigation'),
        (r'(?:^|\n)#+\s*(?:UX проблемы|UX Issues|UX Problems)[:\s]*\n?', 'ux_issues'),
        (r'(?:^|\n)#+\s*(?:Выводы|Conclusions|Заключение)[:\s]*\n?', 'conclusions'),
    ]
    
    # Try to split by headers
    current_section = 'main'
    current_content = []
    lines = text.split('\n')
    
    for line in lines:
        matched = False
        for pattern, section_name in section_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                # Save current section
                if current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = section_name
                current_content = []
                matched = True
                break
        
        if not matched:
            current_content.append(line)
    
    # Save last section
    if current_content:
        sections[current_section] = '\n'.join(current_content).strip()
    
    # If no sections found, put everything in 'full_text'
    if not sections or (len(sections) == 1 and 'main' in sections):
        sections = {'full_text': text}
    
    return sections


def format_for_frontend(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format analysis result specifically for frontend consumption.
    Returns a clean, structured response.
    
    Args:
        analysis_result: Raw analysis result from orchestrator
        
    Returns:
        Frontend-friendly formatted response
    """
    formatted = format_llm_analysis(analysis_result)
    
    # Build frontend response
    response = {
        'success': formatted['status'] == 'success' or formatted['analysis']['status'] == 'success',
        'timestamp': formatted['timestamp'],
        'project': formatted['project'],
        'releases': formatted['releases_compared'],
    }
    
    analysis = formatted.get('analysis', {})
    
    if analysis.get('status') == 'success':
        response['analysis'] = {
            'text': analysis.get('text', ''),
            'sections': analysis.get('sections', {}),
            'model_info': analysis.get('metadata', {})
        }
        response['error'] = None
    else:
        response['analysis'] = None
        response['error'] = analysis.get('error', 'Analysis not available')
    
    # Include validation info
    response['validation'] = formatted.get('validation', {})
    
    return response


def create_human_readable_response(
    analysis_result: Dict[str, Any],
    include_raw: bool = False
) -> Dict[str, Any]:
    """
    Create a complete human-readable response from LLM analysis.
    
    Args:
        analysis_result: Raw analysis result
        include_raw: Whether to include raw analysis text
        
    Returns:
        Human-readable response structure
    """
    formatted = format_for_frontend(analysis_result)
    
    # Add summary at the top level for quick access
    if formatted.get('analysis') and formatted['analysis'].get('sections'):
        sections = formatted['analysis']['sections']
        formatted['summary'] = (
            sections.get('summary') or 
            sections.get('conclusions') or 
            sections.get('full_text', '')[:500]
        )
    else:
        formatted['summary'] = None
    
    if not include_raw and formatted.get('analysis'):
        # Remove full text from sections to reduce response size
        if 'full_text' in formatted['analysis'].get('sections', {}):
            # Keep only if it's the only section
            if len(formatted['analysis']['sections']) > 1:
                del formatted['analysis']['sections']['full_text']
    
    return formatted

