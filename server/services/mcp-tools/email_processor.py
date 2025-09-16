#!/usr/bin/env python3
"""
Email Processor MCP Tool
Real email processing functionality without hardcoded credentials
"""
import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Any


def process_email_content(email_subject: str, email_body: str, sender_email: str) -> Dict[str, Any]:
    """Process email content and generate appropriate response."""
    try:
        result = {
            'success': True,
            'sender': sender_email,
            'subject': email_subject,
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
        response_draft = generate_email_response(email_body, analysis['type'], sender_email.split('@')[0])
        result['processing_results']['response_draft'] = response_draft
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Error processing email: {str(e)}"
        }


def analyze_email_content(email_subject: str, email_body: str, sender_email: str) -> Dict[str, Any]:
    """Analyze email content to understand intent, urgency, and required response type."""
    try:
        analysis = {
            'priority_level': 'normal',
            'type': 'general',
            'urgency_indicators': [],
            'key_topics': [],
            'action_required': False
        }
        
        # Analyze subject line
        subject_lower = email_subject.lower()
        body_lower = email_body.lower()
        
        # Check for urgency indicators
        urgency_words = ['urgent', 'asap', 'emergency', 'important', 'critical', 'deadline']
        found_urgency = [word for word in urgency_words if word in subject_lower or word in body_lower]
        if found_urgency:
            analysis['urgency_indicators'] = found_urgency
            analysis['priority_level'] = 'high'
        
        # Analyze content type
        if any(word in body_lower for word in ['thank', 'thanks', 'appreciate']):
            analysis['type'] = 'appreciation'
        elif any(word in body_lower for word in ['?', 'how', 'what', 'when', 'where', 'why']):
            analysis['type'] = 'inquiry'
            analysis['action_required'] = True
        elif any(word in body_lower for word in ['complaint', 'problem', 'issue', 'wrong', 'error']):
            analysis['type'] = 'complaint'
            analysis['action_required'] = True
            analysis['priority_level'] = 'medium' if analysis['priority_level'] == 'normal' else analysis['priority_level']
        elif any(word in body_lower for word in ['request', 'please', 'could you', 'would you']):
            analysis['type'] = 'request'
            analysis['action_required'] = True
        
        # Extract key topics (simple keyword extraction)
        technical_terms = ['las file', 'well log', 'porosity', 'gamma ray', 'resistivity', 'formation', 'drilling']
        found_topics = [term for term in technical_terms if term in body_lower]
        analysis['key_topics'] = found_topics
        
        return analysis
        
    except Exception as e:
        return {'error': f"Error analyzing email content: {str(e)}"}


def analyze_email_sentiment(email_content: str) -> Dict[str, Any]:
    """Analyze the emotional sentiment of the email."""
    try:
        content_lower = email_content.lower()
        
        # Positive indicators
        positive_words = ['thank', 'great', 'excellent', 'wonderful', 'amazing', 'perfect', 'love', 'happy', 'pleased']
        positive_count = sum(1 for word in positive_words if word in content_lower)
        
        # Negative indicators
        negative_words = ['angry', 'frustrated', 'terrible', 'awful', 'hate', 'disappointed', 'unacceptable', 'horrible']
        negative_count = sum(1 for word in negative_words if word in content_lower)
        
        # Neutral/professional indicators
        professional_words = ['regarding', 'please', 'kindly', 'request', 'information', 'assistance']
        professional_count = sum(1 for word in professional_words if word in content_lower)
        
        # Determine overall sentiment
        if positive_count > negative_count and positive_count > 0:
            sentiment = 'positive'
            confidence = min(0.9, 0.6 + (positive_count - negative_count) * 0.1)
        elif negative_count > positive_count and negative_count > 0:
            sentiment = 'negative'  
            confidence = min(0.9, 0.6 + (negative_count - positive_count) * 0.1)
        else:
            sentiment = 'neutral'
            confidence = 0.7 + professional_count * 0.05
        
        return {
            'sentiment': sentiment,
            'confidence': round(confidence, 2),
            'positive_indicators': positive_count,
            'negative_indicators': negative_count,
            'professional_tone': professional_count > 0
        }
        
    except Exception as e:
        return {'error': f"Error analyzing sentiment: {str(e)}"}


