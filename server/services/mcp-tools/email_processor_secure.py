#!/usr/bin/env python3
"""
Secure Email Processor MCP Tool
Enhanced security with proper attachment handling and path sanitization
"""
import os
import sys
import re
import json
from pathlib import Path
from typing import Dict, List, Any


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks"""
    if not filename:
        return "unknown_file"
    
    # Get basename only (removes any path separators)
    safe_name = os.path.basename(filename)
    
    # Remove or replace dangerous characters
    safe_name = re.sub(r'[<>:"|?*]', '_', safe_name)
    safe_name = re.sub(r'\.\.+', '.', safe_name)  # Remove multiple dots
    
    # Ensure filename is not empty after sanitization
    if not safe_name or safe_name == '.' or safe_name == '..':
        safe_name = "sanitized_file"
    
    # Limit filename length
    if len(safe_name) > 255:
        name_part, ext_part = os.path.splitext(safe_name)
        safe_name = name_part[:250] + ext_part
    
    return safe_name


def is_allowed_extension(filename: str, allowed_extensions: List[str] = None) -> bool:
    """Check if file extension is allowed"""
    if allowed_extensions is None:
        # Default allowed extensions for well log analysis
        allowed_extensions = ['.las', '.txt', '.csv', '.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']
    
    if not filename:
        return False
    
    file_ext = os.path.splitext(filename)[1].lower()
    return file_ext in [ext.lower() for ext in allowed_extensions]


def validate_file_size(filepath: Path, max_size_mb: int = 100) -> bool:
    """Validate file size is within limits"""
    try:
        if not filepath.exists():
            return False
        
        file_size_mb = filepath.stat().st_size / (1024 * 1024)
        return file_size_mb <= max_size_mb
    except Exception:
        return False


def process_email_content(email_subject: str, email_body: str, sender_email: str) -> Dict[str, Any]:
    """Process email content and generate appropriate response with enhanced security"""
    try:
        # Input validation
        if not all([email_subject, email_body, sender_email]):
            return {
                'success': False,
                'error': 'Missing required email fields (subject, body, or sender)'
            }
        
        # Validate email format (basic check)
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', sender_email):
            return {
                'success': False,
                'error': 'Invalid sender email format'
            }
        
        result = {
            'success': True,
            'sender': sender_email,
            'subject': email_subject[:200],  # Limit subject length
            'processing_results': {}
        }
        
        # Analyze email content
        analysis = analyze_email_content(email_subject, email_body, sender_email)
        result['processing_results']['content_analysis'] = analysis
        
        # Analyze sentiment
        sentiment = analyze_email_sentiment(email_body)
        result['processing_results']['sentiment'] = sentiment
        
        # Classify priority
        priority = classify_email_priority(email_subject, email_body)
        result['processing_results']['priority'] = priority
        
        # Generate response draft
        sender_name = extract_sender_name(sender_email, email_body)
        response_draft = generate_email_response(email_body, analysis.get('type', 'general'), sender_name)
        result['processing_results']['response_draft'] = response_draft
        
        # Extract technical topics
        technical_topics = extract_technical_topics(email_body)
        result['processing_results']['technical_topics'] = technical_topics
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Error processing email: {str(e)}'
        }


def analyze_email_content(email_subject: str, email_body: str, sender_email: str) -> Dict[str, Any]:
    """Analyze email content with enhanced categorization"""
    try:
        analysis = {
            'priority_level': 'normal',
            'type': 'general',
            'urgency_indicators': [],
            'key_topics': [],
            'action_required': False,
            'technical_request': False,
            'estimated_complexity': 'low'
        }
        
        # Analyze subject line and body
        subject_lower = email_subject.lower()
        body_lower = email_body.lower()
        combined_text = f"{subject_lower} {body_lower}"
        
        # Check for urgency indicators
        urgency_words = ['urgent', 'asap', 'emergency', 'immediate', 'critical', 'deadline', 'rush']
        found_urgency = [word for word in urgency_words if word in combined_text]
        if found_urgency:
            analysis['urgency_indicators'] = found_urgency
            analysis['priority_level'] = 'high'
        
        # Analyze content type with more specific categories
        if any(word in body_lower for word in ['thank', 'thanks', 'appreciate', 'grateful']):
            analysis['type'] = 'appreciation'
            
        elif any(word in body_lower for word in ['?', 'how', 'what', 'when', 'where', 'why', 'question']):
            analysis['type'] = 'inquiry'
            analysis['action_required'] = True
            
        elif any(word in body_lower for word in ['complaint', 'problem', 'issue', 'wrong', 'error', 'dissatisfied']):
            analysis['type'] = 'complaint'
            analysis['action_required'] = True
            analysis['priority_level'] = 'medium' if analysis['priority_level'] == 'normal' else analysis['priority_level']
            
        elif any(word in body_lower for word in ['request', 'please', 'could you', 'would you', 'need']):
            analysis['type'] = 'request'
            analysis['action_required'] = True
            
        elif any(word in body_lower for word in ['analyze', 'analysis', 'interpretation', 'report']):
            analysis['type'] = 'technical_request'
            analysis['technical_request'] = True
            analysis['action_required'] = True
            analysis['estimated_complexity'] = 'medium'
        
        # Extract technical topics
        technical_terms = [
            'las file', 'well log', 'porosity', 'gamma ray', 'resistivity', 
            'formation', 'drilling', 'lithology', 'neutron', 'density',
            'saturation', 'permeability', 'hydrocarbon', 'petrophysics'
        ]
        found_topics = [term for term in technical_terms if term in body_lower]
        analysis['key_topics'] = found_topics
        
        if len(found_topics) > 3:
            analysis['estimated_complexity'] = 'high'
        elif len(found_topics) > 1:
            analysis['estimated_complexity'] = 'medium'
        
        # Check for data file mentions
        if any(ext in body_lower for ext in ['.las', '.csv', '.txt', 'attachment', 'attached', 'file']):
            analysis['has_data_files'] = True
            analysis['technical_request'] = True
        
        return analysis
        
    except Exception as e:
        return {'error': f'Error analyzing email content: {str(e)}'}


def analyze_email_sentiment(email_content: str) -> Dict[str, Any]:
    """Enhanced sentiment analysis"""
    try:
        content_lower = email_content.lower()
        
        # Positive indicators
        positive_words = ['thank', 'great', 'excellent', 'wonderful', 'amazing', 'perfect', 'love', 'happy', 'pleased', 'satisfied', 'appreciate']
        positive_count = sum(1 for word in positive_words if word in content_lower)
        
        # Negative indicators  
        negative_words = ['angry', 'frustrated', 'terrible', 'awful', 'hate', 'disappointed', 'unacceptable', 'horrible', 'wrong', 'problem', 'issue']
        negative_count = sum(1 for word in negative_words if word in content_lower)
        
        # Professional/neutral indicators
        professional_words = ['regarding', 'please', 'kindly', 'request', 'information', 'assistance', 'analysis', 'report']
        professional_count = sum(1 for word in professional_words if word in content_lower)
        
        # Technical indicators
        technical_words = ['data', 'analysis', 'interpretation', 'results', 'parameters', 'technical']
        technical_count = sum(1 for word in technical_words if word in content_lower)
        
        # Determine overall sentiment
        total_indicators = positive_count + negative_count + professional_count
        
        if positive_count > negative_count and positive_count > 0:
            sentiment = 'positive'
            confidence = min(0.9, 0.6 + (positive_count - negative_count) * 0.1)
        elif negative_count > positive_count and negative_count > 0:
            sentiment = 'negative'
            confidence = min(0.9, 0.6 + (negative_count - positive_count) * 0.1)
        else:
            sentiment = 'neutral'
            confidence = 0.7 + (professional_count * 0.05)
        
        return {
            'sentiment': sentiment,
            'confidence': round(confidence, 2),
            'positive_indicators': positive_count,
            'negative_indicators': negative_count,
            'professional_tone': professional_count > 0,
            'technical_tone': technical_count > 2
        }
        
    except Exception as e:
        return {'error': f'Error analyzing sentiment: {str(e)}'}


def classify_email_priority(subject: str, content: str) -> Dict[str, Any]:
    """Enhanced priority classification"""
    try:
        subject_lower = subject.lower()
        content_lower = content.lower()
        
        priority_score = 0
        indicators = []
        
        # High priority indicators (subject line weighted more)
        high_priority_words = ['urgent', 'emergency', 'asap', 'immediate', 'critical', 'deadline', 'breaking']
        for word in high_priority_words:
            if word in subject_lower:
                priority_score += 4
                indicators.append(f"Subject contains '{word}'")
            elif word in content_lower:
                priority_score += 2
                indicators.append(f"Content contains '{word}'")
        
        # Medium priority indicators
        medium_priority_words = ['important', 'soon', 'issue', 'problem', 'help', 'support', 'question', 'request']
        for word in medium_priority_words:
            if word in subject_lower:
                priority_score += 2
                indicators.append(f"Subject contains '{word}'")
            elif word in content_lower:
                priority_score += 1
                indicators.append(f"Content contains '{word}'")
        
        # Technical complexity indicators
        if any(term in content_lower for term in ['complex analysis', 'detailed interpretation', 'comprehensive report']):
            priority_score += 2
            indicators.append("Complex technical request")
        
        # Time-sensitive indicators
        time_words = ['today', 'tomorrow', 'this week', 'end of day', 'eod']
        if any(word in content_lower for word in time_words):
            priority_score += 1
            indicators.append("Time-sensitive request")
        
        # Determine priority level
        if priority_score >= 6:
            priority_level = 'critical'
            response_time = 'Within 1 hour'
        elif priority_score >= 4:
            priority_level = 'high'
            response_time = 'Within 4 hours'
        elif priority_score >= 2:
            priority_level = 'medium'
            response_time = 'Within 24 hours'
        else:
            priority_level = 'normal'
            response_time = 'Within 48 hours'
        
        return {
            'priority_level': priority_level,
            'priority_score': priority_score,
            'response_time_expectation': response_time,
            'indicators': indicators[:5]  # Limit to top 5 indicators
        }
        
    except Exception as e:
        return {'error': f'Error classifying priority: {str(e)}'}


def generate_email_response(email_content: str, email_type: str, sender_name: str = "valued client") -> Dict[str, Any]:
    """Generate contextually appropriate email responses"""
    try:
        if not sender_name or sender_name.strip() == "":
            sender_name = "valued client"
        
        # Generate response based on email type
        responses = {
            'inquiry': f"""Dear {sender_name},