def classify_email_priority(subject: str, content: str) -> Dict[str, Any]:
    """Classify the priority level of the email."""
    try:
        subject_lower = subject.lower()
        content_lower = content.lower()
        
        priority_score = 0
        indicators = []
        
        # High priority indicators
        high_priority_words = ['urgent', 'emergency', 'asap', 'immediately', 'critical', 'deadline', 'breaking']
        for word in high_priority_words:
            if word in subject_lower:
                priority_score += 3
                indicators.append(f"Subject contains '{word}'")
            elif word in content_lower:
                priority_score += 2
                indicators.append(f"Content contains '{word}'")
        
        # Medium priority indicators
        medium_priority_words = ['important', 'soon', 'issue', 'problem', 'help', 'support', 'question']
        for word in medium_priority_words:
            if word in subject_lower:
                priority_score += 2
                indicators.append(f"Subject contains '{word}'")
            elif word in content_lower:
                priority_score += 1
                indicators.append(f"Content contains '{word}'")
        
        # Determine priority level
        if priority_score >= 5:
            priority_level = 'high'
            response_time = 'Within 2 hours'
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
            'indicators': indicators
        }
        
    except Exception as e:
        return {'error': f"Error classifying priority: {str(e)}"}


def generate_email_response(email_content: str, email_type: str, sender_name: str = "valued customer") -> Dict[str, Any]:
    """Generate an appropriate email response based on content analysis."""
    try:
        if not sender_name or sender_name == "":
            sender_name = "valued customer"
        
        # Generate response based on email type
        if email_type == "inquiry":
            response = f"""Dear {sender_name},

Thank you for reaching out to us. I've reviewed your inquiry and I'm happy to help provide the information you're looking for.

Based on your message, I understand you're asking about technical aspects related to well log analysis. Our team specializes in LAS file processing and can assist with:

- Gamma ray log interpretation
- Porosity analysis (neutron and density logs)
- Resistivity log analysis
- Formation evaluation and lithology identification

I'll review your specific questions and provide detailed technical information within 24 hours. If you have LAS files that need analysis, please feel free to attach them to your response.

Best regards,
Technical Support Team"""

        elif email_type == "complaint":
            response = f"""Dear {sender_name},

Thank you for bringing this matter to our attention. I sincerely apologize for any inconvenience you've experienced.

I understand your concerns and want to assure you that we take all feedback seriously. Our team will immediately investigate the issues you've raised and work towards a prompt resolution.

I will personally follow up with you within 12 hours with a detailed action plan and timeline for addressing your concerns.

In the meantime, if this is an urgent matter, please don't hesitate to contact our support team directly.

Best regards,
Customer Service Manager"""

        elif email_type == "appreciation":
            response = f"""Dear {sender_name},

Thank you so much for your kind words! It truly means a lot to our team to receive such positive feedback.

We're delighted to hear that our services have met your expectations and that you've had a positive experience with our well log analysis tools.

Your feedback motivates us to continue providing high-quality technical support and innovative solutions for the oil and gas industry.

Please don't hesitate to reach out if you need any assistance with future projects.

Best regards,
Customer Success Team"""

        elif email_type == "request":
            response = f"""Dear {sender_name},

Thank you for your request. I've received your message and understand what you're looking for.

I'll review the details of your request and coordinate with our technical team to provide you with the most accurate and helpful response.

You can expect a comprehensive reply within 24-48 hours. If your request involves technical analysis or requires specific expertise, we may need additional time to ensure we provide you with the highest quality information.

If you have any urgent questions in the meantime, please feel free to reach out.

Best regards,
Technical Support Team"""

        else:  # general
            response = f"""Dear {sender_name},

Thank you for your message. I've received your communication and appreciate you taking the time to reach out to us.

I'll review the details of your message and ensure you receive appropriate assistance. Our team will respond with relevant information and next steps within 24 hours.

If there's anything specific I can help you with or if you have any questions, please don't hesitate to let me know.

Best regards,
Customer Service Team"""
        
        return {
            'response_draft': response,
            'response_type': email_type,
            'estimated_response_time': '24 hours',
            'requires_human_review': email_type in ['complaint', 'request']
        }
        
    except Exception as e:
        return {'error': f"Error generating response: {str(e)}"}