Thank you for your inquiry regarding well log analysis. I've reviewed your question and understand you're seeking technical assistance with LAS file interpretation.

Our team specializes in comprehensive petrophysical analysis including:
- Gamma ray log interpretation for lithology identification
- Porosity analysis using neutron and density logs
- Resistivity analysis for fluid saturation assessment
- Formation evaluation and reservoir characterization

I'll provide detailed technical information addressing your specific questions within 24 hours. If you have LAS files for analysis, please ensure they are attached securely.

For immediate technical support, please reference ticket #{abs(hash(email_content)) % 10000}.

Best regards,
Technical Analysis Team""",

            'technical_request': f"""Dear {sender_name},

Thank you for your technical analysis request. I've received your requirements for well log interpretation services.

Based on your request, our analysis will include:
- LAS file validation and quality assessment  
- Petrophysical parameter calculations
- Formation evaluation and lithology analysis
- Detailed interpretation report with recommendations

Our technical team will begin processing your request immediately. You can expect:
- Initial quality assessment within 4 hours
- Preliminary results within 24 hours  
- Complete analysis report within 48 hours

Reference ID: #{abs(hash(email_content)) % 10000}

Best regards,
Senior Petrophysicist""",

            'complaint': f"""Dear {sender_name},

Thank you for bringing this matter to our attention. I sincerely apologize for any issues you've experienced with our services.

Please be assured that:
- Your concerns are being escalated to our senior technical team
- We are conducting a thorough review of our analysis procedures
- A technical supervisor will contact you within 2 hours
- We will provide a corrective action plan within 12 hours

Your satisfaction is our priority, and we are committed to resolving this matter promptly and professionally.

Reference Case: #{abs(hash(email_content)) % 10000}

Sincerely,
Customer Success Manager""",

            'appreciation': f"""Dear {sender_name},

Thank you so much for your positive feedback! It's wonderful to hear that our well log analysis services have met your expectations.

Your testimonial means a great deal to our technical team who work diligently to provide accurate and timely petrophysical interpretations.

We look forward to supporting your future projects and continuing to deliver the high-quality analysis you've come to expect.

Please don't hesitate to reach out for any upcoming well log interpretation needs.

Best regards,
Client Relations Team""",

            'request': f"""Dear {sender_name},

Thank you for your request. I've received your inquiry and understand the scope of your requirements.

I'll coordinate with our technical specialists to ensure you receive comprehensive assistance tailored to your specific needs.

Expected timeline:
- Request review and scoping: 2-4 hours
- Technical analysis (if applicable): 24-48 hours  
- Detailed response with deliverables: 48-72 hours

I'll keep you updated on our progress and reach out if we need any clarification.