def extract_contact_info(email_content: str, sender_email: str) -> Dict[str, Any]:
    """Extract and organize contact information from the email."""
    try:
        contact_info = {
            'email_address': sender_email,
            'phone_numbers': [],
            'company': None,
            'name': None
        }
        
        # Extract phone numbers using regex
        phone_pattern = r'(\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})'
        phones = re.findall(phone_pattern, email_content)
        contact_info['phone_numbers'] = list(set(phones))  # Remove duplicates
        
        # Extract company name (look for common patterns)
        company_patterns = [
            r'(?:from|at|with)\s+([A-Z][A-Za-z\s&]+(?:Inc|LLC|Corp|Ltd|Company))',
            r'([A-Z][A-Za-z\s&]+(?:Inc|LLC|Corp|Ltd|Company))'
        ]
        
        for pattern in company_patterns:
            matches = re.findall(pattern, email_content, re.IGNORECASE)
            if matches:
                contact_info['company'] = matches[0].strip()
                break
        
        # Extract name from email signature (basic pattern)
        name_patterns = [
            r'Best regards,\s*([A-Z][a-z]+ [A-Z][a-z]+)',
            r'Sincerely,\s*([A-Z][a-z]+ [A-Z][a-z]+)',
            r'Thanks,\s*([A-Z][a-z]+ [A-Z][a-z]+)'
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, email_content)
            if matches:
                contact_info['name'] = matches[0].strip()
                break
        
        return contact_info
        
    except Exception as e:
        return {'error': f"Error extracting contact info: {str(e)}"}


def handle_email_attachments(attachments: List[str]) -> Dict[str, Any]:
    """Process and analyze email attachments."""
    try:
        if not attachments:
            return {'message': 'No attachments to process', 'attachment_count': 0}
        
        attachment_info = {
            'attachment_count': len(attachments),
            'processed_attachments': [],
            'las_files_found': [],
            'other_files': []
        }
        
        data_dir = Path("data/email-attachments")
        
        for attachment in attachments:
            file_path = data_dir / attachment
            
            if not file_path.exists():
                attachment_info['processed_attachments'].append({
                    'filename': attachment,
                    'status': 'not_found',
                    'message': f'Attachment {attachment} not found in data directory'
                })
                continue
            
            file_ext = attachment.split('.')[-1].lower() if '.' in attachment else 'unknown'
            file_size = file_path.stat().st_size
            
            attachment_detail = {
                'filename': attachment,
                'file_extension': file_ext,
                'file_size_bytes': file_size,
                'file_size_kb': round(file_size / 1024, 2),
                'status': 'processed'
            }
            
            # Categorize by file type
            if file_ext == 'las':
                attachment_info['las_files_found'].append(attachment)
                attachment_detail['file_type'] = 'LAS well log file'
                attachment_detail['analysis_available'] = True
                
                # Move to main data directory for analysis
                dest_path = Path("data") / attachment
                if not dest_path.exists():
                    import shutil
                    shutil.copy2(file_path, dest_path)
                    attachment_detail['moved_to_analysis_folder'] = True
                
            elif file_ext in ['pdf', 'doc', 'docx']:
                attachment_detail['file_type'] = 'Document file'
                attachment_info['other_files'].append(attachment)
                
            elif file_ext in ['jpg', 'jpeg', 'png', 'gif']:
                attachment_detail['file_type'] = 'Image file'
                attachment_info['other_files'].append(attachment)
                
            elif file_ext in ['txt', 'csv']:
                attachment_detail['file_type'] = 'Data file'
                attachment_info['other_files'].append(attachment)
                
            else:
                attachment_detail['file_type'] = 'Other file'
                attachment_info['other_files'].append(attachment)
            
            attachment_info['processed_attachments'].append(attachment_detail)
        
        # Generate summary
        attachment_info['summary'] = {
            'total_attachments': len(attachments),
            'las_files': len(attachment_info['las_files_found']),
            'other_files': len(attachment_info['other_files']),
            'ready_for_analysis': len(attachment_info['las_files_found'])
        }
        
        return attachment_info
        
    except Exception as e:
        return {'error': f"Error handling attachments: {str(e)}"}


if __name__ == "__main__":
    # Command line interface for testing
    if len(sys.argv) < 4:
        print("Usage: python email_processor.py <sender_email> <subject> <body>")
        sys.exit(1)
    
    sender_email = sys.argv[1]
    subject = sys.argv[2]
    body = sys.argv[3]
    
    result = process_email_content(subject, body, sender_email)
    print(result)