Request ID: #{abs(hash(email_content)) % 10000}

Best regards,
Project Coordination Team"""
        }
        
        # Default response
        default_response = f"""Dear {sender_name},

Thank you for contacting our well log analysis team. I've received your message and will ensure you receive appropriate assistance.

Our team will review your inquiry and respond with relevant information and next steps within 24 hours.

For technical questions, please reference our services:
- LAS file analysis and interpretation
- Formation evaluation and lithology assessment
- Petrophysical parameter calculation
- Reservoir characterization studies

If this is urgent, please indicate the priority level in your response.

Best regards,
Technical Support Team"""
        
        selected_response = responses.get(email_type, default_response)
        
        return {
            'response_draft': selected_response,
            'response_type': email_type,
            'estimated_response_time': '24-48 hours',
            'requires_human_review': email_type in ['complaint', 'technical_request'],
            'auto_reply_safe': email_type in ['appreciation', 'inquiry']
        }
        
    except Exception as e:
        return {'error': f'Error generating response: {str(e)}'}


def extract_sender_name(sender_email: str, email_body: str) -> str:
    """Extract sender name from email or signature"""
    try:
        # Try to extract from email signature
        signature_patterns = [
            r'(?:Best regards|Sincerely|Thanks|Regards),\s*\n?([A-Z][a-z]+ [A-Z][a-z]+)',
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*\n.*(?:Engineer|Geologist|Manager|Director|Analyst)',
            r'From:.*?([A-Z][a-z]+ [A-Z][a-z]+)',
        ]
        
        for pattern in signature_patterns:
            matches = re.findall(pattern, email_body, re.IGNORECASE | re.MULTILINE)
            if matches:
                return matches[0].strip()
        
        # Extract from email address
        local_part = sender_email.split('@')[0]
        # Convert common separators to spaces and title case
        name_guess = re.sub(r'[._-]', ' ', local_part).title()
        
        # Only return if it looks like a real name (has at least 2 parts)
        if len(name_guess.split()) >= 2:
            return name_guess
        
        return "valued client"
        
    except Exception:
        return "valued client"


def extract_technical_topics(email_body: str) -> List[str]:
    """Extract technical topics and keywords from email"""
    try:
        body_lower = email_body.lower()
        
        # Define technical topic categories
        topics_found = []
        
        topic_categories = {
            'log_analysis': ['gamma ray', 'gr log', 'neutron', 'density', 'resistivity', 'porosity'],
            'formation_evaluation': ['lithology', 'formation', 'reservoir', 'hydrocarbon', 'saturation'],
            'data_processing': ['las file', 'data quality', 'calibration', 'processing', 'interpretation'],
            'petrophysics': ['permeability', 'water saturation', 'net pay', 'cutoff', 'shale volume'],
            'geology': ['structural', 'stratigraphy', 'facies', 'depositional', 'correlation']
        }
        
        for category, keywords in topic_categories.items():
            if any(keyword in body_lower for keyword in keywords):
                topics_found.append(category.replace('_', ' ').title())
        
        # Extract specific depth ranges mentioned
        depth_patterns = [
            r'(\d{3,5})\s*(?:ft|feet|m|meters?)',
            r'(\d{3,5})\s*[-–]\s*(\d{3,5})\s*(?:ft|feet|m|meters?)'
        ]
        
        depths_mentioned = []
        for pattern in depth_patterns:
            matches = re.findall(pattern, email_body)
            depths_mentioned.extend([match if isinstance(match, str) else '-'.join(match) for match in matches])
        
        if depths_mentioned:
            topics_found.append(f"Depth Analysis ({len(depths_mentioned)} ranges mentioned)")
        
        return topics_found
        
    except Exception as e:
        return [f"Error extracting topics: {str(e)}"]


def handle_email_attachments_secure(attachments: List[str], max_file_size_mb: int = 100) -> Dict[str, Any]:
    """Secure email attachment handling with validation"""
    try:
        if not attachments:
            return {
                'success': True,
                'message': 'No attachments to process',
                'attachment_count': 0
            }
        
        attachment_info = {
            'success': True,
            'attachment_count': len(attachments),
            'processed_attachments': [],
            'las_files_found': [],
            'other_files': [],
            'security_issues': []
        }
        
        data_dir = Path("data/email-attachments")
        if not data_dir.exists():
            data_dir.mkdir(parents=True, exist_ok=True)
        
        for attachment in attachments:
            # Sanitize filename
            safe_filename = sanitize_filename(attachment)
            
            if safe_filename != attachment:
                attachment_info['security_issues'].append({
                    'original': attachment,
                    'sanitized': safe_filename,
                    'issue': 'Filename sanitized for security'
                })
            
            file_path = data_dir / safe_filename
            
            attachment_detail = {
                'original_name': attachment,
                'safe_name': safe_filename,
                'status': 'processed'
            }
            
            # Check if file exists
            if not file_path.exists():
                attachment_detail['status'] = 'not_found'
                attachment_detail['message'] = f'File not found: {safe_filename}'
                attachment_info['processed_attachments'].append(attachment_detail)
                continue
            
            # Validate file size
            if not validate_file_size(file_path, max_file_size_mb):
                attachment_detail['status'] = 'rejected'
                attachment_detail['message'] = f'File too large (max {max_file_size_mb}MB)'
                attachment_info['security_issues'].append({
                    'file': safe_filename,
                    'issue': f'File size exceeds {max_file_size_mb}MB limit'
                })
                attachment_info['processed_attachments'].append(attachment_detail)
                continue
            
            # Check file extension
            if not is_allowed_extension(safe_filename):
                attachment_detail['status'] = 'rejected'
                attachment_detail['message'] = 'File type not allowed'
                attachment_info['security_issues'].append({
                    'file': safe_filename,
                    'issue': 'File extension not allowed'
                })
                attachment_info['processed_attachments'].append(attachment_detail)
                continue
            
            # Process valid files
            file_ext = os.path.splitext(safe_filename)[1].lower()
            file_size = file_path.stat().st_size
            
            attachment_detail.update({
                'file_extension': file_ext,
                'file_size_bytes': file_size,
                'file_size_kb': round(file_size / 1024, 2),
                'status': 'processed'
            })
            
            # Categorize by file type
            if file_ext == '.las':
                attachment_info['las_files_found'].append(safe_filename)
                attachment_detail['file_type'] = 'LAS well log file'
                attachment_detail['analysis_available'] = True
                
                # Copy to main data directory for analysis (securely)
                dest_path = Path("data") / safe_filename
                if not dest_path.exists():
                    import shutil
                    try:
                        shutil.copy2(file_path, dest_path)
                        attachment_detail['moved_to_analysis_folder'] = True
                    except Exception as e:
                        attachment_detail['copy_error'] = str(e)
                
            elif file_ext in ['.pdf', '.doc', '.docx']:
                attachment_detail['file_type'] = 'Document file'
                attachment_info['other_files'].append(safe_filename)
                
            elif file_ext in ['.jpg', '.jpeg', '.png']:
                attachment_detail['file_type'] = 'Image file'
                attachment_info['other_files'].append(safe_filename)
                
            elif file_ext in ['.txt', '.csv']:
                attachment_detail['file_type'] = 'Data file'
                attachment_info['other_files'].append(safe_filename)
            else:
                attachment_detail['file_type'] = 'Other file'
                attachment_info['other_files'].append(safe_filename)
            
            attachment_info['processed_attachments'].append(attachment_detail)
        
        # Generate summary
        attachment_info['summary'] = {
            'total_attachments': len(attachments),
            'processed_successfully': len([a for a in attachment_info['processed_attachments'] if a['status'] == 'processed']),
            'las_files': len(attachment_info['las_files_found']),
            'other_files': len(attachment_info['other_files']),
            'security_issues': len(attachment_info['security_issues']),
            'ready_for_analysis': len(attachment_info['las_files_found'])
        }
        
        return attachment_info
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Error handling attachments: {str(e)}'
        }


if __name__ == "__main__":
    # Command line interface for testing
    if len(sys.argv) < 4:
        print("Usage: python email_processor_secure.py <sender_email> <subject> <body>")
        print("       python email_processor_secure.py test")
        sys.exit(1)
    
    if sys.argv[1] == "test":
        # Run security tests
        test_attachments = ["normal_file.las", "../../../etc/passwd", "test<script>.las", "very_long_filename" * 20 + ".las"]
        result = handle_email_attachments_secure(test_attachments)
        print("Security Test Results:")
        print(json.dumps(result, indent=2))
    else:
        sender_email = sys.argv[1]
        subject = sys.argv[2]
        body = sys.argv[3]
        
        result = process_email_content(subject, body, sender_email)
        print(json.dumps(result, indent=2